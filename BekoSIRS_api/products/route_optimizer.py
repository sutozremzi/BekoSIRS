# products/route_optimizer.py
"""
Delivery Route Optimization Service.

Uses Haversine formula for distance calculation and
Nearest Neighbor algorithm for route optimization (simplified TSP).

Features:
1. Calculate distance between coordinates
2. Optimize delivery route for minimal total distance
3. Estimate travel time and fuel cost
4. Group deliveries by zone

Usage:
    from products.route_optimizer import RouteOptimizer
    
    optimizer = RouteOptimizer()
    route = optimizer.optimize_route(stops)
    distance = optimizer.calculate_total_distance(route)
"""

import math
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class Stop:
    """Represents a delivery stop."""
    id: int
    name: str
    address: str
    latitude: float
    longitude: float
    priority: int = 1  # 1=highest, 5=lowest
    time_window_start: Optional[str] = None  # e.g., "09:00"
    time_window_end: Optional[str] = None  # e.g., "18:00"


class RouteOptimizer:
    """
    Route Optimization Engine using Haversine + Nearest Neighbor.
    
    Configuration:
    - EARTH_RADIUS_KM: Earth's radius for Haversine formula
    - AVG_SPEED_KMH: Average vehicle speed for time estimation
    - FUEL_COST_PER_KM: Fuel cost in TL per kilometer
    - STOP_DURATION_MIN: Average time spent at each stop
    """
    
    EARTH_RADIUS_KM = 6371
    AVG_SPEED_KMH = 30  # City traffic average
    FUEL_COST_PER_KM = 2.5  # TL per km
    STOP_DURATION_MIN = 15  # Minutes per delivery
    
    # Default depot location (Beko HQ - example: Istanbul Tuzla)
    DEFAULT_DEPOT = {
        'id': 0,
        'name': 'Depo',
        'address': 'Beko Merkez Depo',
        'latitude': 40.8219,
        'longitude': 29.3094
    }
    
    def __init__(self, depot: Dict = None):
        """
        Initialize RouteOptimizer.
        
        Args:
            depot: Custom depot location dict with latitude/longitude
        """
        self.depot = depot or self.DEFAULT_DEPOT
    
    def haversine_distance(self, lat1: float, lon1: float, 
                           lat2: float, lon2: float) -> float:
        """
        Calculate the great-circle distance between two points using Haversine formula.
        
        Args:
            lat1, lon1: Coordinates of first point
            lat2, lon2: Coordinates of second point
            
        Returns:
            Distance in kilometers
        """
        # Convert to radians
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        # Haversine formula
        a = math.sin(delta_lat / 2) ** 2 + \
            math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        distance = self.EARTH_RADIUS_KM * c
        return round(distance, 2)
    
    def optimize_route(self, stops: List[Dict], 
                       return_to_depot: bool = True) -> Dict:
        """
        Optimize delivery route using Nearest Neighbor algorithm.
        
        This is a greedy approach to the Traveling Salesman Problem (TSP).
        Not optimal but efficient for real-world use.
        
        Args:
            stops: List of stop dicts with id, name, address, latitude, longitude
            return_to_depot: Whether to return to depot at the end
            
        Returns:
            Dict with optimized route, total distance, estimated time, and cost
        """
        if not stops:
            return {
                'route': [],
                'total_distance_km': 0,
                'estimated_time_min': 0,
                'estimated_fuel_cost': 0,
                'message': 'No stops provided'
            }
        
        # Convert dicts to Stop objects if needed
        stop_objects = []
        for s in stops:
            if isinstance(s, dict):
                stop_objects.append(Stop(
                    id=s.get('id', 0),
                    name=s.get('name', ''),
                    address=s.get('address', ''),
                    latitude=s.get('latitude', 0),
                    longitude=s.get('longitude', 0),
                    priority=s.get('priority', 1)
                ))
            else:
                stop_objects.append(s)
        
        # Sort by priority first (higher priority = earlier delivery)
        stop_objects.sort(key=lambda x: x.priority)
        
        # Nearest Neighbor Algorithm
        route = []
        unvisited = stop_objects.copy()
        current_lat = self.depot['latitude']
        current_lon = self.depot['longitude']
        total_distance = 0
        
        # Start from depot
        route.append({
            'order': 0,
            'type': 'start',
            **self.depot,
            'distance_from_prev': 0,
            'cumulative_distance': 0
        })
        
        while unvisited:
            # Find nearest unvisited stop
            nearest = None
            nearest_dist = float('inf')
            
            for stop in unvisited:
                dist = self.haversine_distance(
                    current_lat, current_lon,
                    stop.latitude, stop.longitude
                )
                if dist < nearest_dist:
                    nearest_dist = dist
                    nearest = stop
            
            # Add to route
            total_distance += nearest_dist
            route.append({
                'order': len(route),
                'type': 'delivery',
                'id': nearest.id,
                'name': nearest.name,
                'address': nearest.address,
                'latitude': nearest.latitude,
                'longitude': nearest.longitude,
                'priority': nearest.priority,
                'distance_from_prev': nearest_dist,
                'cumulative_distance': round(total_distance, 2)
            })
            
            # Update current position
            current_lat = nearest.latitude
            current_lon = nearest.longitude
            unvisited.remove(nearest)
        
        # Return to depot if requested
        if return_to_depot:
            return_dist = self.haversine_distance(
                current_lat, current_lon,
                self.depot['latitude'], self.depot['longitude']
            )
            total_distance += return_dist
            route.append({
                'order': len(route),
                'type': 'return',
                **self.depot,
                'distance_from_prev': return_dist,
                'cumulative_distance': round(total_distance, 2)
            })
        
        # Calculate time and cost
        driving_time_min = (total_distance / self.AVG_SPEED_KMH) * 60
        stop_time_min = len(stop_objects) * self.STOP_DURATION_MIN
        total_time_min = driving_time_min + stop_time_min
        fuel_cost = total_distance * self.FUEL_COST_PER_KM
        
        return {
            'route': route,
            'stops_count': len(stop_objects),
            'total_distance_km': round(total_distance, 2),
            'driving_time_min': round(driving_time_min),
            'stop_time_min': stop_time_min,
            'total_time_min': round(total_time_min),
            'total_time_hours': round(total_time_min / 60, 1),
            'estimated_fuel_cost': round(fuel_cost, 2),
            'optimization_method': 'Nearest Neighbor (Greedy TSP)',
            'depot': self.depot
        }
    
    def calculate_distance_matrix(self, stops: List[Dict]) -> List[List[float]]:
        """
        Calculate distance matrix between all stops.
        
        Returns:
            2D list where matrix[i][j] is distance from stop i to stop j
        """
        n = len(stops)
        matrix = [[0.0] * n for _ in range(n)]
        
        for i in range(n):
            for j in range(n):
                if i != j:
                    matrix[i][j] = self.haversine_distance(
                        stops[i]['latitude'], stops[i]['longitude'],
                        stops[j]['latitude'], stops[j]['longitude']
                    )
        
        return matrix
    
    def group_by_zone(self, stops: List[Dict], 
                      zone_radius_km: float = 5.0) -> Dict[str, List[Dict]]:
        """
        Group stops by zones based on proximity.
        
        Args:
            stops: List of stops
            zone_radius_km: Maximum radius for a zone
            
        Returns:
            Dict mapping zone names to lists of stops
        """
        if not stops:
            return {}
        
        zones = {}
        assigned = set()
        zone_count = 1
        
        for stop in stops:
            if stop['id'] in assigned:
                continue
            
            # Create new zone centered on this stop
            zone_name = f"Zone {zone_count}"
            zones[zone_name] = [stop]
            assigned.add(stop['id'])
            
            # Find nearby stops
            for other in stops:
                if other['id'] in assigned:
                    continue
                    
                dist = self.haversine_distance(
                    stop['latitude'], stop['longitude'],
                    other['latitude'], other['longitude']
                )
                
                if dist <= zone_radius_km:
                    zones[zone_name].append(other)
                    assigned.add(other['id'])
            
            zone_count += 1
        
        return zones
    
    def estimate_delivery_windows(self, route: List[Dict], 
                                   start_time: str = "09:00") -> List[Dict]:
        """
        Estimate arrival times for each stop.
        
        Args:
            route: Optimized route from optimize_route()
            start_time: Start time in HH:MM format
            
        Returns:
            Route with estimated arrival times
        """
        start_hour, start_min = map(int, start_time.split(':'))
        current_time_min = start_hour * 60 + start_min
        
        for stop in route:
            # Add travel time
            travel_time = (stop['distance_from_prev'] / self.AVG_SPEED_KMH) * 60
            current_time_min += travel_time
            
            # Format arrival time
            hours = int(current_time_min // 60) % 24
            mins = int(current_time_min % 60)
            stop['estimated_arrival'] = f"{hours:02d}:{mins:02d}"
            
            # Add stop duration for non-depot stops
            if stop['type'] == 'delivery':
                current_time_min += self.STOP_DURATION_MIN
                hours = int(current_time_min // 60) % 24
                mins = int(current_time_min % 60)
                stop['estimated_departure'] = f"{hours:02d}:{mins:02d}"
        
        return route


# Utility functions for integration with Delivery model
def optimize_deliveries_for_date(delivery_date, depot: Dict = None):
    """
    Optimize all deliveries for a specific date.
    
    Usage:
        from products.route_optimizer import optimize_deliveries_for_date
        result = optimize_deliveries_for_date(date.today())
    """
    from .models import Delivery
    
    deliveries = Delivery.objects.filter(
        scheduled_date=delivery_date,
        status__in=['pending', 'confirmed']
    ).select_related('customer', 'product_ownership__product')
    
    if not deliveries.exists():
        return {'message': 'No deliveries for this date', 'route': []}
    
    stops = []
    for d in deliveries:
        # Try to get coordinates from customer address
        # In real implementation, you'd use geocoding API
        stops.append({
            'id': d.id,
            'name': f"{d.customer.first_name} {d.customer.last_name}".strip() or d.customer.username,
            'address': d.delivery_address or 'Address not specified',
            'latitude': getattr(d, 'latitude', 41.0082),  # Default: Istanbul
            'longitude': getattr(d, 'longitude', 28.9784),
            'priority': 1 if d.is_priority else 3
        })
    
    optimizer = RouteOptimizer(depot=depot)
    result = optimizer.optimize_route(stops)
    result = optimizer.estimate_delivery_windows(result['route'])
    
    return result
