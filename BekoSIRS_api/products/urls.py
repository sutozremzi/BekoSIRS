# products/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from products.views import my_products_direct, profile_view, notification_settings_view, DashboardSummaryView
from .views import (
    ProductViewSet,
    CategoryViewSet,
    UserManagementViewSet,
    GroupViewSet,
    CustomTokenObtainPairView,
    ProductOwnershipViewSet,
    # Yeni eklenen ViewSet'ler
    WishlistViewSet,
    ViewHistoryViewSet,
    ReviewViewSet,
    ServiceRequestViewSet,
    NotificationViewSet,
    RecommendationViewSet,
)

# Router ile ViewSet'leri kaydediyoruz
router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='product')
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'users', UserManagementViewSet, basename='user')
router.register(r'groups', GroupViewSet, basename='group')
router.register(r'product-ownerships', ProductOwnershipViewSet, basename='product-ownership')

# Yeni eklenen endpoint'ler
router.register(r'wishlist', WishlistViewSet, basename='wishlist')
router.register(r'view-history', ViewHistoryViewSet, basename='view-history')
router.register(r'reviews', ReviewViewSet, basename='review')
router.register(r'service-requests', ServiceRequestViewSet, basename='service-request')
router.register(r'notifications', NotificationViewSet, basename='notification')
router.register(r'recommendations', RecommendationViewSet, basename='recommendation')

urlpatterns = [
    # Router üzerinden gelen tüm endpointler
    path('', include(router.urls)),
    path("my-products/", my_products_direct),
    path("profile/", profile_view),
    path("notification-settings/", notification_settings_view),
    path("dashboard/summary/", DashboardSummaryView.as_view()),

    # 🔹 GİRİŞ (Login) - Müşteri kısıtlaması bu view içinde yapılıyor
    path('token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),

    # Mobil kayıt veya özel kayıt işlemleri için
    path('register/', UserManagementViewSet.as_view({'post': 'create'}), name='auth_register'),
]