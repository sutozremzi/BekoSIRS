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
