# products/email_service.py
"""
Email service utility for sending various email types.
"""

from django.conf import settings
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags


class EmailService:
    """
    Service class for sending emails.
    Uses console backend in development, SMTP in production.
    """
    
    @staticmethod
    def send_password_reset_email(user, token):
        """
        Send password reset email with token.
        
        Args:
            user: CustomUser instance
            token: PasswordResetToken instance
        
        Returns:
            bool: True if sent successfully
        """
        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token.token}"
        
        subject = 'BekoSIRS - Şifre Sıfırlama Talebi'
        
        # Plain text message
        text_message = f"""
Merhaba {user.first_name or user.username},

Şifrenizi sıfırlamak için bir talep aldık.

Şifrenizi sıfırlamak için aşağıdaki linke tıklayın:
{reset_url}

Bu link 1 saat içinde geçerliliğini yitirecektir.

Eğer bu talebi siz yapmadıysanız, bu e-postayı görmezden gelebilirsiniz.

Saygılarımızla,
BekoSIRS Ekibi
        """
        
        # HTML message
        html_message = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #2563eb; color: white; padding: 20px; text-align: center; }}
        .content {{ padding: 30px; background-color: #f9fafb; }}
        .button {{ 
            display: inline-block; 
            padding: 12px 24px; 
            background-color: #2563eb; 
            color: white; 
            text-decoration: none; 
            border-radius: 6px;
            margin: 20px 0;
        }}
        .footer {{ padding: 20px; text-align: center; color: #6b7280; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>BekoSIRS</h1>
        </div>
        <div class="content">
            <h2>Şifre Sıfırlama</h2>
            <p>Merhaba <strong>{user.first_name or user.username}</strong>,</p>
            <p>Şifrenizi sıfırlamak için bir talep aldık. Aşağıdaki butona tıklayarak yeni şifrenizi belirleyebilirsiniz:</p>
            <p style="text-align: center;">
                <a href="{reset_url}" class="button">Şifremi Sıfırla</a>
            </p>
            <p><small>Bu link 1 saat içinde geçerliliğini yitirecektir.</small></p>
            <p>Eğer bu talebi siz yapmadıysanız, bu e-postayı görmezden gelebilirsiniz.</p>
        </div>
        <div class="footer">
            <p>© 2026 BekoSIRS. Tüm hakları saklıdır.</p>
        </div>
    </div>
</body>
</html>
        """
        
        try:
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_message.strip(),
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email]
            )
            email.attach_alternative(html_message, "text/html")
            email.send()
            return True
        except Exception as e:
            print(f"Error sending password reset email: {e}")
            return False

    @staticmethod
    def send_welcome_email(user):
        """
        Send welcome email to newly registered user.
        
        Args:
            user: CustomUser instance
        
        Returns:
            bool: True if sent successfully
        """
        subject = 'BekoSIRS\'a Hoş Geldiniz!'
        
        text_message = f"""
Merhaba {user.first_name or user.username},

BekoSIRS ailesine hoş geldiniz!

Artık Beko ürünlerinizi takip edebilir, servis taleplerinde bulunabilir ve size özel öneriler alabilirsiniz.

Herhangi bir sorunuz olursa bizimle iletişime geçmekten çekinmeyin.

Saygılarımızla,
BekoSIRS Ekibi
        """
        
        html_message = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #2563eb; color: white; padding: 20px; text-align: center; }}
        .content {{ padding: 30px; background-color: #f9fafb; }}
        .button {{ 
            display: inline-block; 
            padding: 12px 24px; 
            background-color: #2563eb; 
            color: white; 
            text-decoration: none; 
            border-radius: 6px;
            margin: 20px 0;
        }}
        .footer {{ padding: 20px; text-align: center; color: #6b7280; font-size: 12px; }}
        .features {{ margin: 20px 0; }}
        .features li {{ margin: 10px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>BekoSIRS'a Hoş Geldiniz!</h1>
        </div>
        <div class="content">
            <p>Merhaba <strong>{user.first_name or user.username}</strong>,</p>
            <p>BekoSIRS ailesine hoş geldiniz! 🎉</p>
            <p>Artık şunları yapabilirsiniz:</p>
            <ul class="features">
                <li>✅ Beko ürünlerinizi takip edin</li>
                <li>✅ Garanti durumunuzu kontrol edin</li>
                <li>✅ Servis taleplerinde bulunun</li>
                <li>✅ Size özel ürün önerileri alın</li>
            </ul>
            <p style="text-align: center;">
                <a href="{settings.FRONTEND_URL}" class="button">Uygulamaya Git</a>
            </p>
        </div>
        <div class="footer">
            <p>© 2026 BekoSIRS. Tüm hakları saklıdır.</p>
        </div>
    </div>
</body>
</html>
        """
        
        try:
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_message.strip(),
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email]
            )
            email.attach_alternative(html_message, "text/html")
            email.send()
            return True
        except Exception as e:
            print(f"Error sending welcome email: {e}")
            return False

    @staticmethod
    def send_price_drop_notification(user, product, old_price, new_price):
        """
        Send price drop notification to user who has product in wishlist.
        
        Args:
            user: CustomUser instance
            product: Product instance
            old_price: Decimal - previous price
            new_price: Decimal - new discounted price
        
        Returns:
            bool: True if sent successfully
        """
        discount_percent = int(((old_price - new_price) / old_price) * 100)
        product_url = f"{settings.FRONTEND_URL}/product/{product.id}"
        
        subject = f'🔥 Fiyat Düştü! {product.name}'
        
        text_message = f"""
Merhaba {user.first_name or user.username},

İstek listenizde bulunan "{product.name}" ürününün fiyatı düştü!

Eski Fiyat: {old_price}₺
Yeni Fiyat: {new_price}₺
İndirim: %{discount_percent}

Bu fırsatı kaçırmayın!

Ürüne git: {product_url}

Saygılarımızla,
BekoSIRS Ekibi
        """
        
        html_message = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #dc2626; color: white; padding: 20px; text-align: center; }}
        .content {{ padding: 30px; background-color: #f9fafb; }}
        .button {{ 
            display: inline-block; 
            padding: 12px 24px; 
            background-color: #dc2626; 
            color: white; 
            text-decoration: none; 
            border-radius: 6px;
            margin: 20px 0;
        }}
        .price-box {{ background-color: #fef2f2; padding: 20px; border-radius: 8px; margin: 20px 0; }}
        .old-price {{ text-decoration: line-through; color: #9ca3af; font-size: 18px; }}
        .new-price {{ color: #dc2626; font-size: 28px; font-weight: bold; }}
        .discount {{ background-color: #dc2626; color: white; padding: 4px 8px; border-radius: 4px; }}
        .footer {{ padding: 20px; text-align: center; color: #6b7280; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔥 Fiyat Düştü!</h1>
        </div>
        <div class="content">
            <p>Merhaba <strong>{user.first_name or user.username}</strong>,</p>
            <p>İstek listenizde bulunan ürünün fiyatı düştü!</p>
            
            <h3>{product.name}</h3>
            <p><strong>{product.brand}</strong></p>
            
            <div class="price-box">
                <p><span class="old-price">{old_price}₺</span></p>
                <p><span class="new-price">{new_price}₺</span> <span class="discount">%{discount_percent} İNDİRİM</span></p>
            </div>
            
            <p style="text-align: center;">
                <a href="{product_url}" class="button">Ürüne Git</a>
            </p>
            <p><small>Bu fırsatı kaçırmayın!</small></p>
        </div>
        <div class="footer">
            <p>© 2026 BekoSIRS. Tüm hakları saklıdır.</p>
            <p><small>Bu bildirimi almak istemiyorsanız, istek listesi ayarlarınızdan bildirimleri kapatabilirsiniz.</small></p>
        </div>
    </div>
</body>
</html>
        """
        
        try:
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_message.strip(),
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email]
            )
            email.attach_alternative(html_message, "text/html")
            email.send()
            return True
        except Exception as e:
            print(f"Error sending price drop email: {e}")
            return False

    @staticmethod
    def send_restock_notification(user, product):
        """
        Send restock notification to user who has product in wishlist.
        
        Args:
            user: CustomUser instance
            product: Product instance
        
        Returns:
            bool: True if sent successfully
        """
        product_url = f"{settings.FRONTEND_URL}/product/{product.id}"
        
        subject = f'✅ Stok Geldi! {product.name}'
        
        text_message = f"""
Merhaba {user.first_name or user.username},

İstek listenizde bulunan "{product.name}" ürünü tekrar stokta!

Stok Adedi: {product.stock}

Hemen sipariş verin!

Ürüne git: {product_url}

Saygılarımızla,
BekoSIRS Ekibi
        """
        
        html_message = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #16a34a; color: white; padding: 20px; text-align: center; }}
        .content {{ padding: 30px; background-color: #f9fafb; }}
        .button {{ 
            display: inline-block; 
            padding: 12px 24px; 
            background-color: #16a34a; 
            color: white; 
            text-decoration: none; 
            border-radius: 6px;
            margin: 20px 0;
        }}
        .stock-badge {{ background-color: #dcfce7; color: #16a34a; padding: 8px 16px; border-radius: 4px; font-weight: bold; }}
        .footer {{ padding: 20px; text-align: center; color: #6b7280; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>✅ Stok Geldi!</h1>
        </div>
        <div class="content">
            <p>Merhaba <strong>{user.first_name or user.username}</strong>,</p>
            <p>İstek listenizde bulunan ürün tekrar stokta!</p>
            
            <h3>{product.name}</h3>
            <p><strong>{product.brand}</strong></p>
            <p>Fiyat: <strong>{product.price}₺</strong></p>
            <p><span class="stock-badge">Stokta: {product.stock} adet</span></p>
            
            <p style="text-align: center;">
                <a href="{product_url}" class="button">Hemen Sipariş Ver</a>
            </p>
            <p><small>Stoklar sınırlıdır, acele edin!</small></p>
        </div>
        <div class="footer">
            <p>© 2026 BekoSIRS. Tüm hakları saklıdır.</p>
        </div>
    </div>
</body>
</html>
        """
        
        try:
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_message.strip(),
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email]
            )
            email.attach_alternative(html_message, "text/html")
            email.send()
            return True
        except Exception as e:
            print(f"Error sending restock email: {e}")
            return False

    @staticmethod
    def send_service_update_notification(user, service_request, old_status, new_status):
        """
        Send service request status update notification.
        
        Args:
            user: CustomUser instance
            service_request: ServiceRequest instance
            old_status: str - previous status
            new_status: str - new status
        
        Returns:
            bool: True if sent successfully
        """
        status_display = {
            'pending': 'Beklemede',
            'in_queue': 'Sırada',
            'in_progress': 'İşlemde',
            'completed': 'Tamamlandı',
            'cancelled': 'İptal Edildi'
        }
        
        status_emoji = {
            'pending': '⏳',
            'in_queue': '📋',
            'in_progress': '🔧',
            'completed': '✅',
            'cancelled': '❌'
        }
        
        old_display = status_display.get(old_status, old_status)
        new_display = status_display.get(new_status, new_status)
        emoji = status_emoji.get(new_status, '📢')
        
        subject = f'{emoji} Servis Talebi Güncellendi - #{service_request.id}'
        
        text_message = f"""
Merhaba {user.first_name or user.username},

#{service_request.id} numaralı servis talebinizin durumu güncellendi.

Ürün: {service_request.ownership.product.name}
Önceki Durum: {old_display}
Yeni Durum: {new_display}

Saygılarımızla,
BekoSIRS Ekibi
        """
        
        # Color based on status
        status_colors = {
            'pending': '#f59e0b',
            'in_queue': '#3b82f6',
            'in_progress': '#8b5cf6',
            'completed': '#16a34a',
            'cancelled': '#dc2626'
        }
        color = status_colors.get(new_status, '#2563eb')
        
        html_message = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: {color}; color: white; padding: 20px; text-align: center; }}
        .content {{ padding: 30px; background-color: #f9fafb; }}
        .status-box {{ background-color: white; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid {color}; }}
        .status-change {{ display: flex; align-items: center; justify-content: center; gap: 20px; margin: 20px 0; }}
        .status {{ padding: 8px 16px; border-radius: 4px; font-weight: bold; }}
        .old-status {{ background-color: #e5e7eb; color: #6b7280; }}
        .new-status {{ background-color: {color}; color: white; }}
        .footer {{ padding: 20px; text-align: center; color: #6b7280; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{emoji} Servis Talebi Güncellendi</h1>
        </div>
        <div class="content">
            <p>Merhaba <strong>{user.first_name or user.username}</strong>,</p>
            <p>Servis talebinizin durumu güncellendi.</p>
            
            <div class="status-box">
                <p><strong>Talep No:</strong> #{service_request.id}</p>
                <p><strong>Ürün:</strong> {service_request.ownership.product.name}</p>
                <p><strong>Açıklama:</strong> {service_request.description[:100]}...</p>
            </div>
            
            <div class="status-change">
                <span class="status old-status">{old_display}</span>
                <span>→</span>
                <span class="status new-status">{new_display}</span>
            </div>
            
            <p>Servis süreciyle ilgili sorularınız için bizimle iletişime geçebilirsiniz.</p>
        </div>
        <div class="footer">
            <p>© 2026 BekoSIRS. Tüm hakları saklıdır.</p>
        </div>
    </div>
</body>
</html>
        """
        
        try:
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_message.strip(),
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email]
            )
            email.attach_alternative(html_message, "text/html")
            email.send()
            return True
        except Exception as e:
            print(f"Error sending service update email: {e}")
            return False

    @staticmethod
    def send_warranty_expiry_reminder(user, ownership, days_remaining):
        """
        Send warranty expiry reminder.
        
        Args:
            user: CustomUser instance
            ownership: ProductOwnership instance
            days_remaining: int - days until warranty expires
        
        Returns:
            bool: True if sent successfully
        """
        product = ownership.product
        product_url = f"{settings.FRONTEND_URL}/my-products"
        
        if days_remaining <= 7:
            urgency = "🚨 ACİL"
            color = "#dc2626"
        elif days_remaining <= 30:
            urgency = "⚠️ ÖNEMLİ"
            color = "#f59e0b"
        else:
            urgency = "📅 Hatırlatma"
            color = "#3b82f6"
        
        subject = f'{urgency} Garanti Süresi Bitiyor - {product.name}'
        
        text_message = f"""
Merhaba {user.first_name or user.username},

"{product.name}" ürününüzün garanti süresi {days_remaining} gün sonra sona erecek.

Ürün: {product.name}
Marka: {product.brand}
Satın Alma Tarihi: {ownership.purchase_date}
Garanti Bitiş Tarihi: {ownership.warranty_end_date}

Garanti süresi dolmadan önce herhangi bir sorununuz varsa lütfen servis talebi oluşturun.

Saygılarımızla,
BekoSIRS Ekibi
        """
        
        html_message = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: {color}; color: white; padding: 20px; text-align: center; }}
        .content {{ padding: 30px; background-color: #f9fafb; }}
        .button {{ 
            display: inline-block; 
            padding: 12px 24px; 
            background-color: {color}; 
            color: white; 
            text-decoration: none; 
            border-radius: 6px;
            margin: 20px 0;
        }}
        .countdown {{ font-size: 48px; font-weight: bold; color: {color}; text-align: center; margin: 20px 0; }}
        .info-box {{ background-color: white; padding: 20px; border-radius: 8px; margin: 20px 0; }}
        .footer {{ padding: 20px; text-align: center; color: #6b7280; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{urgency}</h1>
            <p>Garanti Süresi Bitiyor</p>
        </div>
        <div class="content">
            <p>Merhaba <strong>{user.first_name or user.username}</strong>,</p>
            
            <div class="countdown">{days_remaining} Gün</div>
            <p style="text-align: center;"><strong>{product.name}</strong> ürününüzün garanti süresi bitiyor!</p>
            
            <div class="info-box">
                <p><strong>Ürün:</strong> {product.name}</p>
                <p><strong>Marka:</strong> {product.brand}</p>
                <p><strong>Satın Alma:</strong> {ownership.purchase_date}</p>
                <p><strong>Garanti Bitiş:</strong> {ownership.warranty_end_date}</p>
            </div>
            
            <p>Garanti süresi dolmadan önce herhangi bir sorununuz varsa servis talebi oluşturmanızı öneririz.</p>
            
            <p style="text-align: center;">
                <a href="{product_url}" class="button">Ürünlerimi Görüntüle</a>
            </p>
        </div>
        <div class="footer">
            <p>© 2026 BekoSIRS. Tüm hakları saklıdır.</p>
        </div>
    </div>
</body>
</html>
        """
        
        try:
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_message.strip(),
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email]
            )
            email.attach_alternative(html_message, "text/html")
            email.send()
            return True
        except Exception as e:
            print(f"Error sending warranty expiry email: {e}")
            return False

    @staticmethod
    def send_installment_reminder(user, installment, days_until_due):
        """
        Send installment payment reminder.
        
        Args:
            user: CustomUser instance
            installment: Installment instance
            days_until_due: int - days until payment is due
        
        Returns:
            bool: True if sent successfully
        """
        plan = installment.plan
        product = plan.product
        
        if days_until_due <= 0:
            urgency = "🚨 GECİKMİŞ"
            color = "#dc2626"
            days_text = f"{abs(days_until_due)} gün gecikmiş"
        elif days_until_due <= 3:
            urgency = "⚠️ ACİL"
            color = "#f59e0b"
            days_text = f"{days_until_due} gün kaldı"
        else:
            urgency = "📅 Hatırlatma"
            color = "#3b82f6"
            days_text = f"{days_until_due} gün kaldı"
        
        subject = f'{urgency} Taksit Ödemesi - {product.name}'
        
        text_message = f"""
Merhaba {user.first_name or user.username},

{product.name} ürününüz için {installment.installment_number}. taksit ödemesi yaklaşıyor.

Taksit No: {installment.installment_number}/{plan.installment_count}
Tutar: {installment.amount}₺
Vade Tarihi: {installment.due_date}
Kalan Süre: {days_text}

Lütfen ödemenizi zamanında yapınız.

Saygılarımızla,
BekoSIRS Ekibi
        """
        
        html_message = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: {color}; color: white; padding: 20px; text-align: center; }}
        .content {{ padding: 30px; background-color: #f9fafb; }}
        .amount {{ font-size: 36px; font-weight: bold; color: {color}; text-align: center; margin: 20px 0; }}
        .info-box {{ background-color: white; padding: 20px; border-radius: 8px; margin: 20px 0; }}
        .progress {{ background-color: #e5e7eb; border-radius: 9999px; height: 8px; margin: 10px 0; }}
        .progress-bar {{ background-color: #16a34a; border-radius: 9999px; height: 8px; }}
        .footer {{ padding: 20px; text-align: center; color: #6b7280; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{urgency}</h1>
            <p>Taksit Ödemesi</p>
        </div>
        <div class="content">
            <p>Merhaba <strong>{user.first_name or user.username}</strong>,</p>
            
            <div class="amount">{installment.amount}₺</div>
            <p style="text-align: center;">{days_text}</p>
            
            <div class="info-box">
                <p><strong>Ürün:</strong> {product.name}</p>
                <p><strong>Taksit:</strong> {installment.installment_number}/{plan.installment_count}</p>
                <p><strong>Vade Tarihi:</strong> {installment.due_date}</p>
                
                <p><strong>İlerleme:</strong></p>
                <div class="progress">
                    <div class="progress-bar" style="width: {plan.progress_percentage}%;"></div>
                </div>
                <p><small>Toplam ödenen: {plan.paid_amount}₺ / {plan.total_amount}₺</small></p>
            </div>
            
            <p>Ödemenizi zamanında yaparak gecikme faizinden kaçının.</p>
        </div>
        <div class="footer">
            <p>© 2026 BekoSIRS. Tüm hakları saklıdır.</p>
        </div>
    </div>
</body>
</html>
        """
        
        try:
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_message.strip(),
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email]
            )
            email.attach_alternative(html_message, "text/html")
            email.send()
            return True
        except Exception as e:
            print(f"Error sending installment reminder email: {e}")
            return False
