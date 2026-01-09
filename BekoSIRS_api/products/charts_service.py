# products/charts_service.py
"""
Dashboard Charts Data Service.

Provides aggregated data for frontend charts:
1. Sales trends (line chart)
2. Revenue by category (bar chart)
3. Customer segments (pie chart)
4. Service requests by status (doughnut chart)
5. Product performance (area chart)

Usage:
    from products.charts_service import ChartsService
    
    service = ChartsService()
    sales_data = service.get_sales_chart_data(months=12)
    revenue_data = service.get_revenue_by_category()
"""

from django.utils import timezone
from django.db.models import Count, Sum, Avg, F
from django.db.models.functions import TruncMonth, TruncDate, TruncWeek
from datetime import timedelta, date
from dateutil.relativedelta import relativedelta
from decimal import Decimal
from typing import List, Dict
import logging

from .models import (
    Product, ProductOwnership, Category, CustomUser,
    ServiceRequest, Review, Notification
)

logger = logging.getLogger(__name__)


class ChartsService:
    """
    Service for generating chart-ready data for dashboard.
    
    All methods return data formatted for common chart libraries
    (Chart.js, Recharts, ApexCharts).
    """
    
    def __init__(self):
        self.today = timezone.now().date()
    
    # ==========================================
    # Sales Charts
    # ==========================================
    
    def get_sales_trend(self, months: int = 12) -> Dict:
        """
        Get monthly sales trend data.
        
        Returns:
            {
                'labels': ['Oca 2025', 'Şub 2025', ...],
                'datasets': [{
                    'label': 'Satış Adedi',
                    'data': [45, 52, 38, ...]
                }]
            }
        """
        start_date = self.today - relativedelta(months=months)
        
        monthly_sales = ProductOwnership.objects.filter(
            purchase_date__gte=start_date
        ).annotate(
            month=TruncMonth('purchase_date')
        ).values('month').annotate(
            count=Count('id'),
            revenue=Sum('product__price')
        ).order_by('month')
        
        labels = []
        sales_data = []
        revenue_data = []
        
        month_names = {
            1: 'Oca', 2: 'Şub', 3: 'Mar', 4: 'Nis',
            5: 'May', 6: 'Haz', 7: 'Tem', 8: 'Ağu',
            9: 'Eyl', 10: 'Eki', 11: 'Kas', 12: 'Ara'
        }
        
        for item in monthly_sales:
            month = item['month']
            if month:
                labels.append(f"{month_names[month.month]} {month.year}")
                sales_data.append(item['count'])
                revenue_data.append(float(item['revenue'] or 0))
        
        return {
            'labels': labels,
            'datasets': [
                {
                    'label': 'Satış Adedi',
                    'data': sales_data,
                    'borderColor': '#3b82f6',
                    'backgroundColor': 'rgba(59, 130, 246, 0.1)',
                    'fill': True
                },
                {
                    'label': 'Gelir (TL)',
                    'data': revenue_data,
                    'borderColor': '#10b981',
                    'backgroundColor': 'rgba(16, 185, 129, 0.1)',
                    'yAxisID': 'y1',
                    'fill': True
                }
            ]
        }
    
    def get_daily_sales(self, days: int = 30) -> Dict:
        """Get daily sales for the last N days."""
        start_date = self.today - timedelta(days=days)
        
        daily_sales = ProductOwnership.objects.filter(
            purchase_date__gte=start_date
        ).annotate(
            day=TruncDate('purchase_date')
        ).values('day').annotate(
            count=Count('id')
        ).order_by('day')
        
        # Fill missing days with 0
        sales_dict = {s['day']: s['count'] for s in daily_sales}
        
        labels = []
        data = []
        
        current = start_date
        while current <= self.today:
            labels.append(current.strftime('%d/%m'))
            data.append(sales_dict.get(current, 0))
            current += timedelta(days=1)
        
        return {
            'labels': labels,
            'datasets': [{
                'label': 'Günlük Satış',
                'data': data,
                'borderColor': '#8b5cf6',
                'tension': 0.4
            }]
        }
    
    # ==========================================
    # Revenue Charts
    # ==========================================
    
    def get_revenue_by_category(self) -> Dict:
        """
        Get revenue breakdown by category.
        
        Returns bar chart data.
        """
        revenue = ProductOwnership.objects.values(
            category_name=F('product__category__name')
        ).annotate(
            total=Sum('product__price'),
            count=Count('id')
        ).order_by('-total')
        
        labels = []
        data = []
        colors = [
            '#3b82f6', '#10b981', '#f59e0b', '#ef4444', 
            '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16'
        ]
        
        for idx, item in enumerate(revenue[:8]):  # Top 8 categories
            labels.append(item['category_name'] or 'Diğer')
            data.append(float(item['total'] or 0))
        
        return {
            'labels': labels,
            'datasets': [{
                'label': 'Gelir (TL)',
                'data': data,
                'backgroundColor': colors[:len(data)]
            }]
        }
    
    def get_top_products(self, limit: int = 10) -> Dict:
        """Get top selling products."""
        top = ProductOwnership.objects.values(
            'product__name', 'product__brand'
        ).annotate(
            count=Count('id'),
            revenue=Sum('product__price')
        ).order_by('-count')[:limit]
        
        return {
            'labels': [f"{p['product__name'][:20]}" for p in top],
            'datasets': [{
                'label': 'Satış Adedi',
                'data': [p['count'] for p in top],
                'backgroundColor': '#3b82f6'
            }]
        }
    
    # ==========================================
    # Customer Charts
    # ==========================================
    
    def get_customer_segments(self) -> Dict:
        """
        Get customer segmentation for pie chart.
        
        Uses CLV-based segmentation from CustomerAnalyticsService.
        """
        from .customer_analytics_service import CustomerAnalyticsService
        
        service = CustomerAnalyticsService()
        summary = service.analyze_all_customers()
        
        segments = summary.get('segments', {})
        
        return {
            'labels': ['VIP', 'Premium', 'Standart', 'Düşük', 'Yeni'],
            'datasets': [{
                'data': [
                    segments.get('vip', 0),
                    segments.get('premium', 0),
                    segments.get('standard', 0),
                    segments.get('low', 0),
                    segments.get('new', 0)
                ],
                'backgroundColor': [
                    '#f59e0b',  # VIP - gold
                    '#8b5cf6',  # Premium - purple
                    '#3b82f6',  # Standard - blue
                    '#6b7280',  # Low - gray
                    '#10b981'   # New - green
                ]
            }]
        }
    
    def get_customer_registrations(self, months: int = 6) -> Dict:
        """Get new customer registrations over time."""
        start_date = self.today - relativedelta(months=months)
        
        registrations = CustomUser.objects.filter(
            role='customer',
            date_joined__gte=start_date
        ).annotate(
            month=TruncMonth('date_joined')
        ).values('month').annotate(
            count=Count('id')
        ).order_by('month')
        
        labels = []
        data = []
        
        month_names = {
            1: 'Oca', 2: 'Şub', 3: 'Mar', 4: 'Nis',
            5: 'May', 6: 'Haz', 7: 'Tem', 8: 'Ağu',
            9: 'Eyl', 10: 'Eki', 11: 'Kas', 12: 'Ara'
        }
        
        for item in registrations:
            month = item['month']
            if month:
                labels.append(f"{month_names[month.month]} {month.year}")
                data.append(item['count'])
        
        return {
            'labels': labels,
            'datasets': [{
                'label': 'Yeni Müşteri',
                'data': data,
                'backgroundColor': '#10b981'
            }]
        }
    
    # ==========================================
    # Service Request Charts
    # ==========================================
    
    def get_service_requests_by_status(self) -> Dict:
        """Get service requests breakdown by status."""
        status_counts = ServiceRequest.objects.values('status').annotate(
            count=Count('id')
        )
        
        status_labels = {
            'pending': 'Beklemede',
            'in_queue': 'Sırada',
            'in_progress': 'İşlemde',
            'completed': 'Tamamlandı',
            'cancelled': 'İptal'
        }
        
        status_colors = {
            'pending': '#f59e0b',
            'in_queue': '#3b82f6',
            'in_progress': '#8b5cf6',
            'completed': '#10b981',
            'cancelled': '#ef4444'
        }
        
        labels = []
        data = []
        colors = []
        
        for item in status_counts:
            status = item['status']
            labels.append(status_labels.get(status, status))
            data.append(item['count'])
            colors.append(status_colors.get(status, '#6b7280'))
        
        return {
            'labels': labels,
            'datasets': [{
                'data': data,
                'backgroundColor': colors
            }]
        }
    
    def get_service_requests_trend(self, weeks: int = 12) -> Dict:
        """Get service requests trend over weeks."""
        start_date = self.today - timedelta(weeks=weeks)
        
        weekly = ServiceRequest.objects.filter(
            created_at__gte=start_date
        ).annotate(
            week=TruncWeek('created_at')
        ).values('week').annotate(
            count=Count('id')
        ).order_by('week')
        
        return {
            'labels': [w['week'].strftime('%d/%m') if w['week'] else '' for w in weekly],
            'datasets': [{
                'label': 'Servis Talepleri',
                'data': [w['count'] for w in weekly],
                'borderColor': '#ef4444',
                'fill': False
            }]
        }
    
    # ==========================================
    # Combined Dashboard Data
    # ==========================================
    
    def get_dashboard_charts(self) -> Dict:
        """Get all chart data for dashboard in one call."""
        return {
            'sales_trend': self.get_sales_trend(months=12),
            'revenue_by_category': self.get_revenue_by_category(),
            'top_products': self.get_top_products(10),
            'customer_segments': self.get_customer_segments(),
            'service_by_status': self.get_service_requests_by_status(),
            'summary': self._get_summary_stats()
        }
    
    def _get_summary_stats(self) -> Dict:
        """Get key summary statistics."""
        today_start = timezone.now().replace(hour=0, minute=0, second=0)
        this_month_start = self.today.replace(day=1)
        
        return {
            'today_sales': ProductOwnership.objects.filter(
                purchase_date=self.today
            ).count(),
            'today_revenue': float(
                ProductOwnership.objects.filter(
                    purchase_date=self.today
                ).aggregate(total=Sum('product__price'))['total'] or 0
            ),
            'this_month_sales': ProductOwnership.objects.filter(
                purchase_date__gte=this_month_start
            ).count(),
            'pending_service': ServiceRequest.objects.filter(
                status__in=['pending', 'in_queue']
            ).count(),
            'avg_rating': float(
                Review.objects.filter(is_approved=True).aggregate(
                    avg=Avg('rating')
                )['avg'] or 0
            ),
            'total_customers': CustomUser.objects.filter(role='customer').count(),
        }


# API helper function
def get_dashboard_chart_data():
    """Helper for API views."""
    service = ChartsService()
    return service.get_dashboard_charts()
