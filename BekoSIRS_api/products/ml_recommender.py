# products/ml_recommender.py
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.decomposition import TruncatedSVD
from .models import Product, ViewHistory, WishlistItem, Review, ProductOwnership

class HybridRecommender:
    def __init__(self):
        self.products_df = None
        self.similarity_matrix = None
        self.user_product_matrix = None
        self.svd_model = None
        self.indices = None
        
        # Load data immediately
        self._load_data()
        self._train_content_model()
        self._train_collaborative_model()

    def _load_data(self):
        """Fetches all products from DB into a DataFrame."""
        products = Product.objects.all().values(
            'id', 'name', 'description', 'brand', 'category__name'
        )
        self.products_df = pd.DataFrame(list(products))
        
        if not self.products_df.empty:
            # Map Product ID to DataFrame Index for fast lookup
            self.indices = pd.Series(self.products_df.index, index=self.products_df['id']).drop_duplicates()

    def _train_content_model(self):
        """Builds Content-Based logic using TF-IDF."""
        if self.products_df is None or self.products_df.empty:
            return

        # Combine text fields
        self.products_df['content'] = (
            self.products_df['name'] + " " + 
            self.products_df['description'].fillna('') + " " + 
            self.products_df['brand'].fillna('') + " " + 
            self.products_df['category__name'].fillna('')
        )

        # Create Vectors
        tfidf = TfidfVectorizer(stop_words='english', max_features=5000)
        tfidf_matrix = tfidf.fit_transform(self.products_df['content'])

        # Calculate Similarity
        self.similarity_matrix = cosine_similarity(tfidf_matrix)

    def _train_collaborative_model(self):
        """Builds Collaborative Filtering logic using SVD."""
        # 1. Fetch all interactions
        views = pd.DataFrame(list(ViewHistory.objects.all().values('customer_id', 'product_id', 'view_count')))
        wishlist = pd.DataFrame(list(WishlistItem.objects.filter(wishlist__customer__isnull=False).values('wishlist__customer_id', 'product_id')))
        reviews = pd.DataFrame(list(Review.objects.all().values('customer_id', 'product_id', 'rating')))
        purchases = pd.DataFrame(list(ProductOwnership.objects.all().values('customer_id', 'product_id')))

        # 2. Assign Weights (The "Interest Score")
        interactions = []

        if not views.empty:
            # Views: 1 point, capped at 5
            views['score'] = views['view_count'].apply(lambda x: min(x, 5) * 1.0)
            interactions.append(views[['customer_id', 'product_id', 'score']])

        if not wishlist.empty:
            # Wishlist: 3 points
            wishlist = wishlist.rename(columns={'wishlist__customer_id': 'customer_id'})
            wishlist['score'] = 3.0
            interactions.append(wishlist)

        if not reviews.empty:
            # Reviews: The rating itself (1-5 points)
            reviews = reviews.rename(columns={'rating': 'score'})
            interactions.append(reviews)

        if not purchases.empty:
            # Purchases: 5 points (Highest intent)
            purchases['score'] = 5.0
            interactions.append(purchases)

        # 3. Create the Matrix
        if not interactions:
            self.user_product_matrix = None
            return

        all_interactions = pd.concat(interactions)
        self.user_product_matrix = all_interactions.groupby(['customer_id', 'product_id'])['score'].sum().unstack(fill_value=0)

        # 4. Apply SVD (Singular Value Decomposition)
        if self.user_product_matrix.shape[0] > 5 and self.user_product_matrix.shape[1] > 5:
            n_components = min(12, min(self.user_product_matrix.shape) - 1)
            self.svd_model = TruncatedSVD(n_components=n_components, random_state=42)
            self.svd_matrix = self.svd_model.fit_transform(self.user_product_matrix)
            self.corr_matrix = np.corrcoef(self.svd_matrix)

    def recommend(self, user, top_n=5):
        """Main function to get recommendations."""
        if self.products_df is None:
            return []

        # NOTE: We currently force Content-Based because it is more reliable for
        # immediate "Recency" reactions than SVD on small datasets.
        return self._recommend_content_based(user, top_n)

    def _recommend_content_based(self, user, top_n):
        """User profile weighted by content similarity."""
        # This now includes the Recency Boost!
        user_interests = self._get_user_interactions_dict(user)
        
        if not user_interests:
            return []

        product_scores = np.zeros(len(self.products_df))
        
        for product_id, weight in user_interests.items():
            if product_id not in self.indices: continue
            idx = self.indices[product_id]
            # Multiply similarity by the user's interest weight
            product_scores += self.similarity_matrix[idx] * weight

        return self._format_results(product_scores, list(user_interests.keys()), top_n)

    def _get_user_interactions_dict(self, user):
        """Helper to gather raw interest scores for a single user."""
        interactions = {}

        # 1. Purchases (Strong Base Interest: 5.0)
        for pid in ProductOwnership.objects.filter(customer=user).values_list('product_id', flat=True):
            interactions[pid] = interactions.get(pid, 0) + 5.0

        # 2. Reviews > 3 (High Satisfaction: 4.0)
        for pid in Review.objects.filter(customer=user, rating__gt=3).values_list('product_id', flat=True):
            interactions[pid] = interactions.get(pid, 0) + 4.0

        # 3. Wishlist (Intent to Buy: 3.0)
        for pid in WishlistItem.objects.filter(wishlist__customer=user).values_list('product_id', flat=True):
            interactions[pid] = interactions.get(pid, 0) + 3.0

        # ------------------------------------------------------------
        # 🔥 FIX: RECENCY BOOST
        # Instead of just taking the "count" (which favors old favorites),
        # we take the most RECENT views and give them massive points.
        # ------------------------------------------------------------
        recent_views = ViewHistory.objects.filter(customer=user).order_by('-viewed_at')[:10]

        for i, v in enumerate(recent_views):
            # i=0 (most recent) -> Bonus +10
            # i=1 (second most recent) -> Bonus +9
            # ...
            recency_bonus = 10 - i 
            
            # Add to existing score (or start fresh)
            interactions[v.product_id] = interactions.get(v.product_id, 0) + recency_bonus

        return interactions

    def _format_results(self, scores, exclude_ids, top_n):
        # Zero out already seen products so we don't recommend what they already viewed/bought
        for pid in exclude_ids:
            if pid in self.indices:
                scores[self.indices[pid]] = 0

        # Get top indices sorted by score
        top_indices = scores.argsort()[::-1][:top_n]
        
        results = []
        for idx in top_indices:
            if scores[idx] > 0:
                prod_id = self.products_df.iloc[idx]['id']
                try:
                    obj = Product.objects.get(id=prod_id)
                    results.append({'product': obj, 'score': scores[idx]})
                except Product.DoesNotExist:
                    continue
        return results

# Alias for backward compatibility if needed
ContentBasedRecommender = HybridRecommender