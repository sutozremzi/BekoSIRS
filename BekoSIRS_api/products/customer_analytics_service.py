# products/customer_analytics_service.py
"""
Customer Analytics Service - Customer Lifetime Value (CLV) Analysis.

Provides customer value analysis:
1. CLV calculation based on purchase history
2. Customer segmentation (VIP, Premium, Standard, Low)
3. Churn risk prediction
4. RFM analysis (Recency, Frequency, Monetary)

Usage:
    from products.customer_analytics_service import CustomerAnalyticsService
    
    service = CustomerAnalyticsService()
    clv = service.calculate_clv(customer_id)
    all_customers = service.analyze_all_customers()
"""

from django.utils import timezone
from django.db.models import Count, Sum, Avg, Max, Min
from datetime import timedelta
from decimal import Decimal
import logging
from typing import List, Dict, Optional

from .models import CustomUser, ProductOwnership, ServiceRequest, Review

logger = logging.getLogger(__name__)


class CustomerAnalyticsService:
    """
    Customer Lifetime Value (CLV) and Analytics Engine.
    
    CLV Formula:
        CLV = (Average Order Value × Purchase Frequency × Customer Lifespan) - Acquisition Cost
        
    Segmentation Thresholds:
        - VIP: CLV > 15000 TL
        - Premium: CLV > 8000 TL
        - Standard: CLV > 3000 TL
        - Low: CLV <= 3000 TL
    
    Churn Risk Factors:
        - Days since last purchase > 180: High risk
        - Days since last purchase > 90: Medium risk
        - Active in last 90 days: Low risk
    """
    
    # Segmentation thresholds (in TL)
    VIP_THRESHOLD = 15000
    PREMIUM_THRESHOLD = 8000
    STANDARD_THRESHOLD = 3000
    
    # Churn risk thresholds (in days)
    HIGH_CHURN_DAYS = 180
    MEDIUM_CHURN_DAYS = 90
    
    # Average customer acquisition cost (estimated)
    ACQUISITION_COST = 500
    
    # Average customer lifespan in years
    AVG_LIFESPAN_YEARS = 5
    
    def __init__(self):
        self.today = timezone.now().date()
    
    def calculate_clv(self, customer_id: int) -> Dict:
        """
        Calculate Customer Lifetime Value for a specific customer.
        
        Returns:
            Dict with CLV metrics, segments, and recommendations
        """
        try:
            customer = CustomUser.objects.get(id=customer_id)
        except CustomUser.DoesNotExist:
            return {'error': f'Customer {customer_id} not found'}
        
        # Get purchase history
        purchases = ProductOwnership.objects.filter(
            customer=customer
        ).select_related('product')
        
        if not purchases.exists():
            return {
                'customer_id': customer.id,
                'customer_name': f"{customer.first_name} {customer.last_name}".strip() or customer.username,
                'error': 'Satın alma geçmişi yok',
                'segment': 'new',
                'clv': 0
            }
        
        # Calculate metrics
        total_spent = sum(p.product.price or 0 for p in purchases)
        order_count = purchases.count()
        avg_order_value = total_spent / order_count if order_count > 0 else 0
        
        # Calculate purchase frequency (orders per year)
        first_purchase = purchases.order_by('purchase_date').first().purchase_date
        last_purchase = purchases.order_by('-purchase_date').first().purchase_date
        
        customer_lifespan_days = (last_purchase - first_purchase).days + 1
        customer_lifespan_years = max(customer_lifespan_days / 365, 0.25)  # Min 3 months
        
        purchase_frequency = order_count / customer_lifespan_years
        
        # Calculate CLV
        projected_lifespan = min(self.AVG_LIFESPAN_YEARS, customer_lifespan_years * 2)
        clv = (float(avg_order_value) * purchase_frequency * projected_lifespan) - self.ACQUISITION_COST
        clv = max(0, clv)
        
        # Determine segment
        segment = self._determine_segment(clv)
        
        # Calculate churn risk
        days_since_purchase = (self.today - last_purchase).days
        churn_risk, churn_score = self._calculate_churn_risk(days_since_purchase)
        
        # RFM Analysis
        rfm = self._calculate_rfm(customer, purchases)
        
        # Get service history
        service_count = ServiceRequest.objects.filter(customer=customer).count()
        
        # Get review count
        review_count = Review.objects.filter(customer=customer, is_approved=True).count()
        
        return {
            'customer_id': customer.id,
            'customer_name': f"{customer.first_name} {customer.last_name}".strip() or customer.username,
            'email': customer.email,
            'member_since': customer.date_joined.date() if customer.date_joined else None,
            
            # Purchase metrics
            'total_spent': float(total_spent),
            'order_count': order_count,
            'avg_order_value': round(float(avg_order_value), 2),
            'purchase_frequency': round(purchase_frequency, 2),
            
            # Dates
            'first_purchase': first_purchase,
            'last_purchase': last_purchase,
            'days_since_purchase': days_since_purchase,
            'customer_lifespan_years': round(customer_lifespan_years, 2),
            
            # CLV and Segmentation
            'clv': round(clv, 2),
            'segment': segment,
            'segment_display': self._get_segment_display(segment),
            
            # Churn risk
            'churn_risk': churn_risk,
            'churn_score': churn_score,
            
            # RFM
            'rfm': rfm,
            
            # Engagement
            'service_requests': service_count,
            'reviews_written': review_count,
            
            # Recommendations
            'recommendations': self._generate_recommendations(segment, churn_risk, days_since_purchase)
        }
    
    def analyze_all_customers(self, segment_filter: str = None) -> Dict:
        """
        Analyze all customers and return summary.
        
        Args:
            segment_filter: Optional filter by segment ('vip', 'premium', 'standard', 'low')
            
        Returns:
            Dict with customer analytics summary
        """
        customers = CustomUser.objects.filter(role='customer', is_active=True)
        
        analytics = []
        segments = {'vip': 0, 'premium': 0, 'standard': 0, 'low': 0, 'new': 0}
        churn_risks = {'high': 0, 'medium': 0, 'low': 0}
        total_clv = 0
        
        for customer in customers:
            result = self.calculate_clv(customer.id)
            
            if 'error' not in result or result.get('segment') == 'new':
                segment = result.get('segment', 'new')
                segments[segment] = segments.get(segment, 0) + 1
                
                if 'churn_risk' in result:
                    churn_risks[result['churn_risk']] = churn_risks.get(result['churn_risk'], 0) + 1
                
                total_clv += result.get('clv', 0)
                
                # Apply segment filter
                if segment_filter is None or segment == segment_filter:
                    analytics.append(result)
        
        # Sort by CLV descending
        analytics.sort(key=lambda x: x.get('clv', 0), reverse=True)
        
        return {
            'total_customers': len(analytics),
            'segments': segments,
            'churn_risks': churn_risks,
            'total_clv': round(total_clv, 2),
            'avg_clv': round(total_clv / len(analytics), 2) if analytics else 0,
            'top_customers': analytics[:10],
            'at_risk_customers': [c for c in analytics if c.get('churn_risk') == 'high'][:10]
        }
    
    def get_segment_customers(self, segment: str) -> List[Dict]:
        """Get all customers in a specific segment."""
        result = self.analyze_all_customers(segment_filter=segment)
        return result.get('top_customers', [])
    
    def _determine_segment(self, clv: float) -> str:
        """Determine customer segment based on CLV."""
        if clv >= self.VIP_THRESHOLD:
            return 'vip'
        elif clv >= self.PREMIUM_THRESHOLD:
            return 'premium'
        elif clv >= self.STANDARD_THRESHOLD:
            return 'standard'
        else:
            return 'low'
    
    def _get_segment_display(self, segment: str) -> Dict:
        """Get display info for segment."""
        segments = {
            'vip': {'name': 'VIP', 'color': '#f59e0b', 'icon': '👑', 'description': 'En değerli müşteriler'},
            'premium': {'name': 'Premium', 'color': '#8b5cf6', 'icon': '⭐', 'description': 'Yüksek değerli müşteriler'},
            'standard': {'name': 'Standart', 'color': '#3b82f6', 'icon': '👤', 'description': 'Ortalama müşteriler'},
            'low': {'name': 'Düşük', 'color': '#6b7280', 'icon': '📉', 'description': 'Düşük değerli müşteriler'},
            'new': {'name': 'Yeni', 'color': '#10b981', 'icon': '🆕', 'description': 'Yeni müşteriler'}
        }
        return segments.get(segment, segments['new'])
    
    def _calculate_churn_risk(self, days_since_purchase: int) -> tuple:
        """
        Calculate churn risk based on days since last purchase.
        
        Returns:
            (risk_level, risk_score)
        """
        if days_since_purchase >= self.HIGH_CHURN_DAYS:
            return ('high', min(1.0, days_since_purchase / 365))
        elif days_since_purchase >= self.MEDIUM_CHURN_DAYS:
            return ('medium', 0.5)
        else:
            return ('low', max(0.0, days_since_purchase / 180))
    
    def _calculate_rfm(self, customer: CustomUser, purchases) -> Dict:
        """
        Calculate RFM (Recency, Frequency, Monetary) scores.
        Each score is 1-5 (5 being best).
        """
        if not purchases:
            return {'recency': 0, 'frequency': 0, 'monetary': 0, 'score': 0}
        
        # Recency (days since last purchase)
        last_purchase = purchases.order_by('-purchase_date').first().purchase_date
        days = (self.today - last_purchase).days
        
        if days <= 30:
            r_score = 5
        elif days <= 60:
            r_score = 4
        elif days <= 90:
            r_score = 3
        elif days <= 180:
            r_score = 2
        else:
            r_score = 1
        
        # Frequency (number of purchases)
        count = purchases.count()
        if count >= 10:
            f_score = 5
        elif count >= 5:
            f_score = 4
        elif count >= 3:
            f_score = 3
        elif count >= 2:
            f_score = 2
        else:
            f_score = 1
        
        # Monetary (total spent)
        total = sum(p.product.price or 0 for p in purchases)
        if total >= 50000:
            m_score = 5
        elif total >= 25000:
            m_score = 4
        elif total >= 10000:
            m_score = 3
        elif total >= 5000:
            m_score = 2
        else:
            m_score = 1
        
        return {
            'recency': r_score,
            'frequency': f_score,
            'monetary': m_score,
            'score': (r_score + f_score + m_score) / 3
        }
    
    def _generate_recommendations(self, segment: str, churn_risk: str, 
                                   days_since_purchase: int) -> List[str]:
        """Generate actionable recommendations for the customer."""
        recommendations = []
        
        # Segment-based recommendations
        if segment == 'vip':
            recommendations.append("👑 VIP müşteri - Özel indirimler ve erken erişim sunulabilir")
        elif segment == 'premium':
            recommendations.append("⭐ Premium müşteri - Sadakat programına davet edilebilir")
        elif segment == 'low':
            recommendations.append("📈 Değer artırma fırsatı - Cross-sell kampanyası önerilir")
        
        # Churn-based recommendations
        if churn_risk == 'high':
            recommendations.append(f"⚠️ Yüksek kayıp riski ({days_since_purchase} gün) - 'Özledik' kampanyası gönder")
            recommendations.append("🎁 Geri kazanım için özel indirim kodu önerilir")
        elif churn_risk == 'medium':
            recommendations.append(f"🔔 Orta kayıp riski ({days_since_purchase} gün) - Yeni ürün duyurusu gönder")
        
        return recommendations


# Helper function for API views
def get_customer_analytics_summary():
    """Get summary for dashboard."""
    service = CustomerAnalyticsService()
    return service.analyze_all_customers()
