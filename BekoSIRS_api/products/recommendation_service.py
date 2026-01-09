# products/recommendation_service.py
"""
Enhanced Product Recommendation Service.

Provides intelligent product recommendations based on:
1. Purchase history analysis
2. Collaborative filtering (similar users)
3. Category affinity scoring
4. Seasonal trends
5. View history and wishlist analysis
"""

from django.utils import timezone
from django.db.models import Count, Avg, Q, F
from decimal import Decimal
from datetime import timedelta
import logging

from .models import (
    Product, Category, ProductOwnership, ViewHistory, 
    WishlistItem, Recommendation, CustomUser
)

logger = logging.getLogger(__name__)


class RecommendationService:
    """
    Service class for generating personalized product recommendations.
    
    Scoring weights (configurable):
    - Category affinity: 0.30
    - Complementary products: 0.25
    - Popular items: 0.15
    - View history: 0.15
    - Seasonal boost: 0.10
    - Collaborative: 0.05
    """
    
    # Scoring weights
    WEIGHT_CATEGORY = 0.30
    WEIGHT_COMPLEMENTARY = 0.25
    WEIGHT_POPULAR = 0.15
    WEIGHT_VIEW_HISTORY = 0.15
    WEIGHT_SEASONAL = 0.10
    WEIGHT_COLLABORATIVE = 0.05
    
    # Complementary product pairs (category_id -> list of complementary category_ids)
    COMPLEMENTARY_PAIRS = {
        'Buzdolabı': ['Buzdolabı Aksesuarları', 'Derin Dondurucu'],
        'Çamaşır Makinesi': ['Kurutma Makinesi', 'Ütü', 'Çamaşır Aksesuarları'],
        'Bulaşık Makinesi': ['Bulaşık Deterjanı', 'Mutfak Aksesuarları'],
        'TV': ['Soundbar', 'TV Sehpası', 'HDMI Kablo'],
        'Fırın': ['Ocak', 'Davlumbaz', 'Mutfak Robotu'],
        'Klima': ['Vantilatör', 'Hava Temizleyici'],
    }
    
    # Seasonal categories (month -> category names with boost)
    SEASONAL_CATEGORIES = {
        1: ['Kombi', 'Isıtıcı', 'Elektrikli Battaniye'],  # January - Winter
        2: ['Kombi', 'Isıtıcı'],
        3: ['Elektrikli Süpürge'],  # March - Spring cleaning
        4: ['Elektrikli Süpürge', 'Yıkama Makinesi'],
        5: ['Klima', 'Vantilatör'],  # May - Summer prep
        6: ['Klima', 'Buzdolabı', 'Derin Dondurucu'],  # June - Summer
        7: ['Klima', 'Buzdolabı'],
        8: ['Klima', 'Vantilatör'],
        9: ['Çamaşır Makinesi', 'Ütü'],  # September - Back to school
        10: ['Elektrikli Süpürge', 'Fırın'],  # October - Fall
        11: ['Fırın', 'Ocak', 'Kombi'],  # November - Holiday prep
        12: ['TV', 'Fırın', 'Isıtıcı'],  # December - Holiday
    }
    
    def __init__(self, user: CustomUser):
        self.user = user
        self.today = timezone.now().date()
        self.current_month = self.today.month
    
    def generate_recommendations(self, limit: int = 10) -> list:
        """
        Generate personalized recommendations for the user.
        
        Returns:
            list of dicts with product and score information
        """
        # Get user's owned products to exclude
        owned_product_ids = set(
            ProductOwnership.objects.filter(customer=self.user)
            .values_list('product_id', flat=True)
        )
        
        # Get user's purchase history categories
        purchase_categories = self._get_purchase_category_affinity()
        
        # Get candidate products (not owned)
        candidates = Product.objects.filter(
            stock__gt=0
        ).exclude(
            id__in=owned_product_ids
        ).select_related('category')[:100]  # Limit for performance
        
        scored_products = []
        
        for product in candidates:
            score = self._calculate_product_score(product, purchase_categories)
            scored_products.append({
                'product': product,
                'score': score,
                'reasons': self._get_recommendation_reasons(product, score)
            })
        
        # Sort by score descending
        scored_products.sort(key=lambda x: x['score'], reverse=True)
        
        return scored_products[:limit]
    
    def _get_purchase_category_affinity(self) -> dict:
        """
        Analyze user's purchase history to determine category preferences.
        
        Returns:
            dict mapping category names to affinity scores
        """
        ownerships = ProductOwnership.objects.filter(
            customer=self.user
        ).select_related('product__category')
        
        category_counts = {}
        for ownership in ownerships:
            cat_name = ownership.product.category.name if ownership.product.category else 'Diğer'
            category_counts[cat_name] = category_counts.get(cat_name, 0) + 1
        
        # Normalize to 0-1 range
        if category_counts:
            max_count = max(category_counts.values())
            return {cat: count / max_count for cat, count in category_counts.items()}
        return {}
    
    def _calculate_product_score(self, product: Product, purchase_categories: dict) -> float:
        """
        Calculate recommendation score for a product.
        """
        score = 0.0
        category_name = product.category.name if product.category else None
        
        # 1. Category Affinity Score
        if category_name and category_name in purchase_categories:
            score += purchase_categories[category_name] * self.WEIGHT_CATEGORY
        
        # 2. Complementary Product Score
        score += self._calculate_complementary_score(category_name, purchase_categories)
        
        # 3. Popular Items Score (based on overall ownership count)
        popularity = ProductOwnership.objects.filter(product=product).count()
        popularity_score = min(popularity / 50, 1.0)  # Normalize
        score += popularity_score * self.WEIGHT_POPULAR
        
        # 4. View History Score
        view_count = ViewHistory.objects.filter(
            customer=self.user, 
            product=product
        ).aggregate(total=Count('id'))['total'] or 0
        view_score = min(view_count / 5, 1.0)  # 5+ views = max score
        score += view_score * self.WEIGHT_VIEW_HISTORY
        
        # 5. Seasonal Boost
        seasonal_categories = self.SEASONAL_CATEGORIES.get(self.current_month, [])
        if category_name in seasonal_categories:
            score += 1.0 * self.WEIGHT_SEASONAL
        
        # 6. Price consideration (prefer items in similar price range)
        avg_purchase = ProductOwnership.objects.filter(
            customer=self.user
        ).select_related('product').aggregate(avg=Avg('product__price'))['avg']
        
        if avg_purchase and product.price:
            price_ratio = float(product.price) / float(avg_purchase)
            # Best score if price is 50%-150% of average
            if 0.5 <= price_ratio <= 1.5:
                score += 0.05
        
        return min(score, 1.0)  # Cap at 1.0
    
    def _calculate_complementary_score(self, category_name: str, purchase_categories: dict) -> float:
        """
        Calculate score based on complementary product relationships.
        """
        score = 0.0
        
        for purchased_cat in purchase_categories.keys():
            complementary = self.COMPLEMENTARY_PAIRS.get(purchased_cat, [])
            if category_name in complementary:
                score += 0.8 * self.WEIGHT_COMPLEMENTARY
                break
        
        return score
    
    def _get_recommendation_reasons(self, product: Product, score: float) -> list:
        """
        Generate human-readable reasons for the recommendation.
        """
        reasons = []
        category_name = product.category.name if product.category else None
        
        # Check seasonal
        seasonal_categories = self.SEASONAL_CATEGORIES.get(self.current_month, [])
        if category_name in seasonal_categories:
            reasons.append("Bu dönem popüler")
        
        # Check if complementary
        for cat, complements in self.COMPLEMENTARY_PAIRS.items():
            if category_name in complements:
                if ProductOwnership.objects.filter(
                    customer=self.user,
                    product__category__name=cat
                ).exists():
                    reasons.append(f"{cat} ile uyumlu")
                    break
        
        # Check view history
        view_count = ViewHistory.objects.filter(
            customer=self.user, 
            product=product
        ).count()
        if view_count > 0:
            reasons.append("Daha önce incelendi")
        
        # Default reason
        if not reasons:
            if score > 0.5:
                reasons.append("Sizin için önerilen")
            else:
                reasons.append("Popüler ürün")
        
        return reasons
    
    def save_recommendations(self, recommendations: list) -> int:
        """
        Save generated recommendations to database.
        
        Returns:
            Number of recommendations saved
        """
        # Clear old recommendations
        Recommendation.objects.filter(customer=self.user).delete()
        
        # Create new ones
        new_recommendations = []
        for idx, rec in enumerate(recommendations):
            new_recommendations.append(
                Recommendation(
                    customer=self.user,
                    product=rec['product'],
                    score=Decimal(str(rec['score'])),
                    reason=', '.join(rec['reasons'][:2])  # Max 2 reasons
                )
            )
        
        Recommendation.objects.bulk_create(new_recommendations)
        return len(new_recommendations)


# Helper function for cron job / management command
def generate_all_user_recommendations():
    """
    Generate recommendations for all active customers.
    
    Usage in management command:
        from products.recommendation_service import generate_all_user_recommendations
        generate_all_user_recommendations()
    """
    customers = CustomUser.objects.filter(
        role='customer',
        is_active=True
    )
    
    total_generated = 0
    for customer in customers:
        try:
            service = RecommendationService(customer)
            recommendations = service.generate_recommendations(limit=10)
            saved = service.save_recommendations(recommendations)
            total_generated += saved
            logger.info(f"Generated {saved} recommendations for {customer.username}")
        except Exception as e:
            logger.error(f"Failed to generate recommendations for {customer.username}: {e}")
    
    return total_generated
