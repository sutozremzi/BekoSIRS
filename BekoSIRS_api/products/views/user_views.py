# products/views/user_views.py
"""
User management views: users, groups, profile, notification settings.
"""

from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from django.contrib.auth.models import Group

from products.models import CustomUser
from products.serializers import RegisterSerializer, UserSerializer


class UserManagementViewSet(viewsets.ModelViewSet):
    """User CRUD with role management."""
    queryset = CustomUser.objects.all()

    def get_serializer_class(self):
        if self.action == "create":
            return RegisterSerializer
        return UserSerializer

    def get_permissions(self):
        if self.action == "create":
            return [AllowAny()]
        return [IsAdminUser()]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        try:
            from products.email_service import EmailService
            EmailService.send_welcome_email(user)
        except Exception as e:
            print(f"Failed to send welcome email: {e}")
        
        return Response(
            {
                "success": True,
                "message": f"{user.username} başarıyla oluşturuldu.",
                "user_id": user.id,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def set_role(self, request, pk=None):
        user = self.get_object()
        role = request.data.get("role")
        if role not in ["admin", "seller", "customer"]:
            return Response({"error": "Geçersiz rol"}, status=status.HTTP_400_BAD_REQUEST)
        user.role = role
        user.save()
        return Response({"success": f"Rol {role} olarak güncellendi."})


class GroupViewSet(viewsets.ModelViewSet):
    """Group management for permissions."""
    queryset = Group.objects.all()
    permission_classes = [IsAdminUser]

    def list(self, request):
        groups = Group.objects.all().values("id", "name")
        return Response(groups)


@api_view(["GET", "PUT", "PATCH"])
@permission_classes([IsAuthenticated])
def profile_view(request):
    """GET/PUT/PATCH /api/profile/ - User profile management."""
    user = request.user

    if request.method == "GET":
        return Response({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "phone_number": getattr(user, 'phone_number', ''),
            "role": user.role,
            "date_joined": user.date_joined,
            # Adres Bilgileri
            "address": user.address,
            "address_city": user.address_city,
            "address_lat": user.address_lat,
            "address_lng": user.address_lng,
        })

    data = request.data
    if "first_name" in data:
        user.first_name = data["first_name"]
    if "last_name" in data:
        user.last_name = data["last_name"]
    if "email" in data:
        user.email = data["email"]
    if "phone_number" in data:
        user.phone_number = data["phone_number"]
    
    # Adres güncelleme
    if "address" in data:
        user.address = data["address"]
    if "address_city" in data:
        user.address_city = data["address_city"]
    # Koordinatlar genelde mobilden gelmez ama admin güncellerse diye açık bırakalım
    if "address_lat" in data:
        user.address_lat = data["address_lat"]
    if "address_lng" in data:
        user.address_lng = data["address_lng"]

    if "new_password" in data and data["new_password"]:
        current_password = data.get("current_password", "")
        if not user.check_password(current_password):
            return Response(
                {"error": "Mevcut şifre yanlış"},
                status=status.HTTP_400_BAD_REQUEST
            )
        user.set_password(data["new_password"])

    user.save()

    return Response({
        "success": True,
        "message": "Profil başarıyla güncellendi",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "phone_number": getattr(user, 'phone_number', ''),
            "role": user.role,
            "address": user.address,
            "address_city": user.address_city,
        }
    })


@api_view(["GET", "PUT", "PATCH"])
@permission_classes([IsAuthenticated])
def notification_settings_view(request):
    """GET/PUT/PATCH /api/notification-settings/ - Notification preferences."""
    user = request.user

    if request.method == "GET":
        return Response({
            "notify_service_updates": user.notify_service_updates,
            "notify_price_drops": user.notify_price_drops,
            "notify_restock": user.notify_restock,
            "notify_recommendations": user.notify_recommendations,
            "notify_warranty_expiry": user.notify_warranty_expiry,
            "notify_general": user.notify_general,
        })

    data = request.data
    if "notify_service_updates" in data:
        user.notify_service_updates = data["notify_service_updates"]
    if "notify_price_drops" in data:
        user.notify_price_drops = data["notify_price_drops"]
    if "notify_restock" in data:
        user.notify_restock = data["notify_restock"]
    if "notify_recommendations" in data:
        user.notify_recommendations = data["notify_recommendations"]
    if "notify_warranty_expiry" in data:
        user.notify_warranty_expiry = data["notify_warranty_expiry"]
    if "notify_general" in data:
        user.notify_general = data["notify_general"]

    user.save()

    return Response({
        "success": True,
        "message": "Bildirim ayarları güncellendi",
        "settings": {
            "notify_service_updates": user.notify_service_updates,
            "notify_price_drops": user.notify_price_drops,
            "notify_restock": user.notify_restock,
            "notify_recommendations": user.notify_recommendations,
            "notify_warranty_expiry": user.notify_warranty_expiry,
            "notify_general": user.notify_general,
        }
    })
