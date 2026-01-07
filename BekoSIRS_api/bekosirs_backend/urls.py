import os
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

urlpatterns = [
    # Security: Admin URL changed from predictable '/admin/' to secure path
    # Set via environment variable for additional security
    path(os.getenv('ADMIN_PATH', 'secure-backend-panel-2026/'), admin.site.urls),

    # API v1 endpoints - versioned for future compatibility
    path('api/v1/', include('products.urls')),

    # DRF browsable login
    path("api-auth/", include("rest_framework.urls", namespace="rest_framework")),

    # API Documentation (v1)
    path('api/v1/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/v1/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/v1/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

