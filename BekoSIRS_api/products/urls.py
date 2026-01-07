# products/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter

# Import from modular views package
from products.views import (
    # Auth
    CustomTokenObtainPairView,
    # Products
    ProductViewSet,
    CategoryViewSet,
    my_products_direct,
    export_products_excel,
    # Users
    UserManagementViewSet,
    GroupViewSet,
    profile_view,
    notification_settings_view,
    # Services
    ServiceRequestViewSet,
    ProductOwnershipViewSet,
    DashboardSummaryView,
    # Customer
    WishlistViewSet,
    ViewHistoryViewSet,
    ReviewViewSet,
    NotificationViewSet,
    RecommendationViewSet,
    # Password
    password_reset_request,
    password_reset_confirm,
    # Biometric
    biometric_enable,
    biometric_disable,
    biometric_status,
    biometric_verify_device,
    # Delivery
    DeliveryViewSet,
    DeliveryRouteViewSet,
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

# Teslimat ve Rota Yönetimi
router.register(r'deliveries', DeliveryViewSet, basename='delivery')
router.register(r'delivery-routes', DeliveryRouteViewSet, basename='delivery-route')

urlpatterns = [
    # Router üzerinden gelen tüm endpointler
    path('', include(router.urls)),
    path("my-products/", my_products_direct, name="my-products"),
    path("profile/", profile_view, name="user-profile"),
    path("notification-settings/", notification_settings_view, name="notification-settings"),
    path("dashboard/summary/", DashboardSummaryView.as_view(), name="dashboard-summary"),

    # 🔹 GİRİŞ (Login) - Müşteri kısıtlaması bu view içinde yapılıyor
    path('token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),

    # Mobil kayıt veya özel kayıt işlemleri için
    path('register/', UserManagementViewSet.as_view({'post': 'create'}), name='auth_register'),
    
    # 🔹 ŞİFRE SIFIRLAMA
    path('password-reset/', password_reset_request, name='password_reset_request'),
    path('password-reset/confirm/', password_reset_confirm, name='password_reset_confirm'),
    
    # 🔹 BİYOMETRİK KİMLİK DOĞRULAMA (Face ID / Face Unlock)
    path('biometric/enable/', biometric_enable, name='biometric_enable'),
    path('biometric/disable/', biometric_disable, name='biometric_disable'),
    path('biometric/status/', biometric_status, name='biometric_status'),
    path('biometric/verify-device/', biometric_verify_device, name='biometric_verify_device'),
    
    # 🔹 EXCEL EXPORT
    path('products/export/excel/', export_products_excel, name='export_products_excel'),
]