"""
Auto-Planner Service
====================
District-based delivery planning with capacity constraints.

Algorithm:
1. Collect PLANNED assignments that have no Delivery record yet.
2. Resolve coordinates for each customer (fallback: District center).
3. Group same-customer assignments into a single logical stop.
4. Group stops by District (İlçe).
5. Distribute district groups across the next N business days,
   respecting a daily cap of MAX_DELIVERIES_PER_DAY.
6. For each day, run Nearest-Neighbor + 2-opt to optimize the route.
7. Return a preview JSON (nothing written to DB).
"""

import math
from datetime import date, timedelta
from collections import defaultdict
from typing import List, Dict, Any, Tuple, Optional

from ..models import (
    ProductAssignment, Delivery, CustomerAddress, DepotLocation, District
)


# ── Config ──────────────────────────────────────────────────────────
MAX_DELIVERIES_PER_DAY = 10
MAX_HOURS_PER_DAY = 6
AVG_SPEED_KMH = 60        # KKTC average road speed
STOP_DURATION_MIN = 5      # time spent at each stop
# ────────────────────────────────────────────────────────────────────


# ════════════════════════════════════════════════════════════════════
# 1. Haversine
# ════════════════════════════════════════════════════════════════════
def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the distance (km) between two lat/lng points."""
    R = 6371
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


# ════════════════════════════════════════════════════════════════════
# 2. Nearest-Neighbor + 2-opt
# ════════════════════════════════════════════════════════════════════
def _nn_route(depot: Tuple[float, float], stops: List[dict]) -> List[dict]:
    """
    Nearest-Neighbor ordering.
    Each stop dict must have 'lat' and 'lng' keys.
    Returns the ordered list with 'dist_from_prev' added.
    """
    if not stops:
        return []

    unvisited = list(stops)
    route: List[dict] = []
    cur_lat, cur_lng = depot

    while unvisited:
        best, best_dist = None, float('inf')
        for s in unvisited:
            d = haversine_km(cur_lat, cur_lng, s['lat'], s['lng'])
            if d < best_dist:
                best_dist = d
                best = s
        unvisited.remove(best)
        best['dist_from_prev'] = round(best_dist, 2)
        route.append(best)
        cur_lat, cur_lng = best['lat'], best['lng']

    return route


def _two_opt(route: List[dict], depot: Tuple[float, float]) -> List[dict]:
    """Improve route with 2-opt swaps until no improvement is found."""
    if len(route) < 3:
        return route

    def total_dist(r: List[dict]) -> float:
        d = haversine_km(depot[0], depot[1], r[0]['lat'], r[0]['lng'])
        for i in range(len(r) - 1):
            d += haversine_km(r[i]['lat'], r[i]['lng'], r[i + 1]['lat'], r[i + 1]['lng'])
        return d

    improved = True
    while improved:
        improved = False
        best_distance = total_dist(route)
        for i in range(len(route) - 1):
            for j in range(i + 1, len(route)):
                new_route = route[:i] + list(reversed(route[i:j + 1])) + route[j + 1:]
                new_dist = total_dist(new_route)
                if new_dist < best_distance - 0.01:  # 10m tolerance
                    route = new_route
                    best_distance = new_dist
                    improved = True
                    break
            if improved:
                break

    # Recalculate dist_from_prev after 2-opt
    prev_lat, prev_lng = depot
    for s in route:
        s['dist_from_prev'] = round(haversine_km(prev_lat, prev_lng, s['lat'], s['lng']), 2)
        prev_lat, prev_lng = s['lat'], s['lng']

    return route


def optimize_route(depot: Tuple[float, float], stops: List[dict]) -> List[dict]:
    """NN followed by 2-opt."""
    route = _nn_route(depot, stops)
    return _two_opt(route, depot)


# ════════════════════════════════════════════════════════════════════
# 3. Business-day helpers
# ════════════════════════════════════════════════════════════════════
def next_business_days(start: date, count: int) -> List[date]:
    """Return the next `count` weekdays starting from the day after `start`."""
    days: List[date] = []
    current = start
    while len(days) < count:
        current += timedelta(days=1)
        if current.weekday() < 5:  # Mon=0 … Fri=4
            days.append(current)
    return days


def next_delivery_days(start: date, count: int, allowed_weekdays: Optional[List[int]] = None) -> List[date]:
    """Return the next delivery dates based on seller-selected weekdays."""
    if not allowed_weekdays:
        allowed_weekdays = [0, 1, 2, 3, 4]

    allowed = {int(day) for day in allowed_weekdays if 0 <= int(day) <= 6}
    if not allowed:
        allowed = {0, 1, 2, 3, 4}

    days: List[date] = []
    current = start
    while len(days) < count:
        current += timedelta(days=1)
        if current.weekday() in allowed:
            days.append(current)
    return days


# ════════════════════════════════════════════════════════════════════
# 4. Coordinate resolver
# ════════════════════════════════════════════════════════════════════
def _resolve_customer_coords(customer) -> Tuple[Optional[float], Optional[float], str]:
    """
    Returns (lat, lng, source) where source is 'exact' | 'district_fallback' | None.
    """
    try:
        addr = customer.customer_address
        if addr.latitude and addr.longitude:
            return float(addr.latitude), float(addr.longitude), 'exact'
        # Fallback: district center
        if addr.district and addr.district.center_lat and addr.district.center_lng:
            return float(addr.district.center_lat), float(addr.district.center_lng), 'district_fallback'
    except CustomerAddress.DoesNotExist:
        pass
    return None, None, 'missing'


def _find_existing_active_delivery(customer_id: int, start_date: date) -> Optional[Delivery]:
    """Return the earliest open delivery for this customer, if one is already planned."""
    return Delivery.objects.filter(
        assignment__customer_id=customer_id,
        scheduled_date__gte=start_date,
        status__in=['WAITING', 'OUT_FOR_DELIVERY'],
    ).select_related(
        'assignment__customer',
        'route_stop__route',
    ).order_by('scheduled_date', 'id').first()


# ════════════════════════════════════════════════════════════════════
# 5. Main pipeline
# ════════════════════════════════════════════════════════════════════
def generate_auto_plan(
    start_date: Optional[date] = None,
    *,
    allowed_weekdays: Optional[List[int]] = None,
    max_hours_per_day: Optional[float] = None,
    depot_id: Optional[int] = None,
    assignment_ids: Optional[List[int]] = None,
) -> Dict[str, Any]:
    """
    Build a multi-day delivery plan preview without writing to DB.

    Returns:
    {
        "days": [
            {
                "date": "2026-05-07",
                "weekday": "Pazartesi",
                "district_names": ["Lefkoşa"],
                "total_distance_km": 42.3,
                "total_duration_min": 95,
                "delivery_count": 8,
                "stops": [ { stop detail } ]
            },
            ...
        ],
        "summary": { "total_deliveries": 30, "total_days": 5, ... },
        "warnings": { "no_coordinates": [...], "over_capacity_days": [...] }
    }
    """
    if start_date is None:
        start_date = date.today()
    daily_limit_hours = float(max_hours_per_day or MAX_HOURS_PER_DAY)

    # ── Step 1: Collect pending assignments ──
    pending = ProductAssignment.objects.filter(
        status__in=['PLANNED', 'PENDING']
    ).exclude(
        delivery__isnull=False
    ).select_related(
        'customer', 'customer__customer_address',
        'customer__customer_address__district',
        'product'
    ).order_by('assigned_at')

    if assignment_ids:
        pending = pending.filter(id__in=assignment_ids)

    if not pending.exists():
        return {
            'days': [],
            'summary': {'total_deliveries': 0, 'total_days': 0},
            'warnings': {},
        }

    # ── Step 2: Resolve coordinates & build stop map ──
    # Group by customer to create logical stops
    customer_stops: Dict[int, dict] = {}  # customer_id -> stop dict
    no_coords: List[int] = []  # assignment IDs with no coords

    for assignment in pending:
        cust = assignment.customer
        cid = cust.id

        if cid not in customer_stops:
            lat, lng, source = _resolve_customer_coords(cust)
            if lat is None:
                no_coords.append(assignment.id)
                continue

            # District name
            district_name = 'Bilinmiyor'
            try:
                district_name = cust.customer_address.district.name if cust.customer_address.district else 'Bilinmiyor'
            except Exception:
                pass

            customer_stops[cid] = {
                'customer_id': cid,
                'customer_name': f"{cust.first_name} {cust.last_name}".strip() or cust.username,
                'lat': lat,
                'lng': lng,
                'coord_source': source,
                'district_name': district_name,
                'preferred_date': None,
                'existing_route_id': None,
                'assignment_ids': [],
                'products': [],
                'total_quantity': 0,
            }
            existing_delivery = _find_existing_active_delivery(cid, start_date)
            if existing_delivery:
                customer_stops[cid]['preferred_date'] = existing_delivery.scheduled_date.isoformat()
                try:
                    customer_stops[cid]['existing_route_id'] = existing_delivery.route_stop.route_id
                except Exception:
                    customer_stops[cid]['existing_route_id'] = None
        elif cid not in customer_stops:
            # Customer was already skipped due to missing coords
            no_coords.append(assignment.id)
            continue

        if cid in customer_stops:
            customer_stops[cid]['assignment_ids'].append(assignment.id)
            customer_stops[cid]['products'].append({
                'assignment_id': assignment.id,
                'product_id': assignment.product.id,
                'product_name': assignment.product.name,
                'quantity': assignment.quantity,
            })
            customer_stops[cid]['total_quantity'] += assignment.quantity

    stops_list = list(customer_stops.values())

    if not stops_list:
        return {
            'days': [],
            'summary': {'total_deliveries': 0, 'total_days': 0},
            'warnings': {'no_coordinates': no_coords},
        }

    # ── Step 3: Group by district ──
    anchored_stops = [s for s in stops_list if s.get('preferred_date')]
    unanchored_stops = [s for s in stops_list if not s.get('preferred_date')]

    district_groups: Dict[str, List[dict]] = defaultdict(list)
    for stop in unanchored_stops:
        district_groups[stop['district_name']].append(stop)

    # ── Step 4: Distribute to business days ──
    # Sort districts by stop count (descending) for balanced distribution
    sorted_districts = sorted(district_groups.items(), key=lambda x: -len(x[1]))

    # Calculate how many days we need
    total_deliveries = sum(
        sum(len(s['assignment_ids']) for s in stops)
        for _, stops in sorted_districts
    )
    min_days_needed = math.ceil(total_deliveries / MAX_DELIVERIES_PER_DAY)
    # At least 1 day, at most we'll expand if needed
    num_days = max(1, min_days_needed)

    business_days = next_delivery_days(start_date, num_days, allowed_weekdays)

    # Distribute: fill each day until capacity, district by district
    day_plan: List[Dict[str, Any]] = [
        {
            'date': d.isoformat(),
            'weekday': ['Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi', 'Pazar'][d.weekday()],
            'district_names': [],
            'stops': [],
            'delivery_count': 0,
        }
        for d in business_days
    ]
    day_by_date = {day['date']: day for day in day_plan}

    for stop in anchored_stops:
        preferred_date = stop['preferred_date']
        if preferred_date not in day_by_date:
            preferred_day = date.fromisoformat(preferred_date)
            day_by_date[preferred_date] = {
                'date': preferred_date,
                'weekday': ['Pazartesi', 'SalÄ±', 'Ã‡arÅŸamba', 'PerÅŸembe', 'Cuma', 'Cumartesi', 'Pazar'][preferred_day.weekday()],
                'district_names': [],
                'stops': [],
                'delivery_count': 0,
                'has_existing_route': True,
            }
            day_plan.append(day_by_date[preferred_date])

        target_day = day_by_date[preferred_date]
        target_day['stops'].append(stop)
        target_day['delivery_count'] += len(stop['assignment_ids'])
        target_day['has_existing_route'] = bool(stop.get('existing_route_id')) or target_day.get('has_existing_route', False)
        if stop['district_name'] not in target_day['district_names']:
            target_day['district_names'].append(stop['district_name'])

    day_idx = 0
    for district_name, stops in sorted_districts:
        remaining_stops = list(stops)

        while remaining_stops:
            # If current day is full, move to next
            while day_idx < len(day_plan) and day_plan[day_idx]['delivery_count'] >= MAX_DELIVERIES_PER_DAY:
                day_idx += 1

            # If we ran out of days, add more
            if day_idx >= len(day_plan):
                extra_days = next_delivery_days(business_days[-1], 1, allowed_weekdays)
                business_days.extend(extra_days)
                day_plan.append({
                    'date': extra_days[0].isoformat(),
                    'weekday': ['Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi', 'Pazar'][extra_days[0].weekday()],
                    'district_names': [],
                    'stops': [],
                    'delivery_count': 0,
                })

            capacity_left = MAX_DELIVERIES_PER_DAY - day_plan[day_idx]['delivery_count']
            # Take as many stops as fit (each stop = number of assignments)
            batch = []
            batch_count = 0
            new_remaining = []
            for s in remaining_stops:
                assignment_count = len(s['assignment_ids'])
                if batch_count + assignment_count <= capacity_left:
                    batch.append(s)
                    batch_count += assignment_count
                else:
                    new_remaining.append(s)
            remaining_stops = new_remaining

            if batch:
                day_plan[day_idx]['stops'].extend(batch)
                day_plan[day_idx]['delivery_count'] += batch_count
                if district_name not in day_plan[day_idx]['district_names']:
                    day_plan[day_idx]['district_names'].append(district_name)

            if remaining_stops:
                day_idx += 1

    # ── Step 5: Optimize routes per day ──
    # Get default depot
    depot_lat, depot_lng = 35.1856, 33.3823  # Lefkoşa default
    default_depot = DepotLocation.objects.filter(id=depot_id).first() if depot_id else None
    if not default_depot:
        default_depot = DepotLocation.objects.filter(is_default=True).first()
    if default_depot:
        depot_lat = float(default_depot.latitude)
        depot_lng = float(default_depot.longitude)

    over_time_days = []

    for day in day_plan:
        if not day['stops']:
            continue

        optimized = optimize_route((depot_lat, depot_lng), day['stops'])
        day['stops'] = optimized

        # Calculate totals
        total_dist = sum(s['dist_from_prev'] for s in optimized)
        driving_min = (total_dist / AVG_SPEED_KMH) * 60
        stop_min = len(optimized) * STOP_DURATION_MIN
        total_min = int(driving_min + stop_min)

        day['total_distance_km'] = round(total_dist, 2)
        day['total_duration_min'] = total_min
        day['max_duration_min'] = int(daily_limit_hours * 60)

        if total_min > daily_limit_hours * 60:
            over_time_days.append(day['date'])

        # Add stop_order
        for idx, stop in enumerate(optimized, 1):
            stop['stop_order'] = idx

    # ── Step 6: Remove empty days ──
    day_plan = [d for d in day_plan if d['stops']]

    # ── Build response ──
    warnings: Dict[str, Any] = {}
    if no_coords:
        warnings['no_coordinates'] = no_coords
    if over_time_days:
        warnings['over_time_days'] = over_time_days

    return {
        'days': day_plan,
        'summary': {
            'total_deliveries': sum(d['delivery_count'] for d in day_plan),
            'total_days': len(day_plan),
            'total_distance_km': round(sum(d.get('total_distance_km', 0) for d in day_plan), 2),
            'max_hours_per_day': daily_limit_hours,
            'allowed_weekdays': sorted(list({int(day) for day in (allowed_weekdays or [0, 1, 2, 3, 4])})),
            'depot_id': default_depot.id if default_depot else None,
            'depot_name': default_depot.name if default_depot else "Beko Mağaza, Lefkoşa",
        },
        'warnings': warnings,
    }


# ════════════════════════════════════════════════════════════════════
# 6. Plan approval — writes to DB
# ════════════════════════════════════════════════════════════════════
def recalculate_route_metrics(route) -> None:
    """Recalculate per-stop distances and route totals from stored coordinates."""
    from django.utils import timezone

    depot_lat = float(route.store_lat or 35.1856)
    depot_lng = float(route.store_lng or 33.3823)
    prev_lat, prev_lng = depot_lat, depot_lng
    total_distance = 0.0
    stop_count = 0

    stops = route.stops.select_related('delivery').order_by('stop_order', 'id')
    for stop in stops:
        stop_count += 1
        delivery = stop.delivery
        if delivery.address_lat is None or delivery.address_lng is None:
            distance = float(stop.distance_from_previous_km or 0)
        else:
            cur_lat = float(delivery.address_lat)
            cur_lng = float(delivery.address_lng)
            distance = haversine_km(prev_lat, prev_lng, cur_lat, cur_lng)
            prev_lat, prev_lng = cur_lat, cur_lng

        duration = int((distance / AVG_SPEED_KMH) * 60) + STOP_DURATION_MIN
        stop.distance_from_previous_km = round(distance, 2)
        stop.duration_from_previous_min = duration
        stop.save(update_fields=['distance_from_previous_km', 'duration_from_previous_min'])
        total_distance += distance

    route.total_distance_km = round(total_distance, 2)
    route.total_duration_min = int((total_distance / AVG_SPEED_KMH) * 60) + (stop_count * STOP_DURATION_MIN)
    route.is_optimized = True
    route.optimized_at = timezone.now()
    route.save(update_fields=['total_distance_km', 'total_duration_min', 'is_optimized', 'optimized_at'])


def optimize_persisted_route(route) -> None:
    """
    Reorder an already saved route by customer-level stops.

    A customer can have multiple product deliveries on the same route. They must
    stay consecutive because physically this is one address visit.
    """
    stops = list(route.stops.select_related(
        'delivery',
        'delivery__assignment',
        'delivery__assignment__customer',
    ).order_by('stop_order', 'id'))

    if not stops:
        recalculate_route_metrics(route)
        return

    depot = (float(route.store_lat or 35.1856), float(route.store_lng or 33.3823))
    grouped = {}
    for route_stop in stops:
        delivery = route_stop.delivery
        assignment = delivery.assignment if delivery else None
        customer_id = assignment.customer_id if assignment else None
        key = ('customer', customer_id) if customer_id else ('stop', route_stop.id)

        lat = float(delivery.address_lat) if delivery and delivery.address_lat is not None else depot[0]
        lng = float(delivery.address_lng) if delivery and delivery.address_lng is not None else depot[1]

        if key not in grouped:
            grouped[key] = {
                'key': key,
                'lat': lat,
                'lng': lng,
                'stops': [],
            }
        grouped[key]['stops'].append(route_stop)

    optimized_groups = optimize_route(depot, list(grouped.values()))

    # Avoid unique_together(route, stop_order) conflicts while re-numbering.
    temp_offset = 100000
    for idx, route_stop in enumerate(stops, 1):
        route_stop.stop_order = temp_offset + idx
        route_stop.save(update_fields=['stop_order'])

    order = 0
    for group in optimized_groups:
        for route_stop in sorted(group['stops'], key=lambda item: (item.stop_order, item.id)):
            order += 1
            route_stop.stop_order = order
            route_stop.save(update_fields=['stop_order'])
            if route_stop.delivery:
                route_stop.delivery.delivery_order = order
                route_stop.delivery.save(update_fields=['delivery_order'])

    recalculate_route_metrics(route)


def approve_plan(plan_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Takes the preview plan and creates Delivery + DeliveryRoute + DeliveryRouteStop records.
    Returns a summary of what was created.
    """
    from django.utils import timezone
    from django.db.models import Max
    from ..models import Delivery, DeliveryRoute, DeliveryRouteStop

    depot_lat, depot_lng = 35.1856, 33.3823
    store_address = "Beko Mağaza, Lefkoşa"
    depot_id = plan_data.get('depot_id')
    default_depot = DepotLocation.objects.filter(id=depot_id).first() if depot_id else None
    if not default_depot:
        default_depot = DepotLocation.objects.filter(is_default=True).first()
    if default_depot:
        depot_lat = float(default_depot.latitude)
        depot_lng = float(default_depot.longitude)
        store_address = default_depot.name

    created_routes = []

    for day in plan_data.get('days', []):
        day_date = day['date']

        # Verify assignments are still PLANNED
        all_assignment_ids = []
        for stop in day.get('stops', []):
            all_assignment_ids.extend(stop.get('assignment_ids', []))

        if not all_assignment_ids:
            continue

        valid_assignments = ProductAssignment.objects.filter(
            id__in=all_assignment_ids,
            status__in=['PLANNED', 'PENDING'],
        ).exclude(
            delivery__isnull=False
        )

        valid_ids = set(valid_assignments.values_list('id', flat=True))
        if not valid_ids:
            continue

        existing_route_id = next((s.get('existing_route_id') for s in day.get('stops', []) if s.get('existing_route_id')), None)
        route = DeliveryRoute.objects.filter(id=existing_route_id).first() if existing_route_id else None
        if not route:
            route = DeliveryRoute.objects.filter(date=day_date, status='PLANNED').order_by('id').first()

        route_created = False
        if not route:
            route = DeliveryRoute.objects.create(
                date=day_date,
                store_address=store_address,
                store_lat=depot_lat,
                store_lng=depot_lng,
                total_distance_km=day.get('total_distance_km', 0),
                total_duration_min=day.get('total_duration_min', 0),
                is_optimized=True,
                optimized_at=timezone.now(),
                status='PLANNED',
            )
            route_created = True
        else:
            route.total_distance_km = max(float(route.total_distance_km or 0), float(day.get('total_distance_km', 0) or 0))
            route.total_duration_min = max(int(route.total_duration_min or 0), int(day.get('total_duration_min', 0) or 0))
            route.is_optimized = True
            route.optimized_at = timezone.now()
            route.save(update_fields=['total_distance_km', 'total_duration_min', 'is_optimized', 'optimized_at'])

        stop_order = route.stops.aggregate(Max('stop_order'))['stop_order__max'] or 0
        for stop in day.get('stops', []):
            for product_info in stop.get('products', []):
                aid = product_info['assignment_id']
                if aid not in valid_ids:
                    continue

                stop_order += 1
                assignment = ProductAssignment.objects.get(id=aid)

                # Create Delivery with snapshot data
                delivery = Delivery.objects.create(
                    assignment=assignment,
                    scheduled_date=day_date,
                    address_lat=stop.get('lat'),
                    address_lng=stop.get('lng'),
                    status='WAITING',
                    delivery_order=stop_order,
                    depot=default_depot,
                )

                # Snapshot customer info
                try:
                    addr = assignment.customer.customer_address
                    parts = []
                    if addr.open_address:
                        parts.append(addr.open_address)
                    if addr.area:
                        parts.append(addr.area.name)
                    if addr.district:
                        parts.append(addr.district.name)
                    delivery.address = ", ".join(parts) if parts else ""
                    delivery.address_snapshot = delivery.address
                except Exception:
                    pass
                delivery.customer_phone_snapshot = assignment.customer.phone_number or ""
                delivery.save()

                # Create route stop
                DeliveryRouteStop.objects.create(
                    route=route,
                    delivery=delivery,
                    stop_order=stop_order,
                    distance_from_previous_km=stop.get('dist_from_prev', 0),
                    duration_from_previous_min=int((stop.get('dist_from_prev', 0) / AVG_SPEED_KMH) * 60) + STOP_DURATION_MIN,
                )

                # Update assignment status
                assignment.status = 'SCHEDULED'
                assignment.save(update_fields=['status'])

        optimize_persisted_route(route)

        created_routes.append({
            'route_id': route.id,
            'date': day_date,
            'stop_count': route.stops.count(),
            'merged_into_existing': not route_created,
        })

    return {
        'created_routes': created_routes,
        'total_routes': len(created_routes),
    }
