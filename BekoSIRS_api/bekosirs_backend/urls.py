import os
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from django.db import connection
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView


def health_check(request):
    """Health check endpoint for monitoring and Docker."""
    try:
        connection.ensure_connection()
        db_ok = True
    except Exception:
        db_ok = False

    status = 200 if db_ok else 503
    return JsonResponse({
        'status': 'healthy' if db_ok else 'unhealthy',
        'database': 'connected' if db_ok else 'disconnected',
        'version': '1.0.0',
    }, status=status)


urlpatterns = [
    # Security: Admin URL changed from predictable '/admin/' to secure path
    path(os.getenv('ADMIN_PATH', 'secure-backend-panel-2026/'), admin.site.urls),

    # API v1 endpoints
    path('api/v1/', include('products.urls')),

    # Health check (no auth required)
    path('api/v1/health/', health_check, name='health-check'),

    # DRF browsable login
    path("api-auth/", include("rest_framework.urls", namespace="rest_framework")),

    # API Documentation (v1)
    path('api/v1/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/v1/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/v1/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

