# products/views.py

from rest_framework import viewsets, status, exceptions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action, api_view, permission_classes
from django.contrib.auth.models import Group
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from django.utils import timezone
from django.db.models import Avg, Count, F

from .models import (
    CustomUser, Product, Category, ProductOwnership,
    Wishlist, WishlistItem, ViewHistory, Review,
    ServiceRequest, ServiceQueue, Notification, Recommendation
)
from .serializers import (
    ProductSerializer,
    CategorySerializer,
    RegisterSerializer,
    UserSerializer,
    ProductOwnershipSerializer,
    ProductOwnershipCreateSerializer,
    WishlistSerializer,
    WishlistItemSerializer,
    ViewHistorySerializer,
    ReviewSerializer,
    ReviewCreateSerializer,
    ServiceRequestSerializer,
    ServiceRequestCreateSerializer,
    ServiceQueueSerializer,
    NotificationSerializer,
    RecommendationSerializer,
)

# ------------------------------------------------------------
# 🔹 GİRİŞ KONTROLÜ (Web vs Mobil Ayrımı)
# ------------------------------------------------------------

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)

        request = self.context.get("request")
        platform = request.data.get("platform", "web") if request else "web"
        role = str(self.user.role).lower()

        # ⛔ Güvenlik duvarı - Platform ve Rol Kontrolü:
        #
        # MOBILE (platform="mobile"):
        #   - customer: ✅ Girebilir
        #   - admin/seller: ❌ Giremez (mobil sadece müşteriler için)
        #
        # WEB (platform="web" veya belirtilmemiş):
        #   - customer: ❌ Giremez (web paneli sadece yönetim için)
        #   - admin/seller: ✅ Girebilir

        if platform == "mobile":
            # Mobil uygulama sadece müşteriler için
            if role in ["admin", "seller"]:
                raise exceptions.PermissionDenied(
                    "Yetkisiz Erişim: Yönetici ve satıcı hesapları mobil uygulamaya giremez."
                )
        else:
            # Web paneli sadece admin ve seller için
            if role == "customer":
                raise exceptions.PermissionDenied(
                    "Yetkisiz Erişim: Müşteri hesapları yönetim paneline giremez."
                )

        data["role"] = self.user.role
        data["username"] = self.user.username
        return data


class CustomTokenObtainPairView(TokenObtainPairView):
    permission_classes = [AllowAny]
    serializer_class = CustomTokenObtainPairSerializer


# ----------------------------------------
# 🔹 ÜRÜN YÖNETİMİ
# ----------------------------------------
class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all().select_related("category")
    serializer_class = ProductSerializer

    def get_permissions(self):
        # Ürün listesi ve detayı herkese açık (giriş yapmadan görülebilir)
        if self.action in ["list", "retrieve"]:
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user

        # Anonim kullanıcılar için (giriş yapmamış)
        if not user.is_authenticated:
            return Product.objects.all().select_related("category")

        # Admin ve Satıcılar her şeyi görür
        if user.role in ["admin", "seller"]:
            return Product.objects.all().select_related("category")

        # Müşteri de tüm ürünleri görebilir
        return Product.objects.all().select_related("category")

    @action(
        detail=False,
        methods=["get"],
        url_path="my-products",
        permission_classes=[IsAuthenticated],
    )
    def my_products(self, request):
        """
        Router üzerinden:
        GET /api/products/my-products/

        - admin/seller: tüm ürünler
        - customer: ProductOwnership üzerinden kendine atanmış ürünler
        """
        user = request.user

        if user.role in ["admin", "seller"]:
            qs = Product.objects.all().select_related("category")
            return Response(ProductSerializer(qs, many=True).data)

        # customer: ownership -> product
        ownerships = (
            ProductOwnership.objects.filter(customer=user)
            .select_related("product", "product__category")
            .order_by("-id")
        )

        result = []
        for o in ownerships:
            p = o.product
            item = ProductSerializer(p).data

            # UI için opsiyonel alanlar (modelinizde varsa doldurur)
            # assigned_date / created_at / assigned_at gibi isim farkı olabilir
            if hasattr(o, "assigned_date"):
                item["assigned_date"] = o.assigned_date
            elif hasattr(o, "assigned_at"):
                item["assigned_date"] = o.assigned_at
            elif hasattr(o, "created_at"):
                item["assigned_date"] = o.created_at

            if hasattr(o, "status"):
                item["status"] = o.status

            result.append(item)

        return Response(result)


# ----------------------------------------
# 🔹 KATEGORİ YÖNETİMİ
# ----------------------------------------
class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    def get_permissions(self):
        # Kategori listesi ve detayı herkese açık
        if self.action in ["list", "retrieve"]:
            return [AllowAny()]
        return [IsAdminUser()]


# ----------------------------------------
# 🔹 KULLANICI YÖNETİMİ
# ----------------------------------------
class UserManagementViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all()

    def get_serializer_class(self):
        if self.action == "create":
            return RegisterSerializer
        return UserSerializer

    def get_permissions(self):
        # Kayıt (create) herkese açık (Mobil app için)
        if self.action == "create":
            return [AllowAny()]
        return [IsAdminUser()]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
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


# ----------------------------------------
# 🔹 ÜRÜN SAHİPLİĞİ / ATAMA YÖNETİMİ
# ----------------------------------------
class ProductOwnershipViewSet(viewsets.ModelViewSet):
    """
    Adminlerin müşterilere ürün ataması (Sahiplik kaydı) yapmasını sağlar.
    Müşteriler kendi ürünlerini görebilir.
    """
    queryset = ProductOwnership.objects.all().select_related("customer", "product", "product__category")

    def get_permissions(self):
        if self.action in ["list", "retrieve", "my_ownerships"]:
            return [IsAuthenticated()]
        return [IsAdminUser()]

    def get_serializer_class(self):
        if self.action == "create":
            return ProductOwnershipCreateSerializer
        return ProductOwnershipSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role in ["admin", "seller"]:
            return ProductOwnership.objects.all().select_related("customer", "product", "product__category")
        return ProductOwnership.objects.filter(customer=user).select_related("product", "product__category")

    @action(detail=False, methods=["get"], url_path="my-ownerships")
    def my_ownerships(self, request):
        """
        GET /api/product-ownerships/my-ownerships/
        Müşterinin sahip olduğu ürünleri garanti bilgileriyle döndürür
        """
        ownerships = ProductOwnership.objects.filter(
            customer=request.user
        ).select_related("product", "product__category")

        data = []
        for ownership in ownerships:
            product = ownership.product
            warranty_end = ownership.warranty_end_date
            is_warranty_active = warranty_end and warranty_end >= timezone.now().date()

            # Aktif servis talepleri
            active_service_requests = ownership.service_requests.exclude(
                status__in=["completed", "cancelled"]
            ).count()

            data.append({
                "id": ownership.id,
                "product": {
                    "id": product.id,
                    "name": product.name,
                    "brand": product.brand,
                    "price": str(product.price),
                    "image": product.image.url if product.image else None,
                    "category_name": product.category.name if product.category else None,
                    "warranty_duration_months": product.warranty_duration_months,
                },
                "purchase_date": ownership.purchase_date,
                "serial_number": ownership.serial_number,
                "warranty_end_date": warranty_end,
                "is_warranty_active": is_warranty_active,
                "days_until_warranty_expires": (warranty_end - timezone.now().date()).days if warranty_end and is_warranty_active else None,
                "active_service_requests": active_service_requests,
            })

        return Response(data)


# ----------------------------------------
# 🔹 GRUP & İZİN YÖNETİMİ
# ----------------------------------------
class GroupViewSet(viewsets.ModelViewSet):
    queryset = Group.objects.all()
    permission_classes = [IsAdminUser]

    def list(self, request):
        groups = Group.objects.all().values("id", "name")
        return Response(groups)


# ------------------------------------------------------------
# 🔹 Bildirim Ayarları
# ------------------------------------------------------------
@api_view(["GET", "PUT", "PATCH"])
@permission_classes([IsAuthenticated])
def notification_settings_view(request):
    """
    GET /api/notification-settings/ - Bildirim tercihlerini getir
    PUT/PATCH /api/notification-settings/ - Bildirim tercihlerini güncelle
    """
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

    # PUT veya PATCH
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


# ------------------------------------------------------------
# 🔹 Profil Görüntüleme ve Güncelleme
# ------------------------------------------------------------
@api_view(["GET", "PUT", "PATCH"])
@permission_classes([IsAuthenticated])
def profile_view(request):
    """
    GET /api/profile/ - Kullanıcı profil bilgilerini getir
    PUT/PATCH /api/profile/ - Kullanıcı profil bilgilerini güncelle
    """
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
        })

    # PUT veya PATCH
    data = request.data

    # Güncellenebilir alanlar
    if "first_name" in data:
        user.first_name = data["first_name"]
    if "last_name" in data:
        user.last_name = data["last_name"]
    if "email" in data:
        user.email = data["email"]
    if "phone_number" in data:
        user.phone_number = data["phone_number"]

    # Şifre değişikliği
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
        }
    })


# ------------------------------------------------------------
# 🔹 (Opsiyonel) Mobil uyumluluk için direkt endpoint:
#     GET /api/my-products/
# ------------------------------------------------------------
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_products_direct(request):
    """
    GET /api/my-products/

    Mobil kodunuz şu an bunu çağırdığı için ekledik.
    İsterseniz daha sonra frontend'i /api/products/my-products/ yapıp bunu kaldırabilirsiniz.
    """
    user = request.user

    if user.role in ["admin", "seller"]:
        qs = Product.objects.all().select_related("category")
        return Response(ProductSerializer(qs, many=True).data)

    ownerships = (
        ProductOwnership.objects.filter(customer=user)
        .select_related("product", "product__category")
        .order_by("-id")
    )

    result = []
    for o in ownerships:
        p = o.product
        item = ProductSerializer(p).data

        if hasattr(o, "assigned_date"):
            item["assigned_date"] = o.assigned_date
        elif hasattr(o, "assigned_at"):
            item["assigned_date"] = o.assigned_at
        elif hasattr(o, "created_at"):
            item["assigned_date"] = o.created_at

        if hasattr(o, "status"):
            item["status"] = o.status

        result.append(item)

    return Response(result)


# ----------------------------------------
# 🔹 WISHLIST (İSTEK LİSTESİ) YÖNETİMİ
# ----------------------------------------
class WishlistViewSet(viewsets.ModelViewSet):
    """
    Müşteri istek listesi yönetimi.
    GET /api/wishlist/ - Kullanıcının istek listesini döner
    POST /api/wishlist/add_item/ - Listeye ürün ekler
    DELETE /api/wishlist/remove_item/ - Listeden ürün çıkarır
    """
    serializer_class = WishlistSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Wishlist.objects.filter(customer=self.request.user).prefetch_related('items__product')

    def list(self, request):
        # Kullanıcının wishlist'i yoksa oluştur
        wishlist, created = Wishlist.objects.get_or_create(customer=request.user)
        serializer = WishlistSerializer(wishlist)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='add-item')
    def add_item(self, request):
        """POST /api/wishlist/add-item/ - Ürün ekle"""
        wishlist, _ = Wishlist.objects.get_or_create(customer=request.user)
        product_id = request.data.get('product_id')

        if not product_id:
            return Response({'error': 'product_id gerekli'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response({'error': 'Ürün bulunamadı'}, status=status.HTTP_404_NOT_FOUND)

        # Zaten ekliyse hata dön
        if WishlistItem.objects.filter(wishlist=wishlist, product=product).exists():
            return Response({'error': 'Bu ürün zaten istek listenizde'}, status=status.HTTP_400_BAD_REQUEST)

        item = WishlistItem.objects.create(
            wishlist=wishlist,
            product=product,
            note=request.data.get('note', ''),
            notify_on_price_drop=request.data.get('notify_on_price_drop', True),
            notify_on_restock=request.data.get('notify_on_restock', True)
        )
        return Response(WishlistItemSerializer(item).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['delete'], url_path='remove-item/(?P<product_id>[^/.]+)')
    def remove_item(self, request, product_id=None):
        """DELETE /api/wishlist/remove-item/{product_id}/ - Ürün çıkar"""
        try:
            wishlist = Wishlist.objects.get(customer=request.user)
            item = WishlistItem.objects.get(wishlist=wishlist, product_id=product_id)
            item.delete()
            return Response({'success': 'Ürün istek listesinden çıkarıldı'})
        except (Wishlist.DoesNotExist, WishlistItem.DoesNotExist):
            return Response({'error': 'Ürün istek listenizde bulunamadı'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['get'], url_path='check/(?P<product_id>[^/.]+)')
    def check_item(self, request, product_id=None):
        """GET /api/wishlist/check/{product_id}/ - Ürün listede mi kontrol et"""
        try:
            wishlist = Wishlist.objects.get(customer=request.user)
            exists = WishlistItem.objects.filter(wishlist=wishlist, product_id=product_id).exists()
            return Response({'in_wishlist': exists})
        except Wishlist.DoesNotExist:
            return Response({'in_wishlist': False})


# ----------------------------------------
# 🔹 VIEW HISTORY (GÖRÜNTÜLEME GEÇMİŞİ)
# ----------------------------------------
class ViewHistoryViewSet(viewsets.ModelViewSet):
    """
    Kullanıcı ürün görüntüleme geçmişi.
    GET /api/view-history/ - Görüntüleme geçmişi
    POST /api/view-history/record/ - Görüntüleme kaydet
    """
    serializer_class = ViewHistorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ViewHistory.objects.filter(customer=self.request.user).select_related('product')

    @action(detail=False, methods=['post'], url_path='record')
    def record_view(self, request):
        """POST /api/view-history/record/ - Ürün görüntüleme kaydet"""
        product_id = request.data.get('product_id')

        if not product_id:
            return Response({'error': 'product_id gerekli'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response({'error': 'Ürün bulunamadı'}, status=status.HTTP_404_NOT_FOUND)

        # Varsa güncelle, yoksa oluştur
        view_history, created = ViewHistory.objects.get_or_create(
            customer=request.user,
            product=product,
            defaults={'view_count': 1}
        )

        if not created:
            view_history.view_count = F('view_count') + 1
            view_history.viewed_at = timezone.now()
            view_history.save()
            view_history.refresh_from_db()

        return Response(ViewHistorySerializer(view_history).data)

    @action(detail=False, methods=['delete'], url_path='clear')
    def clear_history(self, request):
        """DELETE /api/view-history/clear/ - Geçmişi temizle"""
        ViewHistory.objects.filter(customer=request.user).delete()
        return Response({'success': 'Görüntüleme geçmişi temizlendi'})


# ----------------------------------------
# 🔹 REVIEW (ÜRÜN DEĞERLENDİRME)
# ----------------------------------------
class ReviewViewSet(viewsets.ModelViewSet):
    """
    Ürün değerlendirmeleri.
    GET /api/reviews/ - Tüm değerlendirmeler (admin)
    GET /api/reviews/product/{id}/ - Ürüne ait değerlendirmeler
    POST /api/reviews/ - Değerlendirme ekle
    """
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return ReviewCreateSerializer
        return ReviewSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role in ['admin', 'seller']:
            return Review.objects.all().select_related('customer', 'product')
        return Review.objects.filter(customer=user).select_related('product')

    def perform_create(self, serializer):
        serializer.save(customer=self.request.user)

    @action(detail=False, methods=['get'], url_path='product/(?P<product_id>[^/.]+)')
    def product_reviews(self, request, product_id=None):
        """GET /api/reviews/product/{id}/ - Ürünün onaylanmış değerlendirmeleri"""
        reviews = Review.objects.filter(
            product_id=product_id,
            is_approved=True
        ).select_related('customer')

        # Ortalama puan hesapla
        avg_rating = reviews.aggregate(avg=Avg('rating'))['avg'] or 0

        return Response({
            'reviews': ReviewSerializer(reviews, many=True).data,
            'average_rating': round(avg_rating, 1),
            'total_reviews': reviews.count()
        })

    @action(detail=True, methods=['post'], url_path='approve')
    def approve_review(self, request, pk=None):
        """POST /api/reviews/{id}/approve/ - Değerlendirmeyi onayla (Admin)"""
        if request.user.role != 'admin':
            return Response({'error': 'Yetkiniz yok'}, status=status.HTTP_403_FORBIDDEN)

        review = self.get_object()
        review.is_approved = True
        review.save()
        return Response({'success': 'Değerlendirme onaylandı'})


# ----------------------------------------
# 🔹 SERVICE REQUEST (SERVİS TALEBİ)
# ----------------------------------------
class ServiceRequestViewSet(viewsets.ModelViewSet):
    """
    Servis talepleri yönetimi.
    GET /api/service-requests/ - Talepleri listele
    POST /api/service-requests/ - Yeni talep oluştur
    """
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return ServiceRequestCreateSerializer
        return ServiceRequestSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role in ['admin', 'seller']:
            return ServiceRequest.objects.all().select_related(
                'customer', 'product_ownership__product', 'assigned_to'
            ).prefetch_related('queue_entry')
        return ServiceRequest.objects.filter(customer=user).select_related(
            'product_ownership__product'
        ).prefetch_related('queue_entry')

    def perform_create(self, serializer):
        service_request = serializer.save(customer=self.request.user)

        # Kuyruğa ekle
        last_queue = ServiceQueue.objects.order_by('-queue_number').first()
        queue_number = (last_queue.queue_number + 1) if last_queue else 1

        ServiceQueue.objects.create(
            service_request=service_request,
            queue_number=queue_number,
            estimated_wait_time=queue_number * 30  # Tahmini 30 dk/talep
        )

        service_request.status = 'in_queue'
        service_request.save()

        # Bildirim oluştur
        Notification.objects.create(
            user=self.request.user,
            notification_type='service_update',
            title='Servis Talebiniz Alındı',
            message=f'Talep numaranız: SR-{service_request.id}. Sıra numaranız: {queue_number}',
            related_service_request=service_request
        )

    @action(detail=True, methods=['post'], url_path='assign')
    def assign_request(self, request, pk=None):
        """POST /api/service-requests/{id}/assign/ - Talep ata (Admin)"""
        if request.user.role not in ['admin', 'seller']:
            return Response({'error': 'Yetkiniz yok'}, status=status.HTTP_403_FORBIDDEN)

        service_request = self.get_object()
        assigned_to_id = request.data.get('assigned_to')

        if assigned_to_id:
            try:
                assigned_user = CustomUser.objects.get(id=assigned_to_id)
                service_request.assigned_to = assigned_user
            except CustomUser.DoesNotExist:
                return Response({'error': 'Kullanıcı bulunamadı'}, status=status.HTTP_404_NOT_FOUND)

        service_request.status = 'in_progress'
        service_request.save()

        # Müşteriye bildirim
        Notification.objects.create(
            user=service_request.customer,
            notification_type='service_update',
            title='Talebiniz İşleme Alındı',
            message=f'SR-{service_request.id} numaralı talebiniz işleme alındı.',
            related_service_request=service_request
        )

        return Response({'success': 'Talep atandı'})

    @action(detail=True, methods=['post'], url_path='complete')
    def complete_request(self, request, pk=None):
        """POST /api/service-requests/{id}/complete/ - Talebi tamamla"""
        if request.user.role not in ['admin', 'seller']:
            return Response({'error': 'Yetkiniz yok'}, status=status.HTTP_403_FORBIDDEN)

        service_request = self.get_object()
        service_request.status = 'completed'
        service_request.resolution_notes = request.data.get('resolution_notes', '')
        service_request.resolved_at = timezone.now()
        service_request.save()

        # Kuyruktan çıkar
        if hasattr(service_request, 'queue_entry'):
            service_request.queue_entry.delete()

        # Müşteriye bildirim
        Notification.objects.create(
            user=service_request.customer,
            notification_type='service_update',
            title='Talebiniz Tamamlandı',
            message=f'SR-{service_request.id} numaralı talebiniz tamamlandı.',
            related_service_request=service_request
        )

        return Response({'success': 'Talep tamamlandı'})

    @action(detail=False, methods=['get'], url_path='queue-status')
    def queue_status(self, request):
        """GET /api/service-requests/queue-status/ - Kuyruk durumu"""
        queue = ServiceQueue.objects.all().select_related(
            'service_request__customer', 'service_request__product_ownership__product'
        )

        result = []
        for entry in queue:
            result.append({
                'queue_number': entry.queue_number,
                'priority': entry.priority,
                'estimated_wait_time': entry.estimated_wait_time,
                'service_request': ServiceRequestSerializer(entry.service_request).data
            })

        return Response(result)


# ----------------------------------------
# 🔹 NOTIFICATION (BİLDİRİM)
# ----------------------------------------
class NotificationViewSet(viewsets.ModelViewSet):
    """
    Kullanıcı bildirimleri.
    GET /api/notifications/ - Bildirimleri listele
    POST /api/notifications/{id}/read/ - Okundu işaretle
    """
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    @action(detail=True, methods=['post'], url_path='read')
    def mark_read(self, request, pk=None):
        """POST /api/notifications/{id}/read/ - Okundu işaretle"""
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response({'success': 'Bildirim okundu olarak işaretlendi'})

    @action(detail=False, methods=['post'], url_path='read-all')
    def mark_all_read(self, request):
        """POST /api/notifications/read-all/ - Tümünü okundu işaretle"""
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({'success': 'Tüm bildirimler okundu olarak işaretlendi'})

    @action(detail=False, methods=['get'], url_path='unread-count')
    def unread_count(self, request):
        """GET /api/notifications/unread-count/ - Okunmamış sayısı"""
        count = Notification.objects.filter(user=request.user, is_read=False).count()
        return Response({'unread_count': count})


# ----------------------------------------
# 🔹 DASHBOARD SUMMARY (ÖZET)
# ----------------------------------------
class DashboardSummaryView(APIView):
    permission_classes = [IsAdminUser]  # Sadece admin/satıcı görebilir

    def get(self, request):
        # 1. KPI Verileri
        total_products = Product.objects.count()
        out_of_stock = Product.objects.filter(stock=0).count()
        low_stock = Product.objects.filter(stock__gt=0, stock__lt=10).count()
        # total_value = Product.objects.aggregate(
        #     total=Sum(F('price') * F('stock'))
        # )['total'] or 0

        # 2. Bekleyen Teslimatlar (ServiceRequest örnek alınarak)
        # Şimdilik servis taleplerini 'aktif işler' olarak sayalım
        pending_requests = ServiceRequest.objects.filter(status__in=['pending', 'in_progress', 'in_queue']).count()

        # 3. Son Aktiviteler / Ürünler
        # Product modelinde created_at yoksa id'ye göre sırala
        recent_products = Product.objects.order_by('-id')[:5]
        
        # 4. Basit Grafik Verisi (Son 5 ürünün stoğu gibi - örnek)
        # Gerçekte sipariş/satış tablosu olmadığı için ürün stok dağılımını verelim
        chart_data = [
            {"name": "Stokta", "value": total_products - out_of_stock},
            {"name": "Tükendi", "value": out_of_stock},
        ]

        return Response({
            "kpis": {
                "total_products": total_products,
                "out_of_stock": out_of_stock,
                "low_stock": low_stock,
                "pending_requests": pending_requests
            },
            "recent_products": ProductSerializer(recent_products, many=True).data,
            "chart_data": chart_data
        })


# ----------------------------------------
# 🔹 RECOMMENDATION (ÖNERİ SİSTEMİ)
# ----------------------------------------
class RecommendationViewSet(viewsets.ModelViewSet):
    """
    Ürün önerileri.
    GET /api/recommendations/ - Kullanıcıya özel öneriler
    POST /api/recommendations/generate/ - Öneri oluştur
    """
    serializer_class = RecommendationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Recommendation.objects.filter(customer=self.request.user).select_related('product')

    @action(detail=False, methods=['post'], url_path='generate')
    def generate_recommendations(self, request):
        """
        POST /api/recommendations/generate/
        Kullanıcının görüntüleme geçmişine göre öneri oluştur
        """
        user = request.user

        # Mevcut önerileri temizle
        Recommendation.objects.filter(customer=user).delete()

        # Görüntüleme geçmişinden kategorileri al
        view_history = ViewHistory.objects.filter(customer=user).select_related('product__category')
        viewed_product_ids = view_history.values_list('product_id', flat=True)

        # En çok görüntülenen kategorileri bul
        category_counts = {}
        for vh in view_history:
            if vh.product.category:
                cat_id = vh.product.category.id
                category_counts[cat_id] = category_counts.get(cat_id, 0) + vh.view_count

        # Kategori bazında öneri oluştur
        recommendations_created = []

        for category_id, view_count in sorted(category_counts.items(), key=lambda x: -x[1])[:3]:
            # Bu kategoriden görüntülenmemiş ürünleri al
            products = Product.objects.filter(
                category_id=category_id,
                stock__gt=0
            ).exclude(
                id__in=viewed_product_ids
            ).order_by('-id')[:5]

            for i, product in enumerate(products):
                score = min(1.0, view_count / 10) * (1 - i * 0.1)
                rec, created = Recommendation.objects.get_or_create(
                    customer=user,
                    product=product,
                    defaults={
                        'score': score,
                        'reason': f'İlgilendiğiniz {product.category.name} kategorisinden'
                    }
                )
                if created:
                    recommendations_created.append(rec)

        # Wishlist'teki ürünlerin kategorilerinden de öneri ekle
        try:
            wishlist = Wishlist.objects.get(customer=user)
            for item in wishlist.items.select_related('product__category').all():
                if item.product.category:
                    related_products = Product.objects.filter(
                        category=item.product.category,
                        stock__gt=0
                    ).exclude(
                        id__in=viewed_product_ids
                    ).exclude(
                        id=item.product.id
                    )[:3]

                    for product in related_products:
                        rec, created = Recommendation.objects.get_or_create(
                            customer=user,
                            product=product,
                            defaults={
                                'score': 0.7,
                                'reason': f'İstek listenizdeki {item.product.name} ile benzer'
                            }
                        )
                        if created:
                            recommendations_created.append(rec)
        except Wishlist.DoesNotExist:
            pass

        return Response({
            'success': True,
            'recommendations_count': len(recommendations_created),
            'recommendations': RecommendationSerializer(recommendations_created, many=True).data
        })

    @action(detail=True, methods=['post'], url_path='click')
    def record_click(self, request, pk=None):
        """POST /api/recommendations/{id}/click/ - Öneri tıklaması kaydet"""
        recommendation = self.get_object()
        recommendation.clicked = True
        recommendation.is_shown = True
        recommendation.save()
        return Response({'success': 'Tıklama kaydedildi'})
