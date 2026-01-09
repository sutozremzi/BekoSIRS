# products/stock_intelligence_service.py
"""
Stock Intelligence Service for Admin Panel.

Analyzes sales data and provides smart stock recommendations:
1. Sales velocity calculation (units per day)
2. Days until stockout prediction
3. Restock point calculation
4. Seasonal trend adjustments
5. Complementary product suggestions

Usage:
    from products.stock_intelligence_service import StockIntelligenceService
    
    service = StockIntelligenceService()
    recommendations = service.get_all_recommendations()
    critical = service.get_critical_stock_alerts()
"""

from django.utils import timezone
from django.db.models import Count, Sum, Avg, F, Q
from datetime import timedelta
from decimal import Decimal
import logging

from .models import Product, ProductOwnership, Category

logger = logging.getLogger(__name__)


class StockIntelligenceService:
    """
    Stock Intelligence Engine for smart inventory management.
    
    Configuration:
    - ANALYSIS_DAYS: Days of sales data to analyze (default: 30)
    - LEAD_TIME_DAYS: Supplier lead time in days (default: 7)
    - SAFETY_STOCK_DAYS: Buffer stock in days (default: 3)
    - CRITICAL_DAYS: Threshold for critical stock (default: 7)
    - WARNING_DAYS: Threshold for warning (default: 14)
    """
    
    ANALYSIS_DAYS = 30
    LEAD_TIME_DAYS = 7
    SAFETY_STOCK_DAYS = 3
    CRITICAL_DAYS = 7
    WARNING_DAYS = 14
    
    # Seasonal boost categories (month -> category names)
    SEASONAL_DEMAND = {
        1: {'Kombi': 1.5, 'Isıtıcı': 1.5},
        2: {'Kombi': 1.3, 'Isıtıcı': 1.3},
        5: {'Klima': 1.5, 'Vantilatör': 1.5},
        6: {'Klima': 2.0, 'Buzdolabı': 1.3, 'Derin Dondurucu': 1.3},
        7: {'Klima': 2.0, 'Buzdolabı': 1.3},
        8: {'Klima': 1.5, 'Vantilatör': 1.3},
        11: {'Fırın': 1.3, 'Ocak': 1.3},
        12: {'TV': 1.5, 'Fırın': 1.5},
    }
    
    def __init__(self):
        self.today = timezone.now().date()
        self.current_month = self.today.month
        self.analysis_start = self.today - timedelta(days=self.ANALYSIS_DAYS)
    
    def get_all_recommendations(self) -> list:
        """
        Get stock recommendations for all products.
        
        Returns:
            List of dicts with product info and recommendations
        """
        products = Product.objects.all().select_related('category')
        recommendations = []
        
        for product in products:
            rec = self._analyze_product(product)
            recommendations.append(rec)
        
        # Sort by urgency (critical first, then by days until stockout)
        recommendations.sort(key=lambda x: (
            0 if x['urgency'] == 'critical' else 
            1 if x['urgency'] == 'warning' else 
            2 if x['urgency'] == 'opportunity' else 3,
            x['days_until_stockout'] or 999
        ))
        
        return recommendations
    
    def get_critical_stock_alerts(self) -> list:
        """Get only critical stock alerts (< CRITICAL_DAYS)."""
        all_recs = self.get_all_recommendations()
        return [r for r in all_recs if r['urgency'] == 'critical']
    
    def get_warning_alerts(self) -> list:
        """Get warning level alerts."""
        all_recs = self.get_all_recommendations()
        return [r for r in all_recs if r['urgency'] == 'warning']
    
    def get_opportunity_alerts(self) -> list:
        """Get seasonal opportunity alerts."""
        all_recs = self.get_all_recommendations()
        return [r for r in all_recs if r['urgency'] == 'opportunity']
    
    def get_dashboard_summary(self) -> dict:
        """
        Get summary for admin dashboard.
        
        Returns:
            Dict with counts and top recommendations
        """
        all_recs = self.get_all_recommendations()
        
        critical = [r for r in all_recs if r['urgency'] == 'critical']
        warning = [r for r in all_recs if r['urgency'] == 'warning']
        opportunity = [r for r in all_recs if r['urgency'] == 'opportunity']
        healthy = [r for r in all_recs if r['urgency'] == 'healthy']
        
        return {
            'summary': {
                'critical_count': len(critical),
                'warning_count': len(warning),
                'opportunity_count': len(opportunity),
                'healthy_count': len(healthy),
                'total_products': len(all_recs),
            },
            'critical_alerts': critical[:5],  # Top 5 critical
            'opportunities': opportunity[:3],  # Top 3 opportunities
            'top_sellers': self._get_top_sellers(5),
            'low_performers': self._get_low_performers(5),
        }
    
    def _analyze_product(self, product: Product) -> dict:
        """
        Analyze a single product and generate recommendation.
        """
        # Get sales in analysis period
        sales_count = ProductOwnership.objects.filter(
            product=product,
            purchase_date__gte=self.analysis_start
        ).count()
        
        # Calculate sales velocity (units per day)
        velocity = sales_count / self.ANALYSIS_DAYS if self.ANALYSIS_DAYS > 0 else 0
        
        # Apply seasonal adjustment
        category_name = product.category.name if product.category else None
        seasonal_boost = self._get_seasonal_boost(category_name)
        adjusted_velocity = velocity * seasonal_boost
        
        # Calculate days until stockout
        if adjusted_velocity > 0:
            days_until_stockout = product.stock / adjusted_velocity
        else:
            days_until_stockout = None  # No sales, can't predict
        
        # Calculate reorder point
        reorder_point = self._calculate_reorder_point(adjusted_velocity)
        
        # Determine urgency level
        urgency = self._determine_urgency(
            product.stock, 
            days_until_stockout, 
            seasonal_boost,
            velocity
        )
        
        # Calculate recommended order quantity
        recommended_qty = self._calculate_recommended_quantity(
            product.stock,
            adjusted_velocity,
            reorder_point
        )
        
        return {
            'product_id': product.id,
            'product_name': product.name,
            'brand': product.brand,
            'category': category_name,
            'current_stock': product.stock,
            'sales_last_30_days': sales_count,
            'velocity': round(velocity, 2),
            'adjusted_velocity': round(adjusted_velocity, 2),
            'seasonal_boost': seasonal_boost,
            'days_until_stockout': round(days_until_stockout, 1) if days_until_stockout else None,
            'reorder_point': reorder_point,
            'recommended_order_qty': recommended_qty,
            'urgency': urgency,
            'message': self._generate_message(urgency, days_until_stockout, seasonal_boost, recommended_qty),
            'price': float(product.price) if product.price else 0,
            'estimated_order_cost': float(product.price) * recommended_qty if product.price else 0,
        }
    
    def _get_seasonal_boost(self, category_name: str) -> float:
        """Get seasonal demand boost for a category."""
        if not category_name:
            return 1.0
        
        month_boosts = self.SEASONAL_DEMAND.get(self.current_month, {})
        return month_boosts.get(category_name, 1.0)
    
    def _calculate_reorder_point(self, velocity: float) -> int:
        """
        Calculate reorder point.
        
        Formula: Reorder Point = (Daily Velocity × Lead Time) + Safety Stock
        """
        lead_time_demand = velocity * self.LEAD_TIME_DAYS
        safety_stock = velocity * self.SAFETY_STOCK_DAYS
        return max(1, int(lead_time_demand + safety_stock))
    
    def _determine_urgency(self, stock: int, days_until_stockout: float, 
                          seasonal_boost: float, velocity: float) -> str:
        """
        Determine urgency level.
        
        Returns: 'critical', 'warning', 'opportunity', or 'healthy'
        """
        # Out of stock
        if stock == 0:
            return 'critical'
        
        # Critical: Less than CRITICAL_DAYS of stock
        if days_until_stockout is not None and days_until_stockout <= self.CRITICAL_DAYS:
            return 'critical'
        
        # Warning: Less than WARNING_DAYS of stock
        if days_until_stockout is not None and days_until_stockout <= self.WARNING_DAYS:
            return 'warning'
        
        # Opportunity: Seasonal boost coming but low velocity
        if seasonal_boost > 1.2 and velocity < 0.5 and stock < 20:
            return 'opportunity'
        
        return 'healthy'
    
    def _calculate_recommended_quantity(self, stock: int, velocity: float, 
                                        reorder_point: int) -> int:
        """
        Calculate recommended order quantity.
        
        Uses Economic Order Quantity (EOQ) simplified:
        Order enough for 30 days + safety stock
        """
        if velocity == 0:
            return 0  # No demand, don't recommend
        
        # Target: 30 days of stock
        target_stock = int(velocity * 30) + self.SAFETY_STOCK_DAYS
        
        if stock < reorder_point:
            return max(10, target_stock - stock)  # Minimum order: 10 units
        
        return 0  # No order needed
    
    def _generate_message(self, urgency: str, days_until_stockout: float,
                         seasonal_boost: float, recommended_qty: int) -> str:
        """Generate human-readable recommendation message."""
        if urgency == 'critical':
            if days_until_stockout is not None:
                return f"🔴 KRİTİK: {int(days_until_stockout)} gün içinde tükenecek. {recommended_qty} adet sipariş önerilir."
            return f"🔴 KRİTİK: Stok tükenmiş! {recommended_qty} adet acil sipariş verin."
        
        if urgency == 'warning':
            return f"🟡 UYARI: {int(days_until_stockout)} gün içinde tükenebilir. {recommended_qty} adet sipariş planlayın."
        
        if urgency == 'opportunity':
            season_msg = "Yaz sezonu" if self.current_month in [5, 6, 7, 8] else \
                        "Kış sezonu" if self.current_month in [11, 12, 1, 2] else "Sezon"
            return f"⭐ FIRSAT: {season_msg} yaklaşıyor (talep {int((seasonal_boost-1)*100)}% artabilir). {recommended_qty} adet stok önerilir."
        
        return "🟢 Stok durumu sağlıklı."
    
    def _get_top_sellers(self, limit: int = 5) -> list:
        """Get top selling products in the analysis period."""
        top_products = ProductOwnership.objects.filter(
            purchase_date__gte=self.analysis_start
        ).values(
            'product__id', 'product__name', 'product__brand'
        ).annotate(
            sales_count=Count('id')
        ).order_by('-sales_count')[:limit]
        
        return list(top_products)
    
    def _get_low_performers(self, limit: int = 5) -> list:
        """Get products with stock but no/low sales."""
        # Products with stock > 10 but 0 sales in last 30 days
        all_product_ids = set(Product.objects.filter(stock__gt=10).values_list('id', flat=True))
        sold_product_ids = set(
            ProductOwnership.objects.filter(
                purchase_date__gte=self.analysis_start
            ).values_list('product_id', flat=True)
        )
        
        unsold_ids = all_product_ids - sold_product_ids
        
        low_performers = Product.objects.filter(
            id__in=list(unsold_ids)[:limit]
        ).values('id', 'name', 'brand', 'stock')
        
        return list(low_performers)


# API endpoint helper
def get_stock_recommendations_response():
    """Helper function for API views."""
    service = StockIntelligenceService()
    return service.get_dashboard_summary()
