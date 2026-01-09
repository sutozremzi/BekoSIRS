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


# -------------------------------
# 🔹 InstallmentPlan (Taksit Planı)
# -------------------------------
class InstallmentPlan(models.Model):
    """Müşteriye atanan ürünün taksit planı."""
    STATUS_CHOICES = (
        ('active', 'Aktif'),
        ('completed', 'Tamamlandı'),
        ('cancelled', 'İptal Edildi'),
    )

    customer = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='installment_plans',
        limit_choices_to={'role': 'customer'},
        verbose_name="Müşteri"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='installment_plans',
        verbose_name="Ürün"
    )
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_installment_plans',
        limit_choices_to={'role__in': ['admin', 'seller']},
        verbose_name="Oluşturan"
    )
    total_amount = models.DecimalField(
        max_digits=10, decimal_places=2,
        verbose_name="Toplam Tutar"
    )
    down_payment = models.DecimalField(
        max_digits=10, decimal_places=2,
        default=0,
        verbose_name="Peşinat"
    )
    installment_count = models.PositiveIntegerField(
        verbose_name="Taksit Sayısı"
    )
    start_date = models.DateField(
        verbose_name="Başlangıç Tarihi"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        verbose_name="Durum"
    )
    notes = models.TextField(
        blank=True,
        null=True,
        verbose_name="Notlar"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Taksit Planı"
        verbose_name_plural = "Taksit Planları"
        indexes = [
            models.Index(fields=['customer', 'status'], name='instplan_cust_status_idx'),
            models.Index(fields=['status'], name='instplan_status_idx'),
        ]

    def __str__(self):
        return f"Taksit Planı #{self.id}: {self.customer.username} - {self.product.name}"

    @property
    def remaining_amount(self):
        """Kalan ödeme tutarı."""
        paid = sum(
            inst.amount for inst in self.installments.filter(status='paid')
        )
        return self.total_amount - self.down_payment - paid

    @property
    def paid_amount(self):
        """Ödenen toplam tutar (peşinat dahil)."""
        paid_installments = sum(
            inst.amount for inst in self.installments.filter(status='paid')
        )
        return self.down_payment + paid_installments

    @property
    def paid_installment_count(self):
        """Ödenen taksit sayısı."""
        return self.installments.filter(status='paid').count()

    @property
    def progress_percentage(self):
        """Ödeme ilerleme yüzdesi."""
        if self.total_amount == 0:
            return 0
        return round((float(self.paid_amount) / float(self.total_amount)) * 100, 1)


# -------------------------------
# 🔹 Installment (Taksit)
# -------------------------------
class Installment(models.Model):
    """Taksit planındaki tekil taksit."""
    STATUS_CHOICES = (
        ('pending', 'Bekliyor'),
        ('customer_confirmed', 'Müşteri Onayladı'),
        ('paid', 'Ödendi'),
        ('overdue', 'Gecikmiş'),
    )

    plan = models.ForeignKey(
        InstallmentPlan,
        on_delete=models.CASCADE,
        related_name='installments',
        verbose_name="Taksit Planı"
    )
    installment_number = models.PositiveIntegerField(
        verbose_name="Taksit No"
    )
    amount = models.DecimalField(
        max_digits=10, decimal_places=2,
        verbose_name="Tutar"
    )
    due_date = models.DateField(
        verbose_name="Vade Tarihi"
    )
    payment_date = models.DateField(
        null=True, blank=True,
        verbose_name="Ödeme Tarihi"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="Durum"
    )
    customer_confirmed_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Müşteri Onay Zamanı"
    )
    admin_confirmed_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Admin Onay Zamanı"
    )

    class Meta:
        ordering = ['plan', 'installment_number']
        unique_together = [['plan', 'installment_number']]
        verbose_name = "Taksit"
        verbose_name_plural = "Taksitler"
        indexes = [
            models.Index(fields=['status'], name='inst_status_idx'),
            models.Index(fields=['due_date'], name='inst_due_date_idx'),
            models.Index(fields=['plan', 'status'], name='inst_plan_status_idx'),
        ]

    def __str__(self):
        return f"Taksit #{self.installment_number} - Plan #{self.plan.id}"

    @property
    def is_overdue(self):
        """Taksit gecikmiş mi?"""
        from django.utils import timezone
        if self.status in ['paid', 'customer_confirmed']:
            return False
        return self.due_date < timezone.now().date()

    @property
    def days_until_due(self):
        """Vadeye kalan gün sayısı (negatif ise gecikmiş)."""
        from django.utils import timezone
        delta = self.due_date - timezone.now().date()
        return delta.days

    @property
    def days_overdue(self):
        """Gecikme gün sayısı (0 veya pozitif)."""
        if self.days_until_due >= 0:
            return 0
        return abs(self.days_until_due)


# -------------------------------
# 🔹 AuditLog (Denetim Kaydı)
# -------------------------------
class AuditLog(models.Model):
    """
    Tüm önemli işlemlerin denetim kaydı.
    Güvenlik, sorun giderme ve uyumluluk için kullanılır.
    """
    ACTION_CHOICES = (
        ('create', 'Oluşturma'),
        ('update', 'Güncelleme'),
        ('delete', 'Silme'),
        ('login', 'Giriş'),
        ('logout', 'Çıkış'),
        ('login_failed', 'Başarısız Giriş'),
        ('password_change', 'Şifre Değişikliği'),
        ('password_reset', 'Şifre Sıfırlama'),
        ('permission_change', 'Yetki Değişikliği'),
        ('export', 'Veri Dışa Aktarma'),
        ('api_access', 'API Erişimi'),
        ('bulk_operation', 'Toplu İşlem'),
    )

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        verbose_name="Kullanıcı"
    )
    action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES,
        verbose_name="İşlem"
    )
    model_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Model Adı",
        help_text="Etkilenen modelin adı (örn: Product, Order)"
    )
    object_id = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Nesne ID",
        help_text="Etkilenen nesnenin ID'si"
    )
    object_repr = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Nesne Temsili",
        help_text="Nesnenin string temsili"
    )
    changes = models.JSONField(
        null=True,
        blank=True,
        verbose_name="Değişiklikler",
        help_text="{'field': [old_value, new_value]} formatında"
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name="IP Adresi"
    )
    user_agent = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name="User Agent"
    )
    request_path = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name="İstek Yolu"
    )
    request_method = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        verbose_name="HTTP Metodu"
    )
    status_code = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Durum Kodu"
    )
    extra_data = models.JSONField(
        null=True,
        blank=True,
        verbose_name="Ek Veri",
        help_text="İşleme özgü ek bilgiler"
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Zaman Damgası"
    )

    class Meta:
        ordering = ['-timestamp']
        verbose_name = "Denetim Kaydı"
        verbose_name_plural = "Denetim Kayıtları"
        indexes = [
            models.Index(fields=['user', 'action'], name='audit_user_action_idx'),
            models.Index(fields=['model_name', 'object_id'], name='audit_model_obj_idx'),
            models.Index(fields=['action'], name='audit_action_idx'),
            models.Index(fields=['timestamp'], name='audit_timestamp_idx'),
            models.Index(fields=['ip_address'], name='audit_ip_idx'),
        ]

    def __str__(self):
        user_str = self.user.username if self.user else "Anonymous"
        return f"{user_str} - {self.get_action_display()} - {self.timestamp.strftime('%Y-%m-%d %H:%M')}"

    @classmethod
    def log(cls, user, action, model_name=None, object_id=None, object_repr=None,
            changes=None, request=None, extra_data=None, status_code=None):
        """
        Convenience method to create an audit log entry.
        
        Usage:
            AuditLog.log(
                user=request.user,
                action='create',
                model_name='Product',
                object_id=product.id,
                object_repr=str(product),
                changes={'price': [100, 150]},
                request=request
            )
        """
        ip_address = None
        user_agent = None
        request_path = None
        request_method = None
        
        if request:
            # Get IP address
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip_address = x_forwarded_for.split(',')[0].strip()
            else:
                ip_address = request.META.get('REMOTE_ADDR')
            
            user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
            request_path = request.path[:500]
            request_method = request.method
        
        return cls.objects.create(
            user=user if user and user.is_authenticated else None,
            action=action,
            model_name=model_name,
            object_id=object_id,
            object_repr=object_repr[:255] if object_repr else None,
            changes=changes,
            ip_address=ip_address,
            user_agent=user_agent,
            request_path=request_path,
            request_method=request_method,
            status_code=status_code,
            extra_data=extra_data
        )


