# products/views/delivery_views.py
"""
Delivery management and route optimization views.
"""

from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.utils import timezone
from django.db.models import Q
from datetime import datetime, timedelta
import math

from products.models import Delivery, DeliveryRoute, DeliveryRouteStop, CustomUser


class DeliveryViewSet(viewsets.ModelViewSet):
    """Teslimat CRUD işlemleri."""
    permission_classes = [IsAdminUser]
    
    def get_queryset(self):
        queryset = Delivery.objects.select_related('customer', 'product_ownership__product')
        
        # Tarih filtresi
        date = self.request.query_params.get('date')
        if date:
            queryset = queryset.filter(delivery_date=date)
        
        # Durum filtresi
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset.order_by('delivery_date', 'created_at')
    
    def list(self, request):
        queryset = self.get_queryset()
        data = []
        for delivery in queryset:
            data.append({
                'id': delivery.id,
                'customer': {
                    'id': delivery.customer.id,
                    'username': delivery.customer.username,
                    'full_name': f"{delivery.customer.first_name} {delivery.customer.last_name}".strip() or delivery.customer.username,
                    'phone': delivery.customer.phone_number,
                },
                'product': delivery.product_ownership.product.name if delivery.product_ownership else None,
                'delivery_date': delivery.delivery_date.isoformat(),
                'status': delivery.status,
                'status_display': delivery.get_status_display(),
                'address': delivery.address,
                'address_lat': float(delivery.address_lat) if delivery.address_lat else None,
                'address_lng': float(delivery.address_lng) if delivery.address_lng else None,
                'notes': delivery.notes,
                'created_at': delivery.created_at.isoformat(),
            })
        return Response(data)
    
    def create(self, request):
        """Yeni teslimat oluştur."""
        customer_id = request.data.get('customer_id')
        delivery_date = request.data.get('delivery_date')
        address = request.data.get('address')
        notes = request.data.get('notes', '')
        product_ownership_id = request.data.get('product_ownership_id')
        
        if not all([customer_id, delivery_date, address]):
            return Response(
                {'error': 'customer_id, delivery_date ve address zorunludur'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            customer = CustomUser.objects.get(id=customer_id)
        except CustomUser.DoesNotExist:
            return Response({'error': 'Müşteri bulunamadı'}, status=status.HTTP_404_NOT_FOUND)
        
        # Müşterinin koordinatlarını kullan (varsa)
        lat = request.data.get('address_lat') or customer.address_lat
        lng = request.data.get('address_lng') or customer.address_lng
        
        delivery = Delivery.objects.create(
            customer=customer,
            delivery_date=delivery_date,
            address=address,
            address_lat=lat,
            address_lng=lng,
            notes=notes,
            product_ownership_id=product_ownership_id if product_ownership_id else None,
        )
        
        return Response({
            'success': True,
            'id': delivery.id,
            'message': 'Teslimat oluşturuldu'
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Teslimat durumunu güncelle."""
        delivery = self.get_object()
        new_status = request.data.get('status')
        
        if new_status not in dict(Delivery.STATUS_CHOICES):
            return Response({'error': 'Geçersiz durum'}, status=status.HTTP_400_BAD_REQUEST)
        
        delivery.status = new_status
        delivery.save()
        
        return Response({'success': True, 'status': new_status})
    
    @action(detail=False, methods=['get'])
    def pending(self, request):
        """Bekleyen teslimatları getir."""
        deliveries = Delivery.objects.filter(status='pending').select_related('customer')
        data = [{
            'id': d.id,
            'customer': d.customer.username,
            'address': d.address,
            'delivery_date': d.delivery_date.isoformat(),
        } for d in deliveries]
        return Response(data)
    
    @action(detail=False, methods=['get'], url_path='by-date/(?P<date>[0-9-]+)')
    def by_date(self, request, date=None):
        """Belirli tarihteki teslimatları getir."""
        deliveries = Delivery.objects.filter(delivery_date=date).select_related('customer')
        data = [{
            'id': d.id,
            'customer': {
                'id': d.customer.id,
                'name': f"{d.customer.first_name} {d.customer.last_name}".strip() or d.customer.username,
            },
            'address': d.address,
            'address_lat': float(d.address_lat) if d.address_lat else None,
            'address_lng': float(d.address_lng) if d.address_lng else None,
            'status': d.status,
        } for d in deliveries]
        return Response(data)


class DeliveryRouteViewSet(viewsets.ModelViewSet):
    """Teslimat rotası yönetimi ve optimizasyonu."""
    permission_classes = [IsAdminUser]
    queryset = DeliveryRoute.objects.all()
    
    def list(self, request):
        routes = DeliveryRoute.objects.all()[:30]
        data = []
        for route in routes:
            data.append({
                'id': route.id,
                'date': route.date.isoformat(),
                'stop_count': route.stops.count(),
                'total_distance_km': float(route.total_distance_km) if route.total_distance_km else None,
                'total_duration_min': route.total_duration_min,
                'is_optimized': route.is_optimized,
            })
        return Response(data)
    
    def retrieve(self, request, pk=None):
        """Rota detaylarını getir."""
        try:
            route = DeliveryRoute.objects.get(pk=pk)
        except DeliveryRoute.DoesNotExist:
            return Response({'error': 'Rota bulunamadı'}, status=status.HTTP_404_NOT_FOUND)
        
        stops = []
        for stop in route.stops.select_related('delivery__customer').order_by('stop_order'):
            stops.append({
                'order': stop.stop_order,
                'delivery_id': stop.delivery.id,
                'customer': stop.delivery.customer.username,
                'address': stop.delivery.address,
                'lat': float(stop.delivery.address_lat) if stop.delivery.address_lat else None,
                'lng': float(stop.delivery.address_lng) if stop.delivery.address_lng else None,
                'estimated_arrival': stop.estimated_arrival.isoformat() if stop.estimated_arrival else None,
                'distance_km': float(stop.distance_from_previous_km) if stop.distance_from_previous_km else None,
                'duration_min': stop.duration_from_previous_min,
            })
        
        return Response({
            'id': route.id,
            'date': route.date.isoformat(),
            'store': {
                'address': route.store_address,
                'lat': float(route.store_lat),
                'lng': float(route.store_lng),
            },
            'stops': stops,
            'total_distance_km': float(route.total_distance_km) if route.total_distance_km else None,
            'total_duration_min': route.total_duration_min,
            'is_optimized': route.is_optimized,
        })
    
    @action(detail=False, methods=['post'])
    def optimize(self, request):
        """
        Belirli bir tarih için rota optimizasyonu yap.
        Body: { date: "2026-01-07", delivery_ids: [1, 2, 3] }
        """
        date_str = request.data.get('date')
        delivery_ids = request.data.get('delivery_ids', [])
        
        if not date_str:
            return Response({'error': 'date zorunludur'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            route_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response({'error': 'Geçersiz tarih formatı (YYYY-MM-DD)'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Teslimatları al
        if delivery_ids:
            deliveries = list(Delivery.objects.filter(id__in=delivery_ids))
        else:
            deliveries = list(Delivery.objects.filter(
                delivery_date=route_date,
                status__in=['pending', 'assigned']
            ))
        
        if not deliveries:
            return Response({'error': 'Optimize edilecek teslimat yok'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Koordinatı olmayan teslimatları kontrol et
        missing_coords = [d for d in deliveries if not d.address_lat or not d.address_lng]
        if missing_coords:
            return Response({
                'error': 'Bazı teslimatların koordinatları eksik',
                'missing': [{'id': d.id, 'address': d.address} for d in missing_coords]
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Rota oluştur veya güncelle
        route, created = DeliveryRoute.objects.get_or_create(date=route_date)
        route.stops.all().delete()  # Mevcut durakları temizle
        
        # Basit optimizasyon: En yakın komşu algoritması
        optimized_order = self._nearest_neighbor_optimization(
            store_lat=float(route.store_lat),
            store_lng=float(route.store_lng),
            deliveries=deliveries
        )
        
        # Durakları kaydet
        total_distance = 0
        total_duration = 0
        prev_lat, prev_lng = float(route.store_lat), float(route.store_lng)
        
        for i, delivery in enumerate(optimized_order):
            curr_lat = float(delivery.address_lat)
            curr_lng = float(delivery.address_lng)
            
            distance = self._haversine_distance(prev_lat, prev_lng, curr_lat, curr_lng)
            duration = int(distance / 40 * 60)  # 40 km/h ortalama hız
            
            DeliveryRouteStop.objects.create(
                route=route,
                delivery=delivery,
                stop_order=i + 1,
                distance_from_previous_km=round(distance, 2),
                duration_from_previous_min=duration,
            )
            
            total_distance += distance
            total_duration += duration
            prev_lat, prev_lng = curr_lat, curr_lng
            
            # Teslimat durumunu güncelle
            delivery.status = 'assigned'
            delivery.save()
        
        route.total_distance_km = round(total_distance, 2)
        route.total_duration_min = total_duration
        route.is_optimized = True
        route.optimized_at = timezone.now()
        route.save()
        
        return Response({
            'success': True,
            'route_id': route.id,
            'stop_count': len(optimized_order),
            'total_distance_km': round(total_distance, 2),
            'total_duration_min': total_duration,
            'stops': [
                {
                    'order': i + 1,
                    'delivery_id': d.id,
                    'customer': d.customer.username,
                    'address': d.address,
                }
                for i, d in enumerate(optimized_order)
            ]
        })
    
    def _nearest_neighbor_optimization(self, store_lat, store_lng, deliveries):
        """
        En Yakın Komşu algoritması ile basit rota optimizasyonu.
        Her adımda en yakın noktaya git.
        """
        if not deliveries:
            return []
        
        remaining = list(deliveries)
        result = []
        current_lat, current_lng = store_lat, store_lng
        
        while remaining:
            # En yakın teslimatı bul
            nearest = min(
                remaining,
                key=lambda d: self._haversine_distance(
                    current_lat, current_lng,
                    float(d.address_lat), float(d.address_lng)
                )
            )
            result.append(nearest)
            remaining.remove(nearest)
            current_lat = float(nearest.address_lat)
            current_lng = float(nearest.address_lng)
        
        return result
    
    def _haversine_distance(self, lat1, lng1, lat2, lng2):
        """İki koordinat arası mesafeyi km olarak hesapla."""
        R = 6371  # Dünya yarıçapı (km)
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lng = math.radians(lng2 - lng1)
        
        a = math.sin(delta_lat / 2) ** 2 + \
            math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lng / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
    
    @action(detail=False, methods=['get'], url_path='by-date/(?P<date>[0-9-]+)')
    def get_by_date(self, request, date=None):
        """Belirli tarihteki rotayı getir."""
        try:
            route = DeliveryRoute.objects.get(date=date)
            return self.retrieve(request, pk=route.id)
        except DeliveryRoute.DoesNotExist:
            return Response({'error': 'Bu tarih için rota bulunamadı'}, status=status.HTTP_404_NOT_FOUND)
