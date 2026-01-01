# products/views.py

from rest_framework import viewsets, status, exceptions
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
# 🔹 IMPORT THE NEW ML CLASS
# ------------------------------------------------------------
from .ml_recommender import HybridRecommender

# ------------------------------------------------------------
# 🔹 GİRİŞ KONTROLÜ
# ------------------------------------------------------------

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        request = self.context.get("request")
        platform = request.data.get("platform", "web") if request else "web"
        role = str(self.user.role).lower()

        if platform == "mobile":
            if role in ["admin", "seller"]:
                raise exceptions.PermissionDenied("Yetkisiz Erişim: Yönetici ve satıcı hesapları mobil uygulamaya giremez.")
        else:
            if role == "customer":
                raise exceptions.PermissionDenied("Yetkisiz Erişim: Müşteri hesapları yönetim paneline giremez.")

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
        if self.action in ["list", "retrieve"]:
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Product.objects.all().select_related("category")
        return Product.objects.all().select_related("category")

    @action(detail=False, methods=["get"], url_path="my-products", permission_classes=[IsAuthenticated])
    def my_products(self, request):
        user = request.user
        if user.role in ["admin", "seller"]:
            qs = Product.objects.all().select_related("category")
            return Response(ProductSerializer(qs, many=True).data)

        ownerships = ProductOwnership.objects.filter(customer=user).select_related("product", "product__category").order_by("-id")
        result = []
        for o in ownerships:
            p = o.product
            item = ProductSerializer(p).data
            if hasattr(o, "assigned_date"): item["assigned_date"] = o.assigned_date
            elif hasattr(o, "assigned_at"): item["assigned_date"] = o.assigned_at
            elif hasattr(o, "created_at"): item["assigned_date"] = o.created_at
            if hasattr(o, "status"): item["status"] = o.status
            result.append(item)
        return Response(result)


# ----------------------------------------
# 🔹 KATEGORİ YÖNETİMİ
# ----------------------------------------
class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    def get_permissions(self):
        if self.action in ["list", "retrieve"]: return [AllowAny()]
        return [IsAdminUser()]


# ----------------------------------------
# 🔹 KULLANICI YÖNETİMİ
# ----------------------------------------
class UserManagementViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all()
    def get_serializer_class(self):
        return RegisterSerializer if self.action == "create" else UserSerializer
    def get_permissions(self):
        return [AllowAny()] if self.action == "create" else [IsAdminUser()]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response({"success": True, "message": f"{user.username} başarıyla oluşturuldu.", "user_id": user.id}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def set_role(self, request, pk=None):
        user = self.get_object()
        role = request.data.get("role")
        if role not in ["admin", "seller", "customer"]: return Response({"error": "Geçersiz rol"}, status=status.HTTP_400_BAD_REQUEST)
        user.role = role
        user.save()
        return Response({"success": f"Rol {role} olarak güncellendi."})


# ----------------------------------------
# 🔹 ÜRÜN SAHİPLİĞİ
# ----------------------------------------
class ProductOwnershipViewSet(viewsets.ModelViewSet):
    queryset = ProductOwnership.objects.all().select_related("customer", "product", "product__category")
    def get_permissions(self):
        return [IsAuthenticated()] if self.action in ["list", "retrieve", "my_ownerships"] else [IsAdminUser()]
    def get_serializer_class(self):
        return ProductOwnershipCreateSerializer if self.action == "create" else ProductOwnershipSerializer
    def get_queryset(self):
        user = self.request.user
        if user.role in ["admin", "seller"]: return ProductOwnership.objects.all().select_related("customer", "product", "product__category")
        return ProductOwnership.objects.filter(customer=user).select_related("product", "product__category")

    @action(detail=False, methods=["get"], url_path="my-ownerships")
    def my_ownerships(self, request):
        ownerships = ProductOwnership.objects.filter(customer=request.user).select_related("product", "product__category")
        data = []
        for ownership in ownerships:
            product = ownership.product
            warranty_end = ownership.warranty_end_date
            is_warranty_active = warranty_end and warranty_end >= timezone.now().date()
            active_requests = ownership.service_requests.exclude(status__in=["completed", "cancelled"]).count()
            data.append({
                "id": ownership.id,
                "product": {
                    "id": product.id, "name": product.name, "brand": product.brand,
                    "price": str(product.price), "image": product.image.url if product.image else None,
                    "category_name": product.category.name if product.category else None,
                    "warranty_duration_months": product.warranty_duration_months,
                },
                "purchase_date": ownership.purchase_date,
                "serial_number": ownership.serial_number,
                "warranty_end_date": warranty_end,
                "is_warranty_active": is_warranty_active,
                "days_until_warranty_expires": (warranty_end - timezone.now().date()).days if warranty_end and is_warranty_active else None,
                "active_service_requests": active_requests,
            })
        return Response(data)


# ----------------------------------------
# 🔹 GRUP & İZİN
# ----------------------------------------
class GroupViewSet(viewsets.ModelViewSet):
    queryset = Group.objects.all()
    permission_classes = [IsAdminUser]
    def list(self, request):
        groups = Group.objects.all().values("id", "name")
        return Response(groups)


# ----------------------------------------
# 🔹 BİLDİRİM AYARLARI
# ----------------------------------------
@api_view(["GET", "PUT", "PATCH"])
@permission_classes([IsAuthenticated])
def notification_settings_view(request):
    user = request.user
    if request.method == "GET":
        return Response({
            "notify_service_updates": user.notify_service_updates, "notify_price_drops": user.notify_price_drops,
            "notify_restock": user.notify_restock, "notify_recommendations": user.notify_recommendations,
            "notify_warranty_expiry": user.notify_warranty_expiry, "notify_general": user.notify_general,
        })
    data = request.data
    if "notify_service_updates" in data: user.notify_service_updates = data["notify_service_updates"]
    if "notify_price_drops" in data: user.notify_price_drops = data["notify_price_drops"]
    if "notify_restock" in data: user.notify_restock = data["notify_restock"]
    if "notify_recommendations" in data: user.notify_recommendations = data["notify_recommendations"]
    if "notify_warranty_expiry" in data: user.notify_warranty_expiry = data["notify_warranty_expiry"]
    if "notify_general" in data: user.notify_general = data["notify_general"]
    user.save()
    return Response({"success": True, "message": "Bildirim ayarları güncellendi"})


# ----------------------------------------
# 🔹 PROFİL
# ----------------------------------------
@api_view(["GET", "PUT", "PATCH"])
@permission_classes([IsAuthenticated])
def profile_view(request):
    user = request.user
    if request.method == "GET":
        return Response({
            "id": user.id, "username": user.username, "email": user.email,
            "first_name": user.first_name, "last_name": user.last_name,
            "phone_number": getattr(user, 'phone_number', ''), "role": user.role, "date_joined": user.date_joined,
        })
    data = request.data
    if "first_name" in data: user.first_name = data["first_name"]
    if "last_name" in data: user.last_name = data["last_name"]
    if "email" in data: user.email = data["email"]
    if "phone_number" in data: user.phone_number = data["phone_number"]
    if "new_password" in data and data["new_password"]:
        if not user.check_password(data.get("current_password", "")):
            return Response({"error": "Mevcut şifre yanlış"}, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(data["new_password"])
    user.save()
    return Response({"success": True, "message": "Profil güncellendi"})


# ----------------------------------------
# 🔹 MOBİL DIRECT ENDPOINT
# ----------------------------------------
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_products_direct(request):
    user = request.user
    if user.role in ["admin", "seller"]:
        qs = Product.objects.all().select_related("category")
        return Response(ProductSerializer(qs, many=True).data)
    ownerships = ProductOwnership.objects.filter(customer=user).select_related("product", "product__category").order_by("-id")
    result = []
    for o in ownerships:
        p = o.product
        item = ProductSerializer(p).data
        if hasattr(o, "assigned_date"): item["assigned_date"] = o.assigned_date
        elif hasattr(o, "assigned_at"): item["assigned_date"] = o.assigned_at
        elif hasattr(o, "created_at"): item["assigned_date"] = o.created_at
        if hasattr(o, "status"): item["status"] = o.status
        result.append(item)
    return Response(result)


# ----------------------------------------
# 🔹 WISHLIST
# ----------------------------------------
class WishlistViewSet(viewsets.ModelViewSet):
    serializer_class = WishlistSerializer
    permission_classes = [IsAuthenticated]
    def get_queryset(self):
        return Wishlist.objects.filter(customer=self.request.user).prefetch_related('items__product')
    def list(self, request):
        wishlist, _ = Wishlist.objects.get_or_create(customer=request.user)
        return Response(WishlistSerializer(wishlist).data)

    @action(detail=False, methods=['post'], url_path='add-item')
    def add_item(self, request):
        wishlist, _ = Wishlist.objects.get_or_create(customer=request.user)
        product_id = request.data.get('product_id')
        if not product_id: return Response({'error': 'product_id gerekli'}, status=status.HTTP_400_BAD_REQUEST)
        try: product = Product.objects.get(id=product_id)
        except Product.DoesNotExist: return Response({'error': 'Ürün bulunamadı'}, status=status.HTTP_404_NOT_FOUND)
        if WishlistItem.objects.filter(wishlist=wishlist, product=product).exists():
            return Response({'error': 'Bu ürün zaten istek listenizde'}, status=status.HTTP_400_BAD_REQUEST)
        item = WishlistItem.objects.create(
            wishlist=wishlist, product=product, note=request.data.get('note', ''),
            notify_on_price_drop=request.data.get('notify_on_price_drop', True),
            notify_on_restock=request.data.get('notify_on_restock', True)
        )
        return Response(WishlistItemSerializer(item).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['delete'], url_path='remove-item/(?P<product_id>[^/.]+)')
    def remove_item(self, request, product_id=None):
        try:
            wishlist = Wishlist.objects.get(customer=request.user)
            WishlistItem.objects.get(wishlist=wishlist, product_id=product_id).delete()
            return Response({'success': 'Ürün çıkarıldı'})
        except: return Response({'error': 'Ürün bulunamadı'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['get'], url_path='check/(?P<product_id>[^/.]+)')
    def check_item(self, request, product_id=None):
        try:
            wishlist = Wishlist.objects.get(customer=request.user)
            exists = WishlistItem.objects.filter(wishlist=wishlist, product_id=product_id).exists()
            return Response({'in_wishlist': exists})
        except: return Response({'in_wishlist': False})


# ----------------------------------------
# 🔹 VIEW HISTORY
# ----------------------------------------
class ViewHistoryViewSet(viewsets.ModelViewSet):
    serializer_class = ViewHistorySerializer
    permission_classes = [IsAuthenticated]
    def get_queryset(self):
        return ViewHistory.objects.filter(customer=self.request.user).select_related('product')

    @action(detail=False, methods=['post'], url_path='record')
    def record_view(self, request):
        product_id = request.data.get('product_id')
        if not product_id: return Response({'error': 'product_id gerekli'}, status=status.HTTP_400_BAD_REQUEST)
        try: product = Product.objects.get(id=product_id)
        except Product.DoesNotExist: return Response({'error': 'Ürün bulunamadı'}, status=status.HTTP_404_NOT_FOUND)
        vh, created = ViewHistory.objects.get_or_create(customer=request.user, product=product, defaults={'view_count': 1})
        if not created:
            vh.view_count = F('view_count') + 1
            vh.viewed_at = timezone.now()
            vh.save()
            vh.refresh_from_db()
        return Response(ViewHistorySerializer(vh).data)

    @action(detail=False, methods=['delete'], url_path='clear')
    def clear_history(self, request):
        ViewHistory.objects.filter(customer=request.user).delete()
        return Response({'success': 'Geçmiş temizlendi'})


# ----------------------------------------
# 🔹 REVIEWS
# ----------------------------------------
class ReviewViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    def get_serializer_class(self):
        return ReviewCreateSerializer if self.action == 'create' else ReviewSerializer
    def get_queryset(self):
        user = self.request.user
        if user.role in ['admin', 'seller']: return Review.objects.all().select_related('customer', 'product')
        return Review.objects.filter(customer=user).select_related('product')
    def perform_create(self, serializer):
        serializer.save(customer=self.request.user)

    @action(detail=False, methods=['get'], url_path='product/(?P<product_id>[^/.]+)')
    def product_reviews(self, request, product_id=None):
        reviews = Review.objects.filter(product_id=product_id, is_approved=True).select_related('customer')
        avg_rating = reviews.aggregate(avg=Avg('rating'))['avg'] or 0
        return Response({
            'reviews': ReviewSerializer(reviews, many=True).data,
            'average_rating': round(avg_rating, 1),
            'total_reviews': reviews.count()
        })

    @action(detail=True, methods=['post'], url_path='approve')
    def approve_review(self, request, pk=None):
        if request.user.role != 'admin': return Response({'error': 'Yetkiniz yok'}, status=status.HTTP_403_FORBIDDEN)
        review = self.get_object()
        review.is_approved = True
        review.save()
        return Response({'success': 'Onaylandı'})


# ----------------------------------------
# 🔹 SERVICE REQUEST
# ----------------------------------------
class ServiceRequestViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    def get_serializer_class(self):
        return ServiceRequestCreateSerializer if self.action == 'create' else ServiceRequestSerializer
    def get_queryset(self):
        user = self.request.user
        if user.role in ['admin', 'seller']:
            return ServiceRequest.objects.all().select_related('customer', 'product_ownership__product', 'assigned_to').prefetch_related('queue_entry')
        return ServiceRequest.objects.filter(customer=user).select_related('product_ownership__product').prefetch_related('queue_entry')

    def perform_create(self, serializer):
        sr = serializer.save(customer=self.request.user)
        last_queue = ServiceQueue.objects.order_by('-queue_number').first()
        qn = (last_queue.queue_number + 1) if last_queue else 1
        ServiceQueue.objects.create(service_request=sr, queue_number=qn, estimated_wait_time=qn * 30)
        sr.status = 'in_queue'
        sr.save()
        Notification.objects.create(user=self.request.user, notification_type='service_update', title='Servis Talebiniz Alındı', message=f'Talep numaranız: SR-{sr.id}.', related_service_request=sr)

    @action(detail=True, methods=['post'], url_path='assign')
    def assign_request(self, request, pk=None):
        if request.user.role not in ['admin', 'seller']: return Response({'error': 'Yetkiniz yok'}, status=status.HTTP_403_FORBIDDEN)
        sr = self.get_object()
        assigned_to_id = request.data.get('assigned_to')
        if assigned_to_id:
            try: sr.assigned_to = CustomUser.objects.get(id=assigned_to_id)
            except: return Response({'error': 'Kullanıcı yok'}, status=status.HTTP_404_NOT_FOUND)
        sr.status = 'in_progress'
        sr.save()
        Notification.objects.create(user=sr.customer, notification_type='service_update', title='Talebiniz İşleme Alındı', message=f'SR-{sr.id} işleme alındı.', related_service_request=sr)
        return Response({'success': 'Atandı'})

    @action(detail=True, methods=['post'], url_path='complete')
    def complete_request(self, request, pk=None):
        if request.user.role not in ['admin', 'seller']: return Response({'error': 'Yetkiniz yok'}, status=status.HTTP_403_FORBIDDEN)
        sr = self.get_object()
        sr.status = 'completed'
        sr.resolution_notes = request.data.get('resolution_notes', '')
        sr.resolved_at = timezone.now()
        sr.save()
        if hasattr(sr, 'queue_entry'): sr.queue_entry.delete()
        Notification.objects.create(user=sr.customer, notification_type='service_update', title='Talebiniz Tamamlandı', message=f'SR-{sr.id} tamamlandı.', related_service_request=sr)
        return Response({'success': 'Tamamlandı'})

    @action(detail=False, methods=['get'], url_path='queue-status')
    def queue_status(self, request):
        queue = ServiceQueue.objects.all().select_related('service_request__customer', 'service_request__product_ownership__product')
        result = []
        for entry in queue:
            result.append({'queue_number': entry.queue_number, 'priority': entry.priority, 'estimated_wait_time': entry.estimated_wait_time, 'service_request': ServiceRequestSerializer(entry.service_request).data})
        return Response(result)


# ----------------------------------------
# 🔹 NOTIFICATIONS
# ----------------------------------------
class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    def get_queryset(self): return Notification.objects.filter(user=self.request.user)
    @action(detail=True, methods=['post'], url_path='read')
    def mark_read(self, request, pk=None):
        n = self.get_object()
        n.is_read = True
        n.save()
        return Response({'success': 'Okundu'})
    @action(detail=False, methods=['post'], url_path='read-all')
    def mark_all_read(self, request):
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({'success': 'Tümü okundu'})
    @action(detail=False, methods=['get'], url_path='unread-count')
    def unread_count(self, request):
        count = Notification.objects.filter(user=request.user, is_read=False).count()
        return Response({'unread_count': count})


# ----------------------------------------
# 🔹 RECOMMENDATION SYSTEM (UPDATED TO 10 ITEMS)
# ----------------------------------------
class RecommendationViewSet(viewsets.ModelViewSet):
    serializer_class = RecommendationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Recommendation.objects.filter(customer=self.request.user).select_related('product')

    @action(detail=False, methods=['post'], url_path='generate')
    def generate_recommendations(self, request):
        """
        POST /api/recommendations/generate/
        Uses HybridRecommender (Good ML)
        """
        user = request.user

        # 1. Clear old recommendations
        Recommendation.objects.filter(customer=user).delete()

        # 2. Init & Run ML
        recommendations_created = []
        try:
            recommender = HybridRecommender()
            # Request 10 items
            recommendations_data = recommender.recommend(user, top_n=10)
            
            # --------------------------------------------------------
            # 🔥 FIX: Normalize scores instead of capping them at 1.0
            # --------------------------------------------------------
            if recommendations_data:
                # Find the highest score in this batch (e.g., 14.5)
                max_score = max(item['score'] for item in recommendations_data)
                
                for item in recommendations_data:
                    # Calculate percentage relative to the best match
                    # Example: 14.5 / 14.5 = 1.0 (100%)
                    # Example: 7.25 / 14.5 = 0.5 (50%)
                    normalized_score = item['score'] / max_score if max_score > 0 else 0

                    rec, created = Recommendation.objects.get_or_create(
                        customer=user,
                        product=item['product'],
                        defaults={
                            'score': normalized_score, # Use the calculated percentage
                            'reason': 'Özel Öneri' if 'reason' not in item else item['reason']
                        }
                    )
                    if created:
                        recommendations_created.append(rec)

        except Exception as e:
            print(f"ML Error: {e}")
            recommendations_created = []

        # 3. Fallback (Cold Start)
        if not recommendations_created:
            last_views = ViewHistory.objects.filter(customer=user).order_by('-viewed_at')[:3]
            if last_views.exists():
                categories = set(v.product.category for v in last_views if v.product.category)
                fallback_products = Product.objects.filter(category__in=categories, stock__gt=0).exclude(id__in=[v.product.id for v in last_views]).order_by('?')[:10]
            else:
                fallback_products = Product.objects.filter(stock__gt=0).order_by('?')[:10]

            for prod in fallback_products:
                # Fallback items get a fixed 0.5 (50%) score since they are random/popular
                rec = Recommendation.objects.create(
                    customer=user, product=prod, score=0.5, reason="Popüler Ürünler"
                )
                recommendations_created.append(rec)

        return Response({
            'success': True,
            'recommendations_count': len(recommendations_created),
            'recommendations': RecommendationSerializer(recommendations_created, many=True).data
        })

    @action(detail=True, methods=['post'], url_path='click')
    def record_click(self, request, pk=None):
        recommendation = self.get_object()
        recommendation.clicked = True
        recommendation.is_shown = True
        recommendation.save()
        return Response({'success': 'Tıklama kaydedildi'})