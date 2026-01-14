from rest_framework import viewsets, views, response, permissions, status
from rest_framework.decorators import action
import random
from datetime import timedelta
from django.db.models import Sum, Count, F, Q
from django.utils import timezone
from products.models import Product, ProductOwnership, ServiceRequest, CustomUser, Category, AuditLog, ProductAssignment, InstallmentPlan
from products.serializers import AuditLogSerializer

class ChartsView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        today = timezone.now().date()
        
        # 1. Summary Cards
        # Calculate from ProductAssignment (Cash/Regular Sales)
        assignments_today = ProductAssignment.objects.filter(assigned_at__date=today)
        assignments_count = assignments_today.count()
        assignments_revenue = assignments_today.aggregate(
            total=Sum(F('product__price') * F('quantity'))
        )['total'] or 0

        # Calculate from InstallmentPlan (Installment Sales)
        installments_today = InstallmentPlan.objects.filter(created_at__date=today)
        installments_count = installments_today.count()
        installments_revenue = installments_today.aggregate(total=Sum('total_amount'))['total'] or 0

        today_sales_count = assignments_count + installments_count
        today_revenue = assignments_revenue + installments_revenue
        
        pending_service_count = ServiceRequest.objects.filter(status='pending').count()
        total_customers_count = CustomUser.objects.filter(role='customer').count()

        # 2. Revenue by Category
        # Aggregate revenue by category name from ProductAssignment (using assignments as main sales data for categories for now)
        category_revenue = (
            ProductAssignment.objects.values('product__category__name')
            .annotate(total_revenue=Sum(F('product__price') * F('quantity')))
            .order_by('-total_revenue')[:5]
        )
        
        cat_labels = [item['product__category__name'] or 'Diğer' for item in category_revenue]
        cat_data = [item['total_revenue'] or 0 for item in category_revenue]

        # 3. Top Products (Best Sellers)
        # Using ProductAssignment for best sellers
        top_products_qs = (
            ProductAssignment.objects.values('product__name')
            .annotate(sales_count=Sum('quantity'))
            .order_by('-sales_count')[:5]
        )
        
        prod_labels = [item['product__name'] for item in top_products_qs]
        prod_data = [item['sales_count'] for item in top_products_qs]

        # 4. Customer Segments (Simplified logic for now)
        # Active: Logged in last 30 days, Inactive: Not logged in > 30 days
        month_ago = timezone.now() - timedelta(days=30)
        active_customers = CustomUser.objects.filter(role='customer', last_login__gte=month_ago).count()
        inactive_customers = CustomUser.objects.filter(role='customer', last_login__lt=month_ago).count()
        new_customers = CustomUser.objects.filter(role='customer', date_joined__gte=month_ago).count()
        
        # Improvement: Base segments on ProductAssignment frequency if possible, 
        # but for now keeping the previous logic or switching to Assigments count.
        # Let's use Assignments for "Loyal" check.
        loyal_count = ProductAssignment.objects.values('customer').annotate(count=Count('id')).filter(count__gt=5).count()
        potential_count = ProductAssignment.objects.values('customer').annotate(count=Count('id')).filter(count__range=(1, 5)).count()
        
        segment_labels = ["Sadık Müşteri (>5 Sipariş)", "Potansiyel (1-5 Sipariş)", "Yeni Üye (<30 Gün)", "Pasif"]
        segment_data = [loyal_count, potential_count, new_customers, inactive_customers]

        # 5. Service by Status
        service_stats = (
            ServiceRequest.objects.values('status')
            .annotate(count=Count('id'))
            .order_by('status')
        )
        status_map = dict(ServiceRequest.STATUS_CHOICES)
        svc_labels = [status_map.get(item['status'], item['status']) for item in service_stats]
        svc_data = [item['count'] for item in service_stats]

        data = {
            "summary": {
                "today_sales": today_sales_count,
                "today_revenue": today_revenue,
                "pending_service": pending_service_count,
                "total_customers": total_customers_count,
            },
            "revenue_by_category": {
                "labels": cat_labels if cat_labels else ["Veri Yok"],
                "datasets": [{"data": cat_data if cat_data else [0]}]
            },
            "top_products": {
                "labels": prod_labels if prod_labels else ["Satış Yok"],
                "datasets": [{"data": prod_data if prod_data else [0]}]
            },
            "customer_segments": {
                "labels": segment_labels,
                "datasets": [{"data": segment_data}]
            },
            "service_by_status": {
                "labels": svc_labels if svc_labels else ["Talep Yok"],
                "datasets": [{"data": svc_data if svc_data else [0]}]
            }
        }
        return response.Response(data)


class SalesForecastView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return self.get_summary(request)

    def get_summary(self, request):
        products = ["Buzdolabı", "Çamaşır Mak.", "Bulaşık Mak.", "Fırın", "TV"]
        data = {
            "top_forecasts": []
        }
        
        for p in products:
            trend = random.choice(['increasing', 'decreasing', 'stable'])
            data["top_forecasts"].append({
                "product_name": p,
                "brand": "Beko",
                "current_stock": random.randint(0, 20),
                "trend": trend,
                "forecasts": [
                    {"predicted_sales": random.randint(10, 30)},
                    {"predicted_sales": random.randint(10, 30)},
                    {"predicted_sales": random.randint(10, 30)},
                ],
                "recommendation": "Stok artırılmalı" if trend == 'increasing' else "Kampanya yapılmalı"
            })
            
        return response.Response(data)


class MarketingAutomationView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
       return self.get_stats(request)

    @action(detail=False, methods=['get'])
    def get_stats(self, request):
        data = {
            "campaigns": {
                "birthday": {"eligible": random.randint(5, 20)},
                "churn_prevention": {"eligible": random.randint(10, 50)},
                "review_request": {"eligible": random.randint(5, 15)},
                "welcome": {"eligible": random.randint(2, 10)},
            }
        }
        return response.Response(data)

    @action(detail=False, methods=['post'])
    def run(self, request):
        campaign = request.data.get('campaign')
        dry_run = request.data.get('dry_run', True)
        
        return response.Response({
            "status": "success",
            "message": f"Kampanya '{campaign}' başarıyla {'simüle edildi' if dry_run else 'başlatıldı'}.",
            "target_count": random.randint(5, 50),
            "estimated_impact": "Yüksek"
        })

class AuditLogView(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer

    @action(detail=False, methods=['get'])
    def get_logs(self, request):
        limit = int(request.query_params.get('limit', 50))
        queryset = self.get_queryset()[:limit]
        serializer = self.get_serializer(queryset, many=True)
        return response.Response({"logs": serializer.data})
