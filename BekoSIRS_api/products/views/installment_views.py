from rest_framework import viewsets, permissions, status, decorators, response
from django.utils import timezone
from products.models import InstallmentPlan, Installment
from products.serializers import (
    InstallmentPlanSerializer, InstallmentPlanListSerializer, 
    InstallmentPlanDetailSerializer, InstallmentPlanCreateSerializer,
    InstallmentSerializer, AdminApprovePaymentSerializer
)

class InstallmentPlanViewSet(viewsets.ModelViewSet):
    queryset = InstallmentPlan.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return InstallmentPlanCreateSerializer
        elif self.action == 'list':
            return InstallmentPlanListSerializer
        elif self.action == 'retrieve':
            return InstallmentPlanDetailSerializer
        return InstallmentPlanSerializer

    def perform_create(self, serializer):
        # Create plan
        plan = serializer.save(created_by=self.request.user)
        
        # Auto-generate installments based on count and total amount
        total = plan.total_amount - plan.down_payment
        count = plan.installment_count
        amount_per_inst = total / count
        
        start_date = plan.start_date
        
        for i in range(1, count + 1):
            due_date = start_date + timezone.timedelta(days=30 * i)
            Installment.objects.create(
                plan=plan,
                installment_number=i,
                amount=amount_per_inst,
                due_date=due_date,
                status='pending'
            )

    @decorators.action(detail=True, methods=['get'])
    def installments(self, request, pk=None):
        plan = self.get_object()
        installments = plan.installments.all()
        serializer = InstallmentSerializer(installments, many=True)
        return response.Response(serializer.data)


class InstallmentViewSet(viewsets.ModelViewSet):
    queryset = Installment.objects.all()
    serializer_class = InstallmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    @decorators.action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        installment = self.get_object()
        serializer = AdminApprovePaymentSerializer(data=request.data)
        
        if serializer.is_valid():
            installment.status = 'paid'
            installment.payment_date = serializer.validated_data.get('payment_date', timezone.now().date())
            installment.admin_confirmed_at = timezone.now()
            installment.save()
            
            # Check if all paid, mark plan completed
            plan = installment.plan
            if not plan.installments.exclude(status='paid').exists():
                plan.status = 'completed'
                plan.save()
                
            return response.Response({'status': 'success'})
        return response.Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
