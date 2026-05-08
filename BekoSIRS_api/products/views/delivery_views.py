from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Q, Count, Prefetch
from django.db import transaction
from datetime import date as date_type, timedelta
import math
from ..models import Delivery, DeliveryRoute, DeliveryRouteStop, ProductAssignment, ProductOwnership, CustomUser, DepotLocation, Notification
from ..serializers import (
    DeliverySerializer, 
    DeliveryRouteSerializer, 
    ProductAssignmentSerializer
)
from ..permissions import IsAdminOrReadOnly, IsDeliveryPerson, IsAdmin


def _assignment_status_filter(status_value):
    """Return a tolerant status filter while old data is being normalized."""
    if status_value == 'PLANNED':
        return Q(status='PLANNED') | Q(status='PENDING')
    if status_value == 'DELIVERED':
        return Q(status='DELIVERED') | Q(status='delivered')
    return Q(status=status_value)


def sync_delivery_business_state(delivery, new_status=None):
    """Keep Delivery, ProductAssignment, ownership and notifications in sync."""
    status_value = new_status or delivery.status
    assignment = delivery.assignment
    if not assignment:
        return

    if status_value == 'DELIVERED':
        delivery.delivered_at = delivery.delivered_at or timezone.now()
        assignment.status = 'DELIVERED'
        assignment.save(update_fields=['status'])
        ProductOwnership.objects.get_or_create(
            customer=assignment.customer,
            product=assignment.product,
            defaults={'purchase_date': timezone.now().date()}
        )
        Notification.objects.get_or_create(
            user=assignment.customer,
            notification_type='general',
            title='Ürününüz Teslim Edildi',
            related_product=assignment.product,
            defaults={
                'message': (
                    f"{assignment.product.name} ürününüz başarıyla teslim edildi. "
                    f"Artık ürününüzü 'Ürünlerim' bölümünden görebilirsiniz."
                )
            }
        )
    elif status_value == 'OUT_FOR_DELIVERY':
        assignment.status = 'OUT_FOR_DELIVERY'
        assignment.save(update_fields=['status'])
    elif status_value in ['WAITING', 'FAILED']:
        assignment.status = 'SCHEDULED'
        assignment.save(update_fields=['status'])


class IsAdminOrSellerOrReadOnly(IsAdminOrReadOnly):
    """Allow delivery operations to admins and sellers; keep reads open as before."""
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_authenticated and request.user.role in ['admin', 'seller']


# ============================================
# Haversine Distance Calculator
# ============================================
def haversine_km(lat1, lon1, lat2, lon2):
    """İki koordinat arasındaki mesafeyi km olarak hesaplar."""
    R = 6371  # Earth radius in km
    lat1, lon1, lat2, lon2 = map(math.radians, [float(lat1), float(lon1), float(lat2), float(lon2)])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    return R * c


def nearest_neighbor_route(depot_lat, depot_lng, deliveries_with_coords):
    """
    Nearest-Neighbor algoritması ile en kısa rota sıralaması.
    deliveries_with_coords: [(delivery_obj, lat, lng), ...]
    Returns: ordered list of (delivery_obj, lat, lng, distance_from_prev)
    """
    if not deliveries_with_coords:
        return []
    
    unvisited = list(deliveries_with_coords)
    route = []
    current_lat, current_lng = float(depot_lat), float(depot_lng)
    
    while unvisited:
        nearest = None
        nearest_dist = float('inf')
        for item in unvisited:
            d_obj, lat, lng = item
            dist = haversine_km(current_lat, current_lng, lat, lng)
            if dist < nearest_dist:
                nearest_dist = dist
                nearest = item
        
        unvisited.remove(nearest)
        route.append((nearest[0], nearest[1], nearest[2], nearest_dist))
        current_lat, current_lng = float(nearest[1]), float(nearest[2])
    
    return route


# ============================================
# ProductAssignment ViewSet
# ============================================
class ProductAssignmentViewSet(viewsets.ModelViewSet):
    queryset = ProductAssignment.objects.select_related('customer', 'product').all()
    serializer_class = ProductAssignmentSerializer
    permission_classes = [IsAdminOrSellerOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['customer__username', 'customer__first_name', 'customer__last_name', 'product__name', 'product__model_code']
    ordering_fields = ['assigned_at', 'status']

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        # Customers only see their own assignments
        if hasattr(user, 'role') and user.role == 'customer':
            qs = qs.filter(customer=user)
        # Filter by customer id for admin/seller usage (e.g. ?customer=5)
        customer_id = self.request.query_params.get('customer')
        if customer_id:
            qs = qs.filter(customer_id=customer_id)
        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(_assignment_status_filter(status_param))
        return qs

    def perform_create(self, serializer):
        assignment = serializer.save(assigned_by=self.request.user if self.request.user.is_authenticated else None)
        # Notify customer that a product has been assigned to them
        Notification.objects.create(
            user=assignment.customer,
            notification_type='general',
            title='Yeni Ürün Ataması',
            message=(
                f"{assignment.product.name} ürünü size atandı. "
                f"Teslimat planlandığında bildirim alacaksınız."
            ),
            related_product=assignment.product,
        )

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Her durum için atama sayısını döndürür."""
        qs = ProductAssignment.objects.aggregate(
            planned=Count('id', filter=_assignment_status_filter('PLANNED')),
            scheduled=Count('id', filter=_assignment_status_filter('SCHEDULED')),
            out_for_delivery=Count('id', filter=_assignment_status_filter('OUT_FOR_DELIVERY')),
            delivered=Count('id', filter=_assignment_status_filter('DELIVERED')),
        )
        return Response(qs)

    @action(detail=True, methods=['post'])
    def schedule_delivery(self, request, pk=None):
        """
        Tek bir atama için teslimat tarihi belirle.
        Body: { "scheduled_date": "2026-03-10", "address": "optional override" }
        """
        assignment = self.get_object()
        scheduled_date = request.data.get('scheduled_date')
        
        if not scheduled_date:
            return Response({"error": "scheduled_date gerekli."}, status=status.HTTP_400_BAD_REQUEST)
        
        # Eğer zaten bir Delivery varsa güncelle, yoksa oluştur
        delivery, created = Delivery.objects.get_or_create(
            assignment=assignment,
            defaults={
                'scheduled_date': scheduled_date,
                'address': request.data.get('address', ''),
                'status': 'WAITING',
            }
        )
        
        if not created:
            delivery.scheduled_date = scheduled_date
            if request.data.get('address'):
                delivery.address = request.data['address']
            delivery.save()
        
        # Assignment durumunu güncelle
        assignment.status = 'SCHEDULED'
        assignment.save()
        
        return Response(ProductAssignmentSerializer(assignment).data)

    @action(detail=False, methods=['post'])
    def batch_schedule(self, request):
        """
        Birden fazla atamaya aynı tarihte teslimat planla.
        Body: { "assignment_ids": [1, 2, 3], "scheduled_date": "2026-03-10" }
        """
        assignment_ids = request.data.get('assignment_ids', [])
        scheduled_date = request.data.get('scheduled_date')
        
        if not assignment_ids or not scheduled_date:
            return Response(
                {"error": "assignment_ids ve scheduled_date gerekli."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        assignments = ProductAssignment.objects.filter(id__in=assignment_ids)
        scheduled_count = 0
        
        for assignment in assignments:
            delivery, created = Delivery.objects.get_or_create(
                assignment=assignment,
                defaults={
                    'scheduled_date': scheduled_date,
                    'status': 'WAITING',
                }
            )
            if not created:
                delivery.scheduled_date = scheduled_date
                delivery.save()
            
            assignment.status = 'SCHEDULED'
            assignment.save()
            scheduled_count += 1
        
        return Response({
            "message": f"{scheduled_count} atama planlandı.",
            "scheduled_count": scheduled_count
        })

    @action(detail=False, methods=['post'])
    def auto_plan(self, request):
        """
        Otomatik teslimat planı oluştur (Preview — DB'ye yazmaz).
        Body: { "start_date": "2026-05-06" }  (optional, default=today)
        """
        from ..services.auto_planner import generate_auto_plan
        from datetime import date as date_type

        start_date_str = request.data.get('start_date')
        start_date = None
        if start_date_str:
            try:
                start_date = date_type.fromisoformat(start_date_str)
            except ValueError:
                return Response(
                    {"error": "Geçersiz tarih formatı. YYYY-MM-DD kullanın."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        plan = generate_auto_plan(
            start_date,
            allowed_weekdays=request.data.get('allowed_weekdays') or None,
            max_hours_per_day=request.data.get('max_hours_per_day') or None,
            depot_id=request.data.get('depot_id') or None,
            assignment_ids=request.data.get('assignment_ids') or None,
        )

        if not plan.get('days'):
            return Response(
                {"error": "Planlanacak teslimat bulunamadı. Tüm atamalar zaten planlanmış olabilir."},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response(plan)

    @action(detail=False, methods=['post'])
    def approve_plan(self, request):
        """
        Otomatik planı onayla ve Delivery + Route kayıtlarını oluştur.
        Body: { "days": [...] }  (auto_plan'dan dönen days verisi)
        """
        from ..services.auto_planner import approve_plan

        days = request.data.get('days')
        if not days:
            return Response(
                {"error": "Plan verisi (days) gerekli."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            result = approve_plan({
                'days': days,
                'depot_id': request.data.get('depot_id') or request.data.get('summary', {}).get('depot_id'),
            })
        except Exception as e:
            return Response(
                {"error": f"Plan onaylanırken hata oluştu: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response({
            "message": f"{result['total_routes']} günlük teslimat planı oluşturuldu.",
            **result
        })


# ============================================
# Delivery ViewSet
# ============================================
class DeliveryViewSet(viewsets.ModelViewSet):
    queryset = Delivery.objects.select_related(
        'assignment', 'assignment__customer', 'assignment__product'
    ).all()
    serializer_class = DeliverySerializer
    permission_classes = [IsAdminOrSellerOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['status', 'assignment__customer__username', 'assignment__customer__first_name', 'assignment__customer__last_name']
    ordering_fields = ['scheduled_date', 'delivery_order', 'status']

    def get_queryset(self):
        qs = super().get_queryset()
        # Tarihe göre filtreleme
        date = self.request.query_params.get('date')
        if date:
            qs = qs.filter(scheduled_date=date)
        # Duruma göre filtreleme
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Teslimat istatistikleri."""
        qs = Delivery.objects.aggregate(
            waiting=Count('id', filter=Q(status='WAITING')),
            out_for_delivery=Count('id', filter=Q(status='OUT_FOR_DELIVERY')),
            delivered=Count('id', filter=Q(status='DELIVERED')),
            failed=Count('id', filter=Q(status='FAILED')),
        )
        selected_date = request.query_params.get('date')
        scheduled_qs = Delivery.objects.all()
        if selected_date:
            scheduled_qs = scheduled_qs.filter(scheduled_date=selected_date)
        qs.update({
            'waiting_count': qs['waiting'],
            'out_for_delivery_count': qs['out_for_delivery'],
            'delivered_count': qs['delivered'],
            'failed_count': qs['failed'],
            'scheduled_for_selected_date_count': scheduled_qs.count(),
            'delivered_last_10_days_count': Delivery.objects.filter(
                status='DELIVERED',
                delivered_at__gte=timezone.now() - timedelta(days=10)
            ).count(),
        })
        return Response(qs)

    def perform_update(self, serializer):
        delivery = serializer.save()
        sync_delivery_business_state(delivery)
        if delivery.status == 'DELIVERED' and delivery.delivered_at:
            delivery.save(update_fields=['delivered_at'])

    @action(detail=False, methods=['get'])
    def by_date(self, request):
        """Belirli tarihteki teslimatları getirir."""
        date = request.query_params.get('date')
        if not date:
            return Response({"error": "date parametresi gerekli."}, status=status.HTTP_400_BAD_REQUEST)
        
        deliveries = Delivery.objects.filter(
            scheduled_date=date
        ).select_related(
            'assignment', 'assignment__customer', 'assignment__product'
        ).order_by('delivery_order')
        
        serializer = DeliverySerializer(deliveries, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def assign_driver(self, request):
        """
        Seçili teslimatları bir delivery person'a ata.
        Body: { "delivery_ids": [1, 2, 3], "driver_id": 5 }
        """
        delivery_ids = request.data.get('delivery_ids', [])
        driver_id = request.data.get('driver_id')
        
        if not delivery_ids or not driver_id:
            return Response(
                {"error": "delivery_ids ve driver_id gerekli."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            driver = CustomUser.objects.get(id=driver_id, role='delivery')
        except CustomUser.DoesNotExist:
            return Response({"error": "Teslimatçı bulunamadı."}, status=status.HTTP_404_NOT_FOUND)
        
        updated = Delivery.objects.filter(id__in=delivery_ids).update(delivered_by=driver)
        
        # Eğer bu teslimatların rotası varsa rotanın driver'ını da güncelle
        routes = DeliveryRoute.objects.filter(
            stops__delivery_id__in=delivery_ids
        ).distinct()
        routes.update(assigned_driver=driver)
        
        return Response({
            "message": f"{updated} teslimat {driver.first_name} {driver.last_name}'e atandı.",
            "updated_count": updated
        })


# ============================================
# DeliveryRoute ViewSet (Rota Optimizasyonu)
# ============================================
class DeliveryRouteViewSet(viewsets.ModelViewSet):
    queryset = DeliveryRoute.objects.select_related('assigned_driver').prefetch_related(
        Prefetch(
            'stops',
            queryset=DeliveryRouteStop.objects.select_related(
                'delivery',
                'delivery__assignment',
                'delivery__assignment__customer',
                'delivery__assignment__customer__customer_address',
                'delivery__assignment__customer__customer_address__area',
                'delivery__assignment__customer__customer_address__district',
                'delivery__assignment__product',
                'delivery__delivered_by',
            ).order_by('stop_order', 'id')
        )
    ).all()
    serializer_class = DeliveryRouteSerializer
    permission_classes = [IsAdminOrSellerOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        date = self.request.query_params.get('date')
        if date:
            qs = qs.filter(date=date)
        return qs

    @action(detail=False, methods=['post'])
    def rebalance_week(self, request):
        """
        Rebuild open delivery plans for a rolling week.
        Only WAITING deliveries and unscheduled PLANNED assignments are touched;
        out-for-delivery/completed items stay as-is.
        """
        from ..services.auto_planner import generate_auto_plan, approve_plan

        week_start_raw = request.data.get('week_start') or date_type.today().isoformat()
        try:
            week_start = date_type.fromisoformat(week_start_raw)
        except ValueError:
            return Response({"error": "Geçersiz week_start. YYYY-MM-DD kullanın."}, status=status.HTTP_400_BAD_REQUEST)

        allowed_weekdays = request.data.get('allowed_weekdays') or []
        if not allowed_weekdays:
            return Response({"error": "En az bir aktif teslimat günü seçilmeli."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            allowed_weekday_set = {int(day) for day in allowed_weekdays}
        except (TypeError, ValueError):
            return Response({"error": "allowed_weekdays sayÄ±sal deÄŸerler iÃ§ermeli."}, status=status.HTTP_400_BAD_REQUEST)

        allowed_weekday_set = {day for day in allowed_weekday_set if 0 <= day <= 6}
        if not allowed_weekday_set:
            return Response({"error": "En az bir geÃ§erli aktif teslimat gÃ¼nÃ¼ seÃ§ilmeli."}, status=status.HTTP_400_BAD_REQUEST)

        week_end = week_start + timedelta(days=13)

        with transaction.atomic():
            open_deliveries = list(Delivery.objects.filter(
                scheduled_date__gte=week_start,
                scheduled_date__lte=week_end,
                status='WAITING',
            ).select_related('assignment'))
            deliveries_to_move = [
                delivery for delivery in open_deliveries
                if delivery.scheduled_date and delivery.scheduled_date.weekday() not in allowed_weekday_set
            ]
            movable_delivery_ids = [delivery.id for delivery in deliveries_to_move]
            movable_assignment_ids = [
                delivery.assignment_id for delivery in deliveries_to_move
                if delivery.assignment_id
            ]

            if movable_assignment_ids:
                ProductAssignment.objects.filter(id__in=movable_assignment_ids).update(status='PLANNED')

            if movable_delivery_ids:
                DeliveryRouteStop.objects.filter(delivery_id__in=movable_delivery_ids).delete()
                Delivery.objects.filter(id__in=movable_delivery_ids).delete()

            DeliveryRoute.objects.filter(
                date__gte=week_start,
                date__lte=week_end,
                status='PLANNED',
                stops__isnull=True,
            ).delete()

            unscheduled_assignment_ids = list(ProductAssignment.objects.filter(
                status__in=['PLANNED', 'PENDING'],
                delivery__isnull=True,
            ).values_list('id', flat=True))

            assignment_ids = sorted(set(movable_assignment_ids + unscheduled_assignment_ids))
            if not assignment_ids:
                return Response({
                    "message": "Yeniden planlanacak açık teslimat bulunamadı.",
                    "created_routes": [],
                    "total_routes": 0,
                    "moved_deliveries": 0,
                })

            plan = generate_auto_plan(
                week_start - timedelta(days=1),
                allowed_weekdays=sorted(allowed_weekday_set),
                max_hours_per_day=request.data.get('max_hours_per_day') or None,
                depot_id=request.data.get('depot_id') or None,
                assignment_ids=assignment_ids,
            )

            if not plan.get('days'):
                return Response({"error": "Plan oluşturulamadı."}, status=status.HTTP_400_BAD_REQUEST)

            result = approve_plan({
                'days': plan['days'],
                'depot_id': request.data.get('depot_id') or plan.get('summary', {}).get('depot_id'),
            })

        return Response({
            "message": "Haftalık teslimat takvimi yeniden dağıtıldı.",
            "plan": plan,
            "moved_deliveries": len(movable_delivery_ids),
            "planned_assignments": len(assignment_ids),
            **result,
        })

    def destroy(self, request, *args, **kwargs):
        """
        Rotayı siler ve içindeki teslimatları tekrar 'WAITING' (Bekliyor) durumuna getirir.
        """
        route = self.get_object()
        
        # Bu rotaya ait tüm teslimatları bul
        # DeliveryRouteStop üzerinden Delivery'lere ulaş
        delivery_ids = route.stops.values_list('delivery_id', flat=True)
        
        if delivery_ids:
            # 1. Teslimatları sıfırla
            Delivery.objects.filter(id__in=delivery_ids).update(
                status='WAITING',
                delivery_order=0,
                distance_km=None,
                eta_minutes=None,
                route_batch_id=None
            )
            
            # 2. ProductAssignment durumlarını da 'SCHEDULED' (Teslimat Planlandı) veya benzeri bir duruma geri çekmek 
            # mantıklı olabilir çünkü atama yapıldı, rota silindi ama henüz yola çıkmadı. 
            ProductAssignment.objects.filter(
                delivery__id__in=delivery_ids
            ).update(status='SCHEDULED')

        # Son olarak rotayı sil (Cascade ile DeliveryRouteStop'lar otomatik silinecek)
        return super().destroy(request, *args, **kwargs)

    @action(detail=False, methods=['post'])
    def optimize(self, request):
        """
        Seçili teslimatlar için rota optimizasyonu yap.
        Body: {
            "delivery_ids": [1, 2, 3],
            "date": "2026-03-10",
            "depot_id": 1  (optional)
        }
        """
        delivery_ids = request.data.get('delivery_ids', [])
        date = request.data.get('date')
        depot_id = request.data.get('depot_id')
        
        if not delivery_ids or not date:
            return Response(
                {"error": "delivery_ids ve date gerekli."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Depo bilgisi
        depot_lat, depot_lng = 35.1856, 33.3823  # Default: Lefkoşa
        store_address = "Beko Mağaza, Lefkoşa"
        
        if depot_id:
            try:
                depot = DepotLocation.objects.get(id=depot_id)
                depot_lat = float(depot.latitude)
                depot_lng = float(depot.longitude)
                store_address = depot.name
            except DepotLocation.DoesNotExist:
                pass
        else:
            # Varsayılan depo
            default_depot = DepotLocation.objects.filter(is_default=True).first()
            if default_depot:
                depot_lat = float(default_depot.latitude)
                depot_lng = float(default_depot.longitude)
                store_address = default_depot.name
        
        # Teslimatları getir
        deliveries = Delivery.objects.filter(
            id__in=delivery_ids
        ).select_related('assignment__customer', 'assignment__product')
        
        if not deliveries.exists():
            return Response({"error": "Teslimat bulunamadı."}, status=status.HTTP_404_NOT_FOUND)
        
        # Koordinat bilgisi olan teslimatları topla
        deliveries_with_coords = []
        no_coords = []
        
        for delivery in deliveries:
            lat = delivery.address_lat
            lng = delivery.address_lng
            
            # Eğer teslimatın kendi koordinatı yoksa, müşteri adresinden al
            if not lat or not lng:
                customer = delivery.assignment.customer
                try:
                    addr = customer.customer_address
                    lat = addr.latitude
                    lng = addr.longitude
                except Exception:
                    lat = None
                    lng = None
            
            if lat and lng:
                deliveries_with_coords.append((delivery, float(lat), float(lng)))
            else:
                no_coords.append(delivery.id)
        
        if not deliveries_with_coords:
            return Response(
                {"error": "Koordinat bilgisi olan teslimat bulunamadı. Müşteri adreslerine koordinat eklenmeli."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Nearest Neighbor ile rota optimize et
        optimized_route = nearest_neighbor_route(depot_lat, depot_lng, deliveries_with_coords)
        
        # Toplam mesafe ve süre hesapla
        total_distance = sum(item[3] for item in optimized_route)
        avg_speed_kmh = 40  # KKTC koşullarında ortalama hız
        total_duration_min = int((total_distance / avg_speed_kmh) * 60) + len(optimized_route) * 5  # +5dk her durak

        # DeliveryRoute kaydı oluştur
        route = DeliveryRoute.objects.create(
            date=date,
            store_address=store_address,
            store_lat=depot_lat,
            store_lng=depot_lng,
            total_distance_km=round(total_distance, 2),
            total_duration_min=total_duration_min,
            is_optimized=True,
            optimized_at=timezone.now(),
            status='PLANNED'
        )
        
        # DeliveryRouteStop kayıtları oluştur ve teslimat sırasını güncelle
        stops_data = []
        for order, (delivery, lat, lng, dist_from_prev) in enumerate(optimized_route, 1):
            stop = DeliveryRouteStop.objects.create(
                route=route,
                delivery=delivery,
                stop_order=order,
                distance_from_previous_km=round(dist_from_prev, 2),
                duration_from_previous_min=int((dist_from_prev / avg_speed_kmh) * 60) + 5,
            )
            # Teslimat sırası güncelle
            delivery.delivery_order = order
            delivery.save(update_fields=['delivery_order'])
            
            stops_data.append({
                'stop_order': order,
                'delivery_id': delivery.id,
                'customer_name': f"{delivery.assignment.customer.first_name} {delivery.assignment.customer.last_name}",
                'product_name': delivery.assignment.product.name,
                'address': delivery.address or '',
                'lat': lat,
                'lng': lng,
                'distance_from_previous_km': round(dist_from_prev, 2),
                'duration_from_previous_min': int((dist_from_prev / avg_speed_kmh) * 60) + 5,
            })
        
        return Response({
            'route_id': route.id,
            'date': date,
            'total_distance_km': round(total_distance, 2),
            'total_duration_min': total_duration_min,
            'stop_count': len(optimized_route),
            'stops': stops_data,
            'warnings': {
                'no_coordinates': no_coords
            } if no_coords else {}
        })


# ============================================
# DeliveryPerson ViewSet (Mobil App)
# ============================================
class DeliveryPersonViewSet(viewsets.GenericViewSet):
    """
    Viewset specifically for Delivery Personnel to manage their tasks.
    """
    permission_classes = [permissions.IsAuthenticated, IsDeliveryPerson]
    
    def get_queryset(self):
        return Delivery.objects.filter(delivered_by=self.request.user)

    @action(detail=False, methods=['get'])
    def my_route(self, request):
        """
        Get today's active route for the logged-in delivery person.
        Includes route summary and ordered delivery stops.
        """
        today = timezone.now().date()
        
        # Bugünkü rotayı bul
        route = DeliveryRoute.objects.filter(
            assigned_driver=request.user,
            date=today
        ).prefetch_related('stops', 'stops__delivery').first()
        
        # Bugünkü teslimatları getir
        deliveries = Delivery.objects.filter(
            delivered_by=request.user,
            scheduled_date=today
        ).select_related(
            'assignment', 'assignment__customer', 'assignment__customer__customer_address', 'assignment__product'
        ).order_by('delivery_order')
        
        route_info = None
        if route:
            route_info = {
                'id': route.id,
                'total_distance_km': float(route.total_distance_km) if route.total_distance_km else 0,
                'total_duration_min': route.total_duration_min or 0,
                'status': route.status,
                'stop_count': route.stops.count(),
                'completed_count': deliveries.filter(status='DELIVERED').count(),
            }
        
        serializer = DeliverySerializer(deliveries, many=True)
        return Response({
            'route': route_info,
            'deliveries': serializer.data
        })

    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """
        Update the status of a specific delivery.
        """
        try:
            delivery = Delivery.objects.get(pk=pk, delivered_by=request.user)
        except Delivery.DoesNotExist:
            return Response({"error": "Teslimat bulunamadı."}, status=status.HTTP_404_NOT_FOUND)

        new_status = request.data.get('status')
        if new_status == 'ISSUE':
            new_status = 'FAILED'
        if new_status not in dict(Delivery.STATUS_CHOICES):
            return Response({"error": "Geçersiz durum."}, status=status.HTTP_400_BAD_REQUEST)

        delivery.status = new_status
        sync_delivery_business_state(delivery, new_status)
        delivery.save()
        return Response(DeliverySerializer(delivery).data)

        if new_status == 'DELIVERED':
            delivery.delivered_at = timezone.now()
            if delivery.assignment:
                delivery.assignment.status = 'DELIVERED'
                delivery.assignment.save()
                # Müşteri için ProductOwnership oluştur (yoksa)
                ProductOwnership.objects.get_or_create(
                    customer=delivery.assignment.customer,
                    product=delivery.assignment.product,
                    defaults={'purchase_date': timezone.now().date()}
                )
                # Müşteriyi teslim edildi olarak bilgilendir
                Notification.objects.create(
                    user=delivery.assignment.customer,
                    notification_type='general',
                    title='Ürününüz Teslim Edildi',
                    message=(
                        f"{delivery.assignment.product.name} ürününüz başarıyla teslim edildi. "
                        f"Artık ürününüzü 'Ürünlerim' bölümünden görebilirsiniz."
                    ),
                    related_product=delivery.assignment.product,
                )
        elif new_status == 'OUT_FOR_DELIVERY':
            if delivery.assignment:
                delivery.assignment.status = 'OUT_FOR_DELIVERY'
                delivery.assignment.save()
                # Müşteriyi yolda olduğu konusunda bilgilendir
                Notification.objects.create(
                    user=delivery.assignment.customer,
                    notification_type='general',
                    title='Ürününüz Yolda',
                    message=(
                        f"{delivery.assignment.product.name} ürününüz bugün teslim edilmek üzere yola çıktı."
                    ),
                    related_product=delivery.assignment.product,
                )

        delivery.save()
        
        # Rota durumu kontrolü - tüm teslimatlar tamamlandıysa rotayı da kapat
        if new_status == 'DELIVERED':
            try:
                route_stop = delivery.route_stop
                route = route_stop.route
                all_delivered = not route.stops.exclude(
                    delivery__status='DELIVERED'
                ).exists()
                if all_delivered:
                    route.status = 'COMPLETED'
                    route.save()
            except Exception:
                pass
        
        return Response(DeliverySerializer(delivery).data)

    @action(detail=False, methods=['post'])
    def start_route(self, request):
        """
        Teslimatçı rotasını başlatır. Tüm teslimatlar OUT_FOR_DELIVERY olur.
        """
        today = timezone.now().date()
        route = DeliveryRoute.objects.filter(
            assigned_driver=request.user,
            date=today,
            status='PLANNED'
        ).first()
        
        if not route:
            return Response({"error": "Bugün için planlı rota bulunamadı."}, status=status.HTTP_404_NOT_FOUND)
        
        # Rotayı başlat
        route.status = 'IN_PROGRESS'
        route.save()
        
        # Tüm teslimatları yolda olarak işaretle
        delivery_ids = route.stops.values_list('delivery_id', flat=True)
        Delivery.objects.filter(id__in=delivery_ids).update(status='OUT_FOR_DELIVERY')
        ProductAssignment.objects.filter(
            delivery__id__in=delivery_ids
        ).update(status='OUT_FOR_DELIVERY')
        
        return Response({"message": "Rota başlatıldı.", "route_status": "IN_PROGRESS"})
