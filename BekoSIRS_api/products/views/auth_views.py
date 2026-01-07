# products/views/auth_views.py
"""
Authentication views: login, token management.
"""

from rest_framework import exceptions
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom token serializer with platform and role validation.
    
    Security rules:
    - MOBILE: Only customers can login
    - WEB: Only admin/seller can login
    """
    def validate(self, attrs):
        data = super().validate(attrs)

        request = self.context.get("request")
        platform = request.data.get("platform", "web") if request else "web"
        role = str(self.user.role).lower()

        if platform == "mobile":
            # Mobile app is customer-only
            if role in ["admin", "seller"]:
                raise exceptions.PermissionDenied(
                    "Yetkisiz Erişim: Yönetici ve satıcı hesapları mobil uygulamaya giremez."
                )
        else:
            # Web panel is admin/seller only
            if role == "customer":
                raise exceptions.PermissionDenied(
                    "Yetkisiz Erişim: Müşteri hesapları yönetim paneline giremez."
                )

        data["role"] = self.user.role
        data["username"] = self.user.username
        return data


class CustomTokenObtainPairView(TokenObtainPairView):
    """Custom JWT token view with platform restrictions."""
    permission_classes = [AllowAny]
    serializer_class = CustomTokenObtainPairSerializer
