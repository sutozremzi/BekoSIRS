# products/sales_forecast_service.py
"""
Sales Forecasting Service.

Provides sales predictions using:
1. Simple Moving Average (SMA)
2. Seasonal adjustment factors
3. Trend analysis (increasing/decreasing/stable)

Usage:
    from products.sales_forecast_service import SalesForecastService
    
    service = SalesForecastService()
    forecasts = service.forecast_product(product_id, months=3)
    all_forecasts = service.forecast_all_products()
"""

from django.utils import timezone
from django.db.models import Count
from django.db.models.functions import TruncMonth
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from decimal import Decimal
import logging
from typing import List, Dict, Optional, Tuple

from .models import Product, ProductOwnership, Category

logger = logging.getLogger(__name__)


class SalesForecastService:
    """
    Sales Forecasting Engine using Moving Average with Seasonal Adjustment.
    
    Configuration:
    - LOOKBACK_MONTHS: Number of months to analyze (default: 6)
    - FORECAST_MONTHS: Number of months to predict (default: 3)
    - MIN_DATA_POINTS: Minimum sales data points required (default: 3)
    """
    
    LOOKBACK_MONTHS = 6
    FORECAST_MONTHS = 3
    MIN_DATA_POINTS = 3
    
    # Seasonal factors by month (1.0 = normal, >1 = high, <1 = low)
    # Based on Turkish appliance market patterns
    SEASONAL_FACTORS = {
        # Category -> {month: factor}
        'Klima': {1: 0.3, 2: 0.3, 3: 0.5, 4: 0.8, 5: 1.5, 6: 2.0, 7: 2.0, 8: 1.5, 9: 0.8, 10: 0.4, 11: 0.3, 12: 0.3},
        'Buzdolabı': {1: 0.8, 2: 0.8, 3: 0.9, 4: 1.0, 5: 1.2, 6: 1.5, 7: 1.5, 8: 1.3, 9: 1.0, 10: 0.9, 11: 0.8, 12: 0.8},
        'Kombi': {1: 1.5, 2: 1.3, 3: 1.0, 4: 0.6, 5: 0.4, 6: 0.3, 7: 0.3, 8: 0.4, 9: 0.8, 10: 1.2, 11: 1.5, 12: 1.5},
        'Isıtıcı': {1: 1.8, 2: 1.5, 3: 1.0, 4: 0.5, 5: 0.3, 6: 0.2, 7: 0.2, 8: 0.3, 9: 0.6, 10: 1.2, 11: 1.5, 12: 1.8},
        'TV': {1: 0.9, 2: 0.8, 3: 0.8, 4: 0.9, 5: 1.0, 6: 1.0, 7: 0.9, 8: 0.9, 9: 1.0, 10: 1.1, 11: 1.3, 12: 1.5},
        'Çamaşır Makinesi': {1: 1.0, 2: 1.0, 3: 1.0, 4: 1.0, 5: 1.0, 6: 0.9, 7: 0.9, 8: 1.0, 9: 1.2, 10: 1.1, 11: 1.0, 12: 1.0},
    }
    
    # Default seasonal factors (no strong seasonality)
    DEFAULT_SEASONAL = {m: 1.0 for m in range(1, 13)}
    
    def __init__(self):
        self.today = timezone.now().date()
    
    def forecast_product(self, product_id: int, months: int = None) -> Dict:
        """
        Generate sales forecast for a specific product.
        
        Args:
            product_id: Product ID
            months: Number of months to forecast (default: FORECAST_MONTHS)
            
        Returns:
            Dict with product info, forecasts, trend, and confidence
        """
        months = months or self.FORECAST_MONTHS
        
        try:
            product = Product.objects.select_related('category').get(id=product_id)
        except Product.DoesNotExist:
            return {'error': f'Product {product_id} not found'}
        
        # Get historical sales data
        historical = self._get_historical_sales(product)
        
        if len(historical) < self.MIN_DATA_POINTS:
            return {
                'product_id': product.id,
                'product_name': product.name,
                'error': 'Yetersiz satış verisi',
                'data_points': len(historical),
                'required': self.MIN_DATA_POINTS
            }
        
        # Calculate moving average
        moving_avg = self._calculate_moving_average(historical)
        
        # Detect trend
        trend, trend_factor = self._detect_trend(historical)
        
        # Get seasonal factors for this product's category
        category_name = product.category.name if product.category else None
        seasonal_factors = self._get_seasonal_factors(category_name)
        
        # Generate forecasts
        forecasts = []
        base_month = self.today.replace(day=1)
        
        for i in range(1, months + 1):
            forecast_month = base_month + relativedelta(months=i)
            month_num = forecast_month.month
            
            # Apply seasonal adjustment
            seasonal = seasonal_factors.get(month_num, 1.0)
            
            # Calculate predicted sales
            predicted = max(0, round(moving_avg * seasonal * trend_factor))
            
            # Calculate confidence (decreases with distance)
            confidence = max(0.5, 0.95 - (i * 0.08))
            
            forecasts.append({
                'month': forecast_month.strftime('%Y-%m'),
                'month_name': self._get_turkish_month_name(forecast_month),
                'predicted_sales': predicted,
                'confidence': round(confidence, 2),
                'seasonal_factor': seasonal
            })
        
        return {
            'product_id': product.id,
            'product_name': product.name,
            'brand': product.brand,
            'category': category_name,
            'current_stock': product.stock,
            'historical_data': historical,
            'moving_average': round(moving_avg, 2),
            'trend': trend,
            'trend_factor': trend_factor,
            'forecasts': forecasts,
            'recommendation': self._generate_recommendation(product, forecasts, moving_avg)
        }
    
    def forecast_all_products(self, min_sales: int = 1) -> List[Dict]:
        """
        Generate forecasts for all products with sales history.
        
        Args:
            min_sales: Minimum total sales to include product
            
        Returns:
            List of forecast dicts, sorted by predicted sales
        """
        # Find products with sales
        products_with_sales = ProductOwnership.objects.values(
            'product_id'
        ).annotate(
            total=Count('id')
        ).filter(
            total__gte=min_sales
        ).values_list('product_id', flat=True)
        
        forecasts = []
        for product_id in products_with_sales:
            forecast = self.forecast_product(product_id)
            if 'error' not in forecast:
                forecasts.append(forecast)
        
        # Sort by next month's predicted sales (descending)
        forecasts.sort(
            key=lambda x: x['forecasts'][0]['predicted_sales'] if x['forecasts'] else 0,
            reverse=True
        )
        
        return forecasts
    
    def get_category_forecast(self, category_id: int, months: int = 3) -> Dict:
        """
        Get aggregated forecast for an entire category.
        """
        category = Category.objects.get(id=category_id)
        products = Product.objects.filter(category=category)
        
        category_forecasts = []
        for product in products:
            forecast = self.forecast_product(product.id, months)
            if 'forecasts' in forecast:
                category_forecasts.append(forecast)
        
        # Aggregate
        aggregated = {}
        for fc in category_forecasts:
            for f in fc.get('forecasts', []):
                month = f['month']
                if month not in aggregated:
                    aggregated[month] = {'month': month, 'predicted_sales': 0, 'products': 0}
                aggregated[month]['predicted_sales'] += f['predicted_sales']
                aggregated[month]['products'] += 1
        
        return {
            'category_id': category.id,
            'category_name': category.name,
            'product_count': len(category_forecasts),
            'forecasts': list(aggregated.values())
        }
    
    def _get_historical_sales(self, product: Product) -> List[Dict]:
        """Get monthly sales data for the past LOOKBACK_MONTHS."""
        start_date = self.today - relativedelta(months=self.LOOKBACK_MONTHS)
        
        monthly_sales = ProductOwnership.objects.filter(
            product=product,
            purchase_date__gte=start_date
        ).annotate(
            month=TruncMonth('purchase_date')
        ).values('month').annotate(
            sales=Count('id')
        ).order_by('month')
        
        # Fill missing months with 0
        result = []
        current = start_date.replace(day=1)
        sales_dict = {s['month'].date() if hasattr(s['month'], 'date') else s['month']: s['sales'] 
                      for s in monthly_sales}
        
        while current <= self.today:
            result.append({
                'month': current.strftime('%Y-%m'),
                'sales': sales_dict.get(current, 0)
            })
            current += relativedelta(months=1)
        
        return result
    
    def _calculate_moving_average(self, historical: List[Dict]) -> float:
        """Calculate simple moving average of sales."""
        if not historical:
            return 0
        
        sales = [h['sales'] for h in historical]
        
        # Use last 3 months for SMA
        recent = sales[-3:] if len(sales) >= 3 else sales
        return sum(recent) / len(recent)
    
    def _detect_trend(self, historical: List[Dict]) -> Tuple[str, float]:
        """
        Detect sales trend.
        
        Returns:
            (trend_name, trend_factor)
            - trend_name: 'increasing', 'decreasing', 'stable'
            - trend_factor: multiplier (e.g., 1.1 for increasing)
        """
        if len(historical) < 3:
            return ('stable', 1.0)
        
        sales = [h['sales'] for h in historical]
        
        # Compare first half average to second half average
        mid = len(sales) // 2
        first_half_avg = sum(sales[:mid]) / mid if mid > 0 else 0
        second_half_avg = sum(sales[mid:]) / (len(sales) - mid) if len(sales) - mid > 0 else 0
        
        if first_half_avg == 0:
            if second_half_avg > 0:
                return ('increasing', 1.2)
            return ('stable', 1.0)
        
        change_ratio = second_half_avg / first_half_avg
        
        if change_ratio > 1.15:
            return ('increasing', min(change_ratio, 1.3))  # Cap at 30% growth
        elif change_ratio < 0.85:
            return ('decreasing', max(change_ratio, 0.7))  # Floor at 30% decline
        else:
            return ('stable', 1.0)
    
    def _get_seasonal_factors(self, category_name: str) -> Dict[int, float]:
        """Get seasonal factors for a category."""
        if category_name in self.SEASONAL_FACTORS:
            return self.SEASONAL_FACTORS[category_name]
        return self.DEFAULT_SEASONAL
    
    def _get_turkish_month_name(self, dt: date) -> str:
        """Get Turkish month name."""
        months = {
            1: 'Ocak', 2: 'Şubat', 3: 'Mart', 4: 'Nisan',
            5: 'Mayıs', 6: 'Haziran', 7: 'Temmuz', 8: 'Ağustos',
            9: 'Eylül', 10: 'Ekim', 11: 'Kasım', 12: 'Aralık'
        }
        return f"{months[dt.month]} {dt.year}"
    
    def _generate_recommendation(self, product: Product, forecasts: List[Dict], 
                                  moving_avg: float) -> str:
        """Generate actionable recommendation based on forecast."""
        if not forecasts:
            return "Veri yetersiz"
        
        next_month = forecasts[0]
        predicted = next_month['predicted_sales']
        
        # Stock adequacy check
        if product.stock < predicted:
            shortage = predicted - product.stock
            return f"⚠️ Stok yetersiz! Önümüzdeki ay için {shortage} adet ek stok önerilir."
        
        # Trend-based recommendations
        total_predicted = sum(f['predicted_sales'] for f in forecasts)
        if product.stock > total_predicted * 1.5:
            excess = product.stock - total_predicted
            return f"📉 Fazla stok! {excess} adet fazla stok bulunuyor."
        
        if next_month['seasonal_factor'] > 1.3:
            return f"📈 Yüksek sezon yaklaşıyor! Stok artırımı düşünülebilir."
        
        return "✅ Stok durumu dengeli."


# Helper function for API views
def get_sales_forecast_summary():
    """Get summary for dashboard."""
    service = SalesForecastService()
    forecasts = service.forecast_all_products()
    
    return {
        'total_products': len(forecasts),
        'top_forecasts': forecasts[:5],
        'increasing_trend': [f for f in forecasts if f.get('trend') == 'increasing'][:5],
        'decreasing_trend': [f for f in forecasts if f.get('trend') == 'decreasing'][:5],
    }
