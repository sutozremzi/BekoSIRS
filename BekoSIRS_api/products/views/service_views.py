# products/views/service_views.py
"""
Service request and product ownership views.
"""

from rest_framework import viewsets, status, exceptions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.utils import timezone
from django.db.models import Count, Sum, Avg, Prefetch

from products.models import (
    CustomUser, Product, Category, ProductOwnership,
    ServiceRequest, ServiceQueue, Notification, Review
)
from products.serializers import (
    ProductOwnershipSerializer, ProductOwnershipCreateSerializer,
    ServiceRequestSerializer, ServiceRequestCreateSerializer,
    ServiceQueueSerializer
)


class ProductOwnershipViewSet(viewsets.ModelViewSet):
    """Product ownership/assignment management."""
    queryset = ProductOwnership.objects.all().select_related("customer", "product", "product__category")
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ["list", "retrieve", "my_ownerships"]:
            return [IsAuthenticated()]
        return [IsAdminUser()]

    def get_serializer_class(self):
        if self.action == "create":
            return ProductOwnershipCreateSerializer
        return ProductOwnershipSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role in ["admin", "seller"]:
            return ProductOwnership.objects.all().select_related("customer", "product", "product__category")
        return ProductOwnership.objects.filter(customer=user).select_related("product", "product__category")

    @action(detail=False, methods=["get"], url_path="my-ownerships")
    def my_ownerships(self, request):
        """GET /api/product-ownerships/my-ownerships/ - Customer's owned products with warranty info."""
        # FIX: Use prefetch_related to avoid N+1 query problem
        ownerships = ProductOwnership.objects.filter(
            customer=request.user
        ).select_related("product", "product__category").prefetch_related(
            Prefetch(
                'service_requests',
                queryset=ServiceRequest.objects.exclude(status__in=["completed", "cancelled"]),
                to_attr='active_service_requests_list'
            )
        )

        data = []
        for ownership in ownerships:
            product = ownership.product
            warranty_end = ownership.warranty_end_date
            is_warranty_active = warranty_end and warranty_end >= timezone.now().date()
            # Use prefetched data instead of querying again
            active_service_requests = len(ownership.active_service_requests_list)

            data.append({
                "id": ownership.id,
                "product": {
                    "id": product.id,
                    "name": product.name,
                    "brand": product.brand,
                    "price": str(product.price),
                    "image": product.image.url if product.image else None,
                    "category_name": product.category.name if product.category else None,
                    "warranty_duration_months": product.warranty_duration_months,
                },
                "purchase_date": ownership.purchase_date,
                "serial_number": ownership.serial_number,
                "warranty_end_date": warranty_end,
                "is_warranty_active": is_warranty_active,
                "days_until_warranty_expires": (warranty_end - timezone.now().date()).days if warranty_end and is_warranty_active else None,
                "active_service_requests": active_service_requests,
            })

        return Response(data)


class ServiceRequestViewSet(viewsets.ModelViewSet):
    """Service request management."""
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return ServiceRequestCreateSerializer
        return ServiceRequestSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role in ['admin', 'seller']:
            return ServiceRequest.objects.all().select_related(
                'customer', 'product_ownership__product', 'assigned_to'
            ).prefetch_related('queue_entry')
        return ServiceRequest.objects.filter(customer=user).select_related(
            'product_ownership__product'
        ).prefetch_related('queue_entry')

    def perform_create(self, serializer):
        ownership = serializer.validated_data['product_ownership']
        if ownership.customer != self.request.user:
            raise exceptions.PermissionDenied("Bu ürün için servis talebi oluşturamazsınız.")

        service_request = serializer.save(customer=self.request.user)
        
        # Calculate priority based on business rules
        priority = self._calculate_priority(service_request, ownership)
        
        last_queue = ServiceQueue.objects.order_by('-queue_number').first()
        queue_number = (last_queue.queue_number + 1) if last_queue else 1

        ServiceQueue.objects.create(
            service_request=service_request,
            queue_number=queue_number,
            priority=priority,
            estimated_wait_time=queue_number * 30
        )

        service_request.status = 'in_queue'
        service_request.save()

        Notification.objects.create(
            user=self.request.user,
            notification_type='service_update',
            title='Servis Talebiniz Alındı',
            message=f'Talep numaranız: SR-{service_request.id}. Sıra numaranız: {queue_number}. Öncelik: {priority}',
            related_service_request=service_request
        )

    def _calculate_priority(self, service_request, ownership):
        """
        Calculate priority for service request (1=highest, 10=lowest).
        
        Factors:
        - Warranty status: In warranty = +2 priority boost
        - Wait time: Each day waiting = +1 boost (max 3)
        - Request type: repair/urgent = +2 boost
        - Customer value: VIP potential (future: based on purchase history)
        """
        base_priority = 5  # Default middle priority
        
        # Factor 1: Warranty status
        warranty_end = ownership.warranty_end_date
        if warranty_end and warranty_end >= timezone.now().date():
            base_priority -= 2  # Higher priority for in-warranty products
        
        # Factor 2: Request type priority
        request_type = getattr(service_request, 'request_type', None)
        if request_type in ['repair', 'urgent']:
            base_priority -= 2  # Higher priority for urgent repairs
        elif request_type == 'maintenance':
            base_priority += 1  # Lower priority for maintenance
        
        # Factor 3: Customer history (VIP bonus)
        customer = ownership.customer
        total_products = ProductOwnership.objects.filter(customer=customer).count()
        if total_products >= 5:
            base_priority -= 1  # Loyal customer bonus
        
        # Ensure priority is within valid range (1-10)
        return max(1, min(10, base_priority))

    @action(detail=False, methods=['post'], url_path='recalculate-priorities')
    def recalculate_priorities(self, request):
        """
        POST /api/service-requests/recalculate-priorities/
        Recalculate priorities for all pending queue items based on wait time.
        Admin only.
        """
        if request.user.role != 'admin':
            return Response({'error': 'Yetkiniz yok'}, status=status.HTTP_403_FORBIDDEN)
        
        updated_count = 0
        
        # Get all active queue entries
        queue_entries = ServiceQueue.objects.filter(
            service_request__status__in=['pending', 'in_queue']
        ).select_related('service_request__ownership')
        
        for queue in queue_entries:
            sr = queue.service_request
            old_priority = queue.priority
            
            # Add wait time bonus
            days_waiting = (timezone.now() - sr.created_at).days
            wait_bonus = min(days_waiting, 3)  # Max 3 points for waiting
            
            new_priority = max(1, old_priority - wait_bonus)
            
            if new_priority != queue.priority:
                queue.priority = new_priority
                queue.save()
                updated_count += 1
        
        return Response({
            'success': True,
            'updated_count': updated_count,
            'message': f'{updated_count} talebin önceliği güncellendi.'
        })

    @action(detail=True, methods=['post'], url_path='assign')
    def assign_request(self, request, pk=None):
        """POST /api/service-requests/{id}/assign/ - Assign to staff."""
        if request.user.role not in ['admin', 'seller']:
            return Response({'error': 'Yetkiniz yok'}, status=status.HTTP_403_FORBIDDEN)

        service_request = self.get_object()
        assigned_to_id = request.data.get('assigned_to')

        if assigned_to_id:
            try:
                assigned_user = CustomUser.objects.get(id=assigned_to_id)
                service_request.assigned_to = assigned_user
                service_request.status = 'in_progress'
                service_request.save()

                Notification.objects.create(
                    user=service_request.customer,
                    notification_type='service_update',
                    title='Servis Talebiniz İşleme Alındı',
                    message=f'Talep SR-{service_request.id} artık işleme alındı.',
                    related_service_request=service_request
                )
                return Response({'success': 'Talep atandı'})
            except CustomUser.DoesNotExist:
                return Response({'error': 'Kullanıcı bulunamadı'}, status=status.HTTP_404_NOT_FOUND)
        
        return Response({'error': 'assigned_to gerekli'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], url_path='queue-status')
    def queue_status(self, request):
        """GET /api/service-requests/queue-status/ - Get user's queue position."""
        user_requests = ServiceRequest.objects.filter(
            customer=request.user
        ).exclude(status__in=['completed', 'cancelled']).select_related('queue_entry')

        data = []
        for sr in user_requests:
            queue = getattr(sr, 'queue_entry', None)
            data.append({
                'request_id': sr.id,
                'status': sr.status,
                'queue_number': queue.queue_number if queue else None,
                'estimated_wait_time': queue.estimated_wait_time if queue else None,
            })

        return Response(data)


class DashboardSummaryView(APIView):
    """Dashboard summary statistics for admin panel."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.role not in ['admin', 'seller']:
            return Response({'error': 'Yetkisiz'}, status=status.HTTP_403_FORBIDDEN)

        total_products = Product.objects.count()
        total_categories = Category.objects.count()
        total_customers = CustomUser.objects.filter(role='customer').count()
        total_orders = ProductOwnership.objects.count()

        pending_requests = ServiceRequest.objects.filter(status='pending').count()
        in_progress_requests = ServiceRequest.objects.filter(status='in_progress').count()
        completed_requests = ServiceRequest.objects.filter(status='completed').count()

        pending_reviews = Review.objects.filter(is_approved=False).count()
        avg_rating = Review.objects.filter(is_approved=True).aggregate(avg=Avg('rating'))['avg'] or 0

        low_stock = Product.objects.filter(stock__lt=10).count()
        out_of_stock = Product.objects.filter(stock=0).count()

        return Response({
            'products': {
                'total': total_products,
                'low_stock': low_stock,
                'out_of_stock': out_of_stock,
            },
            'categories': {'total': total_categories},
            'customers': {'total': total_customers},
            'orders': {'total': total_orders},
            'service_requests': {
                'pending': pending_requests,
                'in_progress': in_progress_requests,
                'completed': completed_requests,
            },
            'reviews': {
                'pending_approval': pending_reviews,
                'average_rating': round(avg_rating, 1),
            }
        })


class StockIntelligenceView(APIView):
    """
    Stock Intelligence API for admin panel.
    
    Provides smart stock recommendations based on:
    - Sales velocity (units per day)
    - Days until stockout
    - Seasonal demand adjustments
    - Reorder point calculations
    
    Endpoints:
    - GET /api/stock-intelligence/ - Full dashboard summary
    - GET /api/stock-intelligence/critical/ - Critical alerts only
    - GET /api/stock-intelligence/opportunities/ - Seasonal opportunities
    - GET /api/stock-intelligence/all/ - All recommendations
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.role not in ['admin', 'seller']:
            return Response({'error': 'Yetkisiz'}, status=status.HTTP_403_FORBIDDEN)
        
        from products.stock_intelligence_service import StockIntelligenceService
        
        view_type = request.query_params.get('view', 'dashboard')
        service = StockIntelligenceService()
        
        if view_type == 'critical':
            data = {
                'type': 'critical',
                'alerts': service.get_critical_stock_alerts()
            }
        elif view_type == 'opportunities':
            data = {
                'type': 'opportunities',
                'alerts': service.get_opportunity_alerts()
            }
        elif view_type == 'all':
            data = {
                'type': 'all',
                'recommendations': service.get_all_recommendations()
            }
        else:
            # Default: dashboard summary
            data = service.get_dashboard_summary()
        
        return Response(data)

