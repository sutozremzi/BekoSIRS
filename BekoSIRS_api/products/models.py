from django.db import models
from django.contrib.auth.models import AbstractUser
from dateutil.relativedelta import relativedelta

# -------------------------------
# 🔹 Custom User Model
# -------------------------------
class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('seller', 'Satıcı'),
        ('customer', 'Müşteri'),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='customer')
    phone_number = models.CharField(max_length=15, unique=True, null=True, blank=True)

    # Bildirim Tercihleri
    notify_service_updates = models.BooleanField(default=True, verbose_name="Servis Güncellemeleri")
    notify_price_drops = models.BooleanField(default=True, verbose_name="Fiyat Düşüşleri")
    notify_restock = models.BooleanField(default=True, verbose_name="Stok Bildirimleri")
    notify_recommendations = models.BooleanField(default=True, verbose_name="Ürün Önerileri")
    notify_warranty_expiry = models.BooleanField(default=True, verbose_name="Garanti Süresi Uyarıları")
    notify_general = models.BooleanField(default=True, verbose_name="Genel Bildirimler")

    # Biometric Authentication (Face ID / Face Unlock)
    biometric_enabled = models.BooleanField(default=False, verbose_name="Biyometrik Giriş")
    biometric_device_id = models.CharField(
        max_length=255, 
        null=True, 
        blank=True, 
        verbose_name="Biyometrik Cihaz ID",
        help_text="Device identifier for biometric login"
    )

    # Adres Bilgileri (Nakliye için)
    address = models.TextField(blank=True, null=True, verbose_name="Adres")
    address_city = models.CharField(max_length=100, blank=True, null=True, verbose_name="Şehir")
    address_lat = models.DecimalField(
        max_digits=10, decimal_places=7, null=True, blank=True,
        verbose_name="Enlem", help_text="Latitude koordinatı"
    )
    address_lng = models.DecimalField(
        max_digits=10, decimal_places=7, null=True, blank=True,
        verbose_name="Boylam", help_text="Longitude koordinatı"
    )

    def __str__(self):
        return f"{self.username} ({self.role})"


# -------------------------------
# 🔹 Category Model
# -------------------------------
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='subcategories')

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


# -------------------------------
# 🔹 Product Model
# -------------------------------
class Product(models.Model):
    name = models.CharField(max_length=100)
    brand = models.CharField(max_length=50)
    category = models.ForeignKey(Category, related_name='products', on_delete=models.SET_NULL, null=True)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    
    # New fields from Excel Import
    model_code = models.CharField(max_length=100, unique=True, null=True, blank=True, verbose_name="Model Kodu")
    warranty_code = models.CharField(max_length=50, null=True, blank=True, verbose_name="Ek Garanti Kodu")
    price_list = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Liste Fiyatı")
    price_cash = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Peşin Fiyat")
    campaign_tag = models.CharField(max_length=100, null=True, blank=True, verbose_name="Kampanya")
    
    #status = models.CharField(max_length=20, default='in_stock')
    warranty_duration_months = models.PositiveIntegerField(default=24, help_text="Garanti süresi (ay olarak)")
    stock = models.IntegerField(default=0, verbose_name="Stok Adedi")

    def __str__(self):
        return self.name


# -------------------------------
# 🔹 Product Ownership (Kim aldı?)
# -------------------------------
class ProductOwnership(models.Model):
    customer = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='owned_products',
        limit_choices_to={'role': 'customer'}
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    purchase_date = models.DateField()
    serial_number = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.customer.username} owns {self.product.name}"

    @property
    def warranty_end_date(self):
        if self.purchase_date:
            return self.purchase_date + relativedelta(months=self.product.warranty_duration_months)
        return None


# -------------------------------
# 🔹 Kullanıcı Aktivite Takibi
# -------------------------------
class UserActivity(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    activity_type = models.CharField(max_length=10)  # 'view', 'search'
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.activity_type} - {self.product.name}"


# -------------------------------
# 🔹 Wishlist (İstek Listesi)
# -------------------------------
class Wishlist(models.Model):
    customer = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='wishlist',
        limit_choices_to={'role': 'customer'}
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.customer.username}'s Wishlist"

    @property
    def item_count(self):
        return self.items.count()


# -------------------------------
# 🔹 WishlistItem (İstek Listesi Öğesi)
# -------------------------------
class WishlistItem(models.Model):
    wishlist = models.ForeignKey(
        Wishlist,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='wishlisted_by'
    )
    added_at = models.DateTimeField(auto_now_add=True)
    note = models.TextField(blank=True, null=True, help_text="Kullanıcı notu")
    notify_on_price_drop = models.BooleanField(default=True, help_text="Fiyat düşüşünde bildirim")
    notify_on_restock = models.BooleanField(default=True, help_text="Stok geldiğinde bildirim")

    class Meta:
        unique_together = ('wishlist', 'product')
        ordering = ['-added_at']

    def __str__(self):
        return f"{self.wishlist.customer.username} - {self.product.name}"


# -------------------------------
# 🔹 ViewHistory (Görüntüleme Geçmişi)
# -------------------------------
class ViewHistory(models.Model):
    customer = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='view_history',
        limit_choices_to={'role': 'customer'}
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='viewed_by'
    )
    viewed_at = models.DateTimeField(auto_now_add=True)
    view_count = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ('customer', 'product')
        ordering = ['-viewed_at']

    def __str__(self):
        return f"{self.customer.username} viewed {self.product.name}"


# -------------------------------
# 🔹 Review (Ürün Değerlendirmesi)
# -------------------------------
class Review(models.Model):
    customer = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='reviews',
        limit_choices_to={'role': 'customer'}
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    rating = models.PositiveIntegerField(help_text="1-5 arası puan")
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_approved = models.BooleanField(default=False, help_text="Admin onayı")

    class Meta:
        unique_together = ('customer', 'product')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.customer.username} - {self.product.name} ({self.rating}/5)"


# -------------------------------
# 🔹 ServiceRequest (Servis Talebi)
# -------------------------------
class ServiceRequest(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Beklemede'),
        ('in_queue', 'Sırada'),
        ('in_progress', 'İşlemde'),
        ('completed', 'Tamamlandı'),
        ('cancelled', 'İptal Edildi'),
    )
    REQUEST_TYPE_CHOICES = (
        ('repair', 'Tamir'),
        ('maintenance', 'Bakım'),
        ('warranty', 'Garanti'),
        ('complaint', 'Şikayet'),
        ('other', 'Diğer'),
    )

    customer = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='service_requests',
        limit_choices_to={'role': 'customer'}
    )
    product_ownership = models.ForeignKey(
        ProductOwnership,
        on_delete=models.CASCADE,
        related_name='service_requests'
    )
    request_type = models.CharField(max_length=20, choices=REQUEST_TYPE_CHOICES, default='repair')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    description = models.TextField(help_text="Sorun açıklaması")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    assigned_to = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_requests',
        limit_choices_to={'role__in': ['admin', 'seller']}
    )
    resolution_notes = models.TextField(blank=True, null=True, help_text="Çözüm notları")
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status'], name='svcreq_status_idx'),
            models.Index(fields=['customer', 'status'], name='svcreq_cust_status_idx'),
            models.Index(fields=['created_at'], name='svcreq_created_idx'),
        ]

    def __str__(self):
        return f"SR-{self.id}: {self.customer.username} - {self.product_ownership.product.name}"


# -------------------------------
# 🔹 ServiceQueue (Servis Kuyruğu)
# -------------------------------
class ServiceQueue(models.Model):
    service_request = models.OneToOneField(
        ServiceRequest,
        on_delete=models.CASCADE,
        related_name='queue_entry'
    )
    queue_number = models.PositiveIntegerField()
    priority = models.PositiveIntegerField(default=5, help_text="1=En yüksek, 10=En düşük")
    estimated_wait_time = models.PositiveIntegerField(default=0, help_text="Tahmini bekleme süresi (dakika)")
    entered_queue_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['priority', 'entered_queue_at']

    def __str__(self):
        return f"Queue #{self.queue_number} - SR-{self.service_request.id}"


# -------------------------------
# 🔹 Notification (Bildirim)
# -------------------------------
class Notification(models.Model):
    NOTIFICATION_TYPE_CHOICES = (
        ('price_drop', 'Fiyat Düşüşü'),
        ('restock', 'Stok Geldi'),
        ('service_update', 'Servis Güncellemesi'),
        ('recommendation', 'Öneri'),
        ('general', 'Genel'),
    )

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPE_CHOICES, default='general')
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    related_product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifications'
    )
    related_service_request = models.ForeignKey(
        ServiceRequest,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifications'
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read'], name='notif_user_read_idx'),
            models.Index(fields=['notification_type'], name='notif_type_idx'),
            models.Index(fields=['created_at'], name='notif_created_idx'),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.title}"


# -------------------------------
# 🔹 Recommendation (Öneri)
# -------------------------------
class Recommendation(models.Model):
    customer = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='recommendations',
        limit_choices_to={'role': 'customer'}
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='recommended_to'
    )
    score = models.FloatField(help_text="Öneri skoru (0-1)")
    reason = models.CharField(max_length=200, help_text="Öneri sebebi")
    created_at = models.DateTimeField(auto_now_add=True)
    is_shown = models.BooleanField(default=False)
    clicked = models.BooleanField(default=False)

    class Meta:
        unique_together = ('customer', 'product')
        ordering = ['-score', '-created_at']

    def __str__(self):
        return f"Recommendation: {self.product.name} for {self.customer.username}"


# -------------------------------
# 🔹 Password Reset Token Model
# -------------------------------
class PasswordResetToken(models.Model):
    """
    Token for password reset requests.
    Expires after 1 hour.
    """
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='password_reset_tokens'
    )
    token = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Password reset token for {self.user.username}"

    @classmethod
    def generate_token(cls):
        """Generate a secure random token."""
        import secrets
        return secrets.token_urlsafe(48)

    @classmethod
    def create_for_user(cls, user):
        """Create a new password reset token for a user."""
        from django.utils import timezone
        from datetime import timedelta
        
        # Invalidate any existing tokens for this user
        cls.objects.filter(user=user, is_used=False).update(is_used=True)
        
        # Create new token with 1 hour expiration
        token = cls.generate_token()
        expires_at = timezone.now() + timedelta(hours=1)
        
        return cls.objects.create(
            user=user,
            token=token,
            expires_at=expires_at
        )

    def is_valid(self):
        """Check if token is valid (not used and not expired)."""
        from django.utils import timezone
        return not self.is_used and self.expires_at > timezone.now()

    def use(self):
        """Mark token as used."""
        self.is_used = True
        self.save()


# -------------------------------
# 🔹 Delivery (Teslimat)
# -------------------------------
class Delivery(models.Model):
    """Müşterilere yapılacak teslimatları temsil eder."""
    STATUS_CHOICES = (
        ('pending', 'Bekliyor'),
        ('assigned', 'Rotaya Atandı'),
        ('in_transit', 'Yolda'),
        ('delivered', 'Teslim Edildi'),
        ('cancelled', 'İptal'),
    )
    
    customer = models.ForeignKey(
        CustomUser, 
        on_delete=models.CASCADE, 
        related_name='deliveries',
        verbose_name="Müşteri"
    )
    product_ownership = models.ForeignKey(
        ProductOwnership, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='deliveries',
        verbose_name="Satın Alınan Ürün"
    )
    delivery_date = models.DateField(verbose_name="Teslimat Tarihi")
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pending',
        verbose_name="Durum"
    )
    
    # Teslimat Adresi (Müşteri adresinden farklı olabilir)
    address = models.TextField(verbose_name="Teslimat Adresi")
    address_lat = models.DecimalField(
        max_digits=10, decimal_places=7, null=True, blank=True,
        verbose_name="Enlem"
    )
    address_lng = models.DecimalField(
        max_digits=10, decimal_places=7, null=True, blank=True,
        verbose_name="Boylam"
    )
    
    notes = models.TextField(blank=True, verbose_name="Notlar")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['delivery_date', 'created_at']
        verbose_name = "Teslimat"
        verbose_name_plural = "Teslimatlar"

    def __str__(self):
        return f"{self.customer.username} - {self.delivery_date} ({self.get_status_display()})"


# -------------------------------
# 🔹 Delivery Route (Günlük Rota)
# -------------------------------
class DeliveryRoute(models.Model):
    """Belirli bir gün için optimize edilmiş teslimat rotası."""
    date = models.DateField(unique=True, verbose_name="Tarih")
    
    # Mağaza (başlangıç noktası) koordinatları
    store_address = models.TextField(
        default="Beko Mağaza, Lefkoşa",
        verbose_name="Mağaza Adresi"
    )
    store_lat = models.DecimalField(
        max_digits=10, decimal_places=7, 
        default=35.1856,  # Lefkoşa
        verbose_name="Mağaza Enlemi"
    )
    store_lng = models.DecimalField(
        max_digits=10, decimal_places=7, 
        default=33.3823,  # Lefkoşa
        verbose_name="Mağaza Boylamı"
    )
    
    # Rota istatistikleri
    total_distance_km = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        verbose_name="Toplam Mesafe (km)"
    )
    total_duration_min = models.IntegerField(
        null=True, blank=True,
        verbose_name="Toplam Süre (dk)"
    )
    
    is_optimized = models.BooleanField(default=False, verbose_name="Optimize Edildi")
    optimized_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']
        verbose_name = "Teslimat Rotası"
        verbose_name_plural = "Teslimat Rotaları"

    def __str__(self):
        return f"Rota: {self.date} ({self.stops.count()} durak)"


# -------------------------------
# 🔹 Delivery Route Stop (Rota Durağı)
# -------------------------------
class DeliveryRouteStop(models.Model):
    """Rotadaki her bir durak (sıralı)."""
    route = models.ForeignKey(
        DeliveryRoute, 
        on_delete=models.CASCADE, 
        related_name='stops',
        verbose_name="Rota"
    )
    delivery = models.ForeignKey(
        Delivery, 
        on_delete=models.CASCADE, 
        related_name='route_stops',
        verbose_name="Teslimat"
    )
    stop_order = models.PositiveIntegerField(
        verbose_name="Sıra",
        help_text="0=Mağaza (başlangıç), 1,2,3...=Müşteriler"
    )
    
    # Tahmini varış
    estimated_arrival = models.TimeField(
        null=True, blank=True,
        verbose_name="Tahmini Varış"
    )
    distance_from_previous_km = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        verbose_name="Önceki Duraktan Mesafe (km)"
    )
    duration_from_previous_min = models.IntegerField(
        null=True, blank=True,
        verbose_name="Önceki Duraktan Süre (dk)"
    )

    class Meta:
        ordering = ['route', 'stop_order']
        unique_together = [['route', 'stop_order'], ['route', 'delivery']]
        verbose_name = "Rota Durağı"
        verbose_name_plural = "Rota Durakları"

    def __str__(self):
        return f"{self.route.date} - Durak {self.stop_order}: {self.delivery.customer.username}"
