from rest_framework import serializers, validators
from django.contrib.auth.models import Group, Permission
from .models import (
    Category, Product, ProductOwnership, CustomUser,
    Wishlist, WishlistItem, ViewHistory, Review,
    ServiceRequest, ServiceQueue, Notification, Recommendation
)

# ---------------------------
# Category Serializer
# ---------------------------
class CategorySerializer(serializers.ModelSerializer):
    product_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Category
        fields = ['id', 'name', 'parent', 'product_count']


# ---------------------------
# Product Serializer (Stok ve Kategori İsmi Dahil)
# ---------------------------
class ProductSerializer(serializers.ModelSerializer):
    # Kategori detaylarını obje olarak döner (read_only)
    category = CategorySerializer(read_only=True)
    # Kategori ismini düz metin olarak da döner (Frontend kolaylığı için)
    category_name = serializers.SerializerMethodField()

    def get_category_name(self, obj):
        return obj.category.name if obj.category else None
    
    class Meta:
        model = Product
        # 'stock', 'category_name' ve 'image' alanlarının burada olduğundan emin olun
        fields = [
            "id", 
            "name", 
            "brand", 
            "description", 
            "price", 
            "stock", 
            "category", 
            "category_name", 
            "image",
            "model_code",
            "warranty_code",
            "price_list",
            "price_cash",
            "campaign_tag"
        ]


# ---------------------------
# User Serializers (Kullanıcı Listeleme ve Arama)
# ---------------------------
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ["id", "username", "email", "first_name", "last_name", "role", "is_active", "phone_number", "biometric_enabled"]


class UserSearchSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'role', 'phone_number']


# ---------------------------
# Product Ownership (Ürün Sahipliği)
# ---------------------------
class ProductOwnershipSerializer(serializers.ModelSerializer):
    # Ürün detaylarını tam göstermek için ProductSerializer'ı içe gömüyoruz
    product = ProductSerializer(read_only=True)
    warranty_end_date = serializers.DateField(read_only=True)

    class Meta:
        model = ProductOwnership
        fields = ['id', 'product', 'purchase_date', 'serial_number', 'warranty_end_date']


class ProductOwnershipCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductOwnership
        fields = ['customer', 'product', 'purchase_date', 'serial_number']


# ---------------------------
# Group & Permission Serializers (Rol Yönetimi)
# ---------------------------
class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ["id", "name"]

class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ["id", "name", "codename"]


# ------------------------------------------------------------
# 🔹 Register Serializer (Tam Düzeltilmiş Versiyon)
# ------------------------------------------------------------
class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ("username", "password", "email", "first_name", "last_name", "role", "phone_number")
        extra_kwargs = {
            "password": {"write_only": True},
            "email": {
                "required": True,
                "allow_blank": False,
                "validators": [
                    validators.UniqueValidator(
                        CustomUser.objects.all(), 
                        "Bu e-posta adresi ile bir kullanıcı zaten mevcut."
                    )
                ],
            },
            # Telefon numarasının boş geçilebilmesi için ayarlar:
            "phone_number": {"required": False, "allow_null": True, "allow_blank": True}
        }

    def create(self, validated_data):
        # ❗ SQL Server Unique Constraint Hatası Çözümü:
        # Eğer telefon numarası boş string ("") gelirse, onu veritabanına None (NULL) olarak kaydet.
        # Böylece birden fazla kişi telefon numarasını boş bırakabilir.
        phone = validated_data.get("phone_number")
        if phone == "" or phone is None:
            phone = None 

        # create_user metodu şifreyi otomatik olarak hashler (pbkdf2_sha256)
        user = CustomUser.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
            # Eğer rol gönderilmezse varsayılan olarak 'customer' ata
            role=validated_data.get("role", "customer"),
            phone_number=phone
        )
        return user


# ---------------------------
# Wishlist Serializers (İstek Listesi)
# ---------------------------
class WishlistItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(), source='product', write_only=True
    )

    class Meta:
        model = WishlistItem
        fields = ['id', 'product', 'product_id', 'added_at', 'note',
                  'notify_on_price_drop', 'notify_on_restock']
        read_only_fields = ['id', 'added_at']


class WishlistSerializer(serializers.ModelSerializer):
    items = WishlistItemSerializer(many=True, read_only=True)
    item_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Wishlist
        fields = ['id', 'customer', 'items', 'item_count', 'created_at', 'updated_at']
        read_only_fields = ['id', 'customer', 'created_at', 'updated_at']


# ---------------------------
# ViewHistory Serializer (Görüntüleme Geçmişi)
# ---------------------------
class ViewHistorySerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(), source='product', write_only=True
    )

    class Meta:
        model = ViewHistory
        fields = ['id', 'product', 'product_id', 'viewed_at', 'view_count']
        read_only_fields = ['id', 'viewed_at', 'view_count']


# ---------------------------
# Review Serializers (Ürün Değerlendirmesi)
# ---------------------------
class ReviewSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.username', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = Review
        fields = ['id', 'customer', 'customer_name', 'product', 'product_name',
                  'rating', 'comment', 'created_at', 'updated_at', 'is_approved']
        read_only_fields = ['id', 'customer', 'created_at', 'updated_at']


class ReviewCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ['product', 'rating', 'comment']

    def validate_rating(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError("Puan 1-5 arasında olmalıdır.")
        return value


# ---------------------------
# ServiceRequest Serializers (Servis Talebi)
# ---------------------------
class ServiceQueueSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceQueue
        fields = ['id', 'queue_number', 'priority', 'estimated_wait_time', 'entered_queue_at']
        read_only_fields = ['id', 'entered_queue_at']


class ServiceRequestSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.username', read_only=True)
    product_name = serializers.CharField(source='product_ownership.product.name', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.username', read_only=True)
    queue_entry = ServiceQueueSerializer(read_only=True)
    product_ownership_detail = ProductOwnershipSerializer(source='product_ownership', read_only=True)

    class Meta:
        model = ServiceRequest
        fields = ['id', 'customer', 'customer_name', 'product_ownership', 'product_ownership_detail',
                  'product_name', 'request_type', 'status', 'description', 'created_at', 'updated_at',
                  'assigned_to', 'assigned_to_name', 'resolution_notes', 'resolved_at', 'queue_entry']
        read_only_fields = ['id', 'customer', 'created_at', 'updated_at', 'resolved_at']


class ServiceRequestCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceRequest
        fields = ['product_ownership', 'request_type', 'description']


# ---------------------------
# Notification Serializer (Bildirim)
# ---------------------------
class NotificationSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='related_product.name', read_only=True)

    class Meta:
        model = Notification
        fields = ['id', 'notification_type', 'title', 'message', 'is_read',
                  'created_at', 'related_product', 'product_name', 'related_service_request']
        read_only_fields = ['id', 'created_at']


# ---------------------------
# Recommendation Serializer (Öneri)
# ---------------------------
class RecommendationSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)

    class Meta:
        model = Recommendation
        fields = ['id', 'product', 'score', 'reason', 'created_at', 'is_shown', 'clicked']
        read_only_fields = ['id', 'created_at']


# ---------------------------
# Password Reset Serializers
# ---------------------------
class PasswordResetRequestSerializer(serializers.Serializer):
    """Serializer for requesting a password reset email."""
    email = serializers.EmailField()

    def validate_email(self, value):
        """Check if user with this email exists."""
        if not CustomUser.objects.filter(email=value).exists():
            # Don't reveal if email exists or not for security
            pass  # Still return success to prevent email enumeration
        return value


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Serializer for confirming password reset with token."""
    token = serializers.CharField()
    new_password = serializers.CharField(min_length=8, write_only=True)
    confirm_password = serializers.CharField(min_length=8, write_only=True)

    def validate(self, attrs):
        """Validate that passwords match and token is valid."""
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({
                'confirm_password': 'Şifreler eşleşmiyor.'
            })
        
        from .models import PasswordResetToken
        try:
            token_obj = PasswordResetToken.objects.get(token=attrs['token'])
            if not token_obj.is_valid():
                raise serializers.ValidationError({
                    'token': 'Bu şifre sıfırlama bağlantısı geçersiz veya süresi dolmuş.'
                })
            attrs['token_obj'] = token_obj
        except PasswordResetToken.DoesNotExist:
            raise serializers.ValidationError({
                'token': 'Geçersiz şifre sıfırlama bağlantısı.'
            })
        
        return attrs

    def save(self):
        """Reset the user's password."""
        token_obj = self.validated_data['token_obj']
        user = token_obj.user
        user.set_password(self.validated_data['new_password'])
        user.save()
        token_obj.use()
        return user


# ---------------------------
# Biometric Authentication Serializers
# ---------------------------
class BiometricEnableSerializer(serializers.Serializer):
    """Serializer for enabling biometric authentication."""
    device_id = serializers.CharField(max_length=255)
    refresh_token = serializers.CharField(write_only=True)


class BiometricLoginSerializer(serializers.Serializer):
    """Serializer for biometric login."""
    device_id = serializers.CharField(max_length=255)
    user_id = serializers.IntegerField()