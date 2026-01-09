# products/views/installment_views.py
"""
Installment System views - Taksit Planları ve Taksit yönetimi.
"""

from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Q

from products.models import InstallmentPlan, Installment, Notification
from products.serializers import (
    InstallmentSerializer,
    InstallmentPlanSerializer,
    InstallmentPlanListSerializer,
    InstallmentPlanCreateSerializer,
    InstallmentPlanDetailSerializer,
    CustomerConfirmPaymentSerializer,
    AdminApprovePaymentSerializer,
)
from products.permissions import IsSeller, IsOwnerOrAdmin


class InstallmentPlanViewSet(viewsets.ModelViewSet):
    """ViewSet for InstallmentPlan CRUD and custom actions."""
    queryset = InstallmentPlan.objects.all().select_related('customer', 'product', 'created_by')
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return InstallmentPlanCreateSerializer
        elif self.action == 'list':
            return InstallmentPlanListSerializer
        elif self.action == 'retrieve':
            return InstallmentPlanDetailSerializer
        return InstallmentPlanSerializer

    def get_queryset(self):
        user = self.request.user
        qs = InstallmentPlan.objects.all().select_related('customer', 'product', 'created_by')

        # Customers can only see their own plans
        if user.role == 'customer':
            qs = qs.filter(customer=user)
        
        # Apply filters
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)

        customer_filter = self.request.query_params.get('customer')
        if customer_filter and user.role in ['admin', 'seller']:
            qs = qs.filter(customer_id=customer_filter)

        return qs.order_by('-created_at')

    def get_permissions(self):
        """Set permissions based on action."""
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'cancel']:
            return [IsAuthenticated(), IsSeller()]
        return [IsAuthenticated()]

    @action(detail=False, methods=['get'], url_path='customer-plans')
    def customer_plans(self, request):
        """GET /api/installment-plans/customer-plans/ - Login olan müşterinin planları."""
        user = request.user
        if user.role != 'customer':
            return Response(
                {'error': 'Bu endpoint sadece müşteriler için geçerlidir.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        plans = InstallmentPlan.objects.filter(customer=user).select_related('product')
        serializer = InstallmentPlanListSerializer(plans, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='installments')
    def installments(self, request, pk=None):
        """GET /api/installment-plans/{id}/installments/ - Plana ait taksitler."""
        plan = self.get_object()
        
        # Check permission
        user = request.user
        if user.role == 'customer' and plan.customer != user:
            return Response(
                {'error': 'Bu plana erişim yetkiniz yok.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        installments = plan.installments.all().order_by('installment_number')
        serializer = InstallmentSerializer(installments, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='overdue')
    def overdue(self, request):
        """GET /api/installment-plans/overdue/ - Gecikmiş taksitleri olan planlar."""
        user = request.user
        if user.role not in ['admin', 'seller']:
            return Response(
                {'error': 'Bu endpoint sadece yöneticiler için geçerlidir.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Find plans with overdue installments
        overdue_plans = InstallmentPlan.objects.filter(
            status='active',
            installments__status='overdue'
        ).distinct().select_related('customer', 'product')
        
        serializer = InstallmentPlanListSerializer(overdue_plans, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel(self, request, pk=None):
        """POST /api/installment-plans/{id}/cancel/ - Planı iptal et."""
        plan = self.get_object()
        
        if plan.status != 'active':
            return Response(
                {'error': 'Sadece aktif planlar iptal edilebilir.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if any installments are paid
        if plan.installments.filter(status='paid').exists():
            return Response(
                {'error': 'Ödenmiş taksiti olan planlar iptal edilemez.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        plan.status = 'cancelled'
        plan.save()
        
        # Send notification to customer
        Notification.objects.create(
            user=plan.customer,
            notification_type='general',
            title='Taksit Planı İptal Edildi',
            message=f'{plan.product.name} ürününe ait taksit planınız iptal edildi.',
            related_product=plan.product
        )
        
        return Response({'status': 'Plan iptal edildi.'})


class InstallmentViewSet(viewsets.ModelViewSet):
    """ViewSet for Installment CRUD and payment actions."""
    queryset = Installment.objects.all().select_related('plan', 'plan__customer', 'plan__product')
    serializer_class = InstallmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = Installment.objects.all().select_related('plan', 'plan__customer', 'plan__product')

        # Customers can only see their own installments
        if user.role == 'customer':
            qs = qs.filter(plan__customer=user)
        
        # Apply filters
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)

        plan_filter = self.request.query_params.get('plan')
        if plan_filter:
            qs = qs.filter(plan_id=plan_filter)

        return qs.order_by('due_date')

    def get_permissions(self):
        """Set permissions based on action."""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsSeller()]
        return [IsAuthenticated()]

    @action(detail=True, methods=['post'], url_path='customer-confirm')
    def customer_confirm(self, request, pk=None):
        """POST /api/installments/{id}/customer-confirm/ - Müşteri ödeme onayı."""
        installment = self.get_object()
        user = request.user

        # Only the owner customer can confirm
        if user.role != 'customer' or installment.plan.customer != user:
            return Response(
                {'error': 'Bu taksiti onaylama yetkiniz yok.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Check installment status
        if installment.status not in ['pending', 'overdue']:
            return Response(
                {'error': 'Bu taksit zaten onaylanmış veya ödenmiş.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update status
        installment.status = 'customer_confirmed'
        installment.customer_confirmed_at = timezone.now()
        installment.save()

        # Create notification for admin/seller
        Notification.objects.create(
            user=installment.plan.created_by or installment.plan.customer,
            notification_type='general',
            title='Taksit Ödemesi Onay Bekliyor',
            message=f'{installment.plan.customer.username} müşterisi {installment.plan.product.name} ürününün {installment.installment_number}. taksitini ödediğini bildirdi.',
            related_product=installment.plan.product
        )

        serializer = InstallmentSerializer(installment)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='admin-approve')
    def admin_approve(self, request, pk=None):
        """POST /api/installments/{id}/admin-approve/ - Admin/Seller ödeme onayı."""
        installment = self.get_object()
        user = request.user

        # Only admin or seller can approve
        if user.role not in ['admin', 'seller']:
            return Response(
                {'error': 'Bu işlemi gerçekleştirme yetkiniz yok.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Check installment status
        if installment.status not in ['pending', 'customer_confirmed', 'overdue']:
            return Response(
                {'error': 'Bu taksit zaten ödenmiş.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Parse request data
        serializer = AdminApprovePaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Update installment
        installment.status = 'paid'
        installment.admin_confirmed_at = timezone.now()
        installment.payment_date = serializer.validated_data.get('payment_date') or timezone.now().date()
        installment.save()

        # Check if all installments are paid, update plan status
        plan = installment.plan
        if not plan.installments.exclude(status='paid').exists():
            plan.status = 'completed'
            plan.save()
            
            # Send completion notification
            Notification.objects.create(
                user=plan.customer,
                notification_type='general',
                title='Taksit Planı Tamamlandı! 🎉',
                message=f'{plan.product.name} ürününe ait tüm taksitleriniz ödenmiştir. Tebrikler!',
                related_product=plan.product
            )
        else:
            # Send payment confirmed notification
            Notification.objects.create(
                user=plan.customer,
                notification_type='general',
                title='Taksit Ödemesi Onaylandı ✓',
                message=f'{plan.product.name} ürününün {installment.installment_number}. taksit ödemesi onaylandı.',
                related_product=plan.product
            )

        return Response(InstallmentSerializer(installment).data)

    @action(detail=False, methods=['get'], url_path='overdue-list')
    def overdue_list(self, request):
        """GET /api/installments/overdue-list/ - Tüm gecikmiş taksitler."""
        user = request.user
        if user.role not in ['admin', 'seller']:
            return Response(
                {'error': 'Bu endpoint sadece yöneticiler için geçerlidir.'},
                status=status.HTTP_403_FORBIDDEN
            )

        overdue = Installment.objects.filter(
            status='overdue'
        ).select_related('plan', 'plan__customer', 'plan__product').order_by('due_date')

        serializer = InstallmentSerializer(overdue, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='pending-confirmations')
    def pending_confirmations(self, request):
        """GET /api/installments/pending-confirmations/ - Müşteri onayı bekleyen taksitler."""
        user = request.user
        if user.role not in ['admin', 'seller']:
            return Response(
                {'error': 'Bu endpoint sadece yöneticiler için geçerlidir.'},
                status=status.HTTP_403_FORBIDDEN
            )

        pending = Installment.objects.filter(
            status='customer_confirmed'
        ).select_related('plan', 'plan__customer', 'plan__product').order_by('customer_confirmed_at')

        serializer = InstallmentSerializer(pending, many=True)
        return Response(serializer.data)
