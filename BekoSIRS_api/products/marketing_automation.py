# products/marketing_automation.py
"""
Marketing Automation Service.

Automated marketing campaigns:
1. Birthday Campaign - Special discount before birthday
2. Churn Prevention - Re-engagement for inactive customers
3. Cross-sell Campaign - Complementary product suggestions
4. Review Request - Ask for review after purchase
5. Welcome Series - Welcome email for new customers

Usage:
    from products.marketing_automation import MarketingAutomationService
    
    service = MarketingAutomationService()
    service.run_birthday_campaign()
    service.run_churn_prevention()
"""

from django.utils import timezone
from django.db.models import Count, Max
from django.conf import settings
from datetime import timedelta, date
from typing import List, Dict, Optional
import logging
import random
import string

from .models import CustomUser, ProductOwnership, Notification
from .email_service import EmailService
from .customer_analytics_service import CustomerAnalyticsService

logger = logging.getLogger(__name__)


class MarketingAutomationService:
    """
    Marketing Automation Engine for customer engagement.
    
    Campaign Types:
    1. Birthday: 7 days before birthday, send discount code
    2. Churn Prevention: 90+ days inactive, send re-engagement email
    3. Cross-sell: Purchase → suggest complementary product
    4. Review Request: 14 days after purchase, ask for review
    5. Welcome: New registration, welcome email series
    
    Configuration via settings:
    - MARKETING_BIRTHDAY_DISCOUNT: Default 10%
    - MARKETING_CHURN_DAYS: Days of inactivity (default 90)
    - MARKETING_REVIEW_DAYS: Days after purchase (default 14)
    """
    
    # Campaign configuration
    BIRTHDAY_DAYS_BEFORE = 7
    BIRTHDAY_DISCOUNT_PERCENT = 10
    CHURN_THRESHOLD_DAYS = 90
    REVIEW_REQUEST_DAYS = 14
    COUPON_VALIDITY_DAYS = 30
    
    # Complementary product mapping (category -> suggested categories)
    CROSS_SELL_MAP = {
        'Buzdolabı': ['Buzdolabı Aksesuarları', 'Derin Dondurucu'],
        'Çamaşır Makinesi': ['Kurutma Makinesi', 'Ütü'],
        'Bulaşık Makinesi': ['Bulaşık Deterjanı'],
        'TV': ['Soundbar', 'TV Sehpası'],
        'Fırın': ['Ocak', 'Davlumbaz'],
        'Klima': ['Vantilatör', 'Hava Temizleyici'],
    }
    
    def __init__(self, dry_run: bool = False):
        """
        Initialize MarketingAutomationService.
        
        Args:
            dry_run: If True, don't actually send emails/create coupons
        """
        self.dry_run = dry_run
        self.today = timezone.now().date()
        self.results = {
            'emails_sent': 0,
            'notifications_created': 0,
            'coupons_generated': 0,
            'errors': []
        }
    
    def run_all_campaigns(self) -> Dict:
        """Run all marketing campaigns."""
        results = {
            'birthday': self.run_birthday_campaign(),
            'churn_prevention': self.run_churn_prevention(),
            'review_request': self.run_review_request(),
            'welcome': self.run_welcome_campaign(),
        }
        return results
    
    def run_birthday_campaign(self) -> Dict:
        """
        Send birthday discount to customers with upcoming birthdays.
        
        Sends email 7 days before birthday with a discount coupon.
        """
        logger.info("Running Birthday Campaign...")
        
        target_date = self.today + timedelta(days=self.BIRTHDAY_DAYS_BEFORE)
        
        # Find customers - note: date_of_birth may not exist in all models
        # For now, return empty result since we don't have date_of_birth field
        customers = CustomUser.objects.filter(
            role='customer',
            is_active=True,
            notify_general=True  # Using existing field
        )
        
        # Since date_of_birth doesn't exist in current model, return empty for now
        eligible = []
        # If you add date_of_birth to CustomUser model, uncomment below:
        # for customer in customers:
        #     if hasattr(customer, 'date_of_birth') and customer.date_of_birth:
        #         if (customer.date_of_birth.month == target_date.month and 
        #             customer.date_of_birth.day == target_date.day):
        #             eligible.append(customer)
        
        sent_count = 0
        for customer in eligible:
            try:
                coupon = self._generate_coupon_code('BDAY')
                
                if not self.dry_run:
                    # Send email
                    self._send_birthday_email(customer, coupon)
                    
                    # Create notification
                    Notification.objects.create(
                        user=customer,
                        notification_type='general',
                        title='🎂 Doğum Günü Hediyeniz!',
                        message=f'Doğum gününüz için %{self.BIRTHDAY_DISCOUNT_PERCENT} indirim kuponu: {coupon}'
                    )
                    self.results['notifications_created'] += 1
                
                sent_count += 1
                logger.info(f"Birthday email sent to {customer.email}")
                
            except Exception as e:
                logger.error(f"Birthday email failed for {customer.email}: {e}")
                self.results['errors'].append(str(e))
        
        return {
            'campaign': 'birthday',
            'eligible_customers': len(eligible),
            'emails_sent': sent_count,
            'dry_run': self.dry_run
        }
    
    def run_churn_prevention(self) -> Dict:
        """
        Send re-engagement email to inactive customers.
        
        Targets customers who haven't purchased in CHURN_THRESHOLD_DAYS.
        """
        logger.info("Running Churn Prevention Campaign...")
        
        cutoff_date = self.today - timedelta(days=self.CHURN_THRESHOLD_DAYS)
        
        # Find customers with last purchase before cutoff
        inactive_customers = []
        
        customers = CustomUser.objects.filter(
            role='customer',
            is_active=True,
            notify_general=True  # Using existing field
        )
        
        for customer in customers:
            last_purchase = ProductOwnership.objects.filter(
                customer=customer
            ).order_by('-purchase_date').first()
            
            if last_purchase and last_purchase.purchase_date <= cutoff_date:
                # Also check that we haven't sent churn email recently
                recent_notification = Notification.objects.filter(
                    user=customer,
                    title__contains='Özledik',
                    created_at__gte=timezone.now() - timedelta(days=30)
                ).exists()
                
                if not recent_notification:
                    days_inactive = (self.today - last_purchase.purchase_date).days
                    inactive_customers.append({
                        'customer': customer,
                        'days_inactive': days_inactive,
                        'last_purchase': last_purchase
                    })
        
        sent_count = 0
        for item in inactive_customers:
            customer = item['customer']
            days = item['days_inactive']
            
            try:
                coupon = self._generate_coupon_code('WELCOME')
                
                if not self.dry_run:
                    # Send email
                    self._send_churn_email(customer, days, coupon)
                    
                    # Create notification
                    Notification.objects.create(
                        user=customer,
                        notification_type='general',
                        title='💔 Sizi Özledik!',
                        message=f'{days} gündür sizi görmedik. Size özel %15 indirim kuponu: {coupon}'
                    )
                    self.results['notifications_created'] += 1
                
                sent_count += 1
                logger.info(f"Churn prevention email sent to {customer.email}")
                
            except Exception as e:
                logger.error(f"Churn email failed for {customer.email}: {e}")
                self.results['errors'].append(str(e))
        
        return {
            'campaign': 'churn_prevention',
            'eligible_customers': len(inactive_customers),
            'emails_sent': sent_count,
            'dry_run': self.dry_run
        }
    
    def run_review_request(self) -> Dict:
        """
        Send review request to customers who purchased recently.
        
        Targets customers REVIEW_REQUEST_DAYS after purchase.
        """
        logger.info("Running Review Request Campaign...")
        
        target_date = self.today - timedelta(days=self.REVIEW_REQUEST_DAYS)
        
        # Find purchases from target date
        purchases = ProductOwnership.objects.filter(
            purchase_date=target_date
        ).select_related('customer', 'product')
        
        sent_count = 0
        for ownership in purchases:
            customer = ownership.customer
            product = ownership.product
            
            if not customer.notify_general:
                continue
            
            # Check if review already exists
            from .models import Review
            existing_review = Review.objects.filter(
                customer=customer,
                product=product
            ).exists()
            
            if existing_review:
                continue
            
            try:
                if not self.dry_run:
                    # Send email
                    self._send_review_request_email(customer, product)
                    
                    # Create notification
                    Notification.objects.create(
                        user=customer,
                        notification_type='general',
                        title='⭐ Ürünümüzü değerlendirir misiniz?',
                        message=f'{product.name} hakkındaki düşüncelerinizi merak ediyoruz!',
                        related_product=product
                    )
                    self.results['notifications_created'] += 1
                
                sent_count += 1
                logger.info(f"Review request sent to {customer.email} for {product.name}")
                
            except Exception as e:
                logger.error(f"Review request failed for {customer.email}: {e}")
                self.results['errors'].append(str(e))
        
        return {
            'campaign': 'review_request',
            'eligible_customers': purchases.count(),
            'emails_sent': sent_count,
            'dry_run': self.dry_run
        }
    
    def run_welcome_campaign(self) -> Dict:
        """
        Send welcome email to new customers.
        
        Targets customers who registered today.
        """
        logger.info("Running Welcome Campaign...")
        
        # Find customers who registered today
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        
        new_customers = CustomUser.objects.filter(
            role='customer',
            date_joined__gte=today_start,
            date_joined__lt=today_end
        )
        
        sent_count = 0
        for customer in new_customers:
            try:
                if not self.dry_run:
                    # Send welcome email
                    EmailService.send_welcome_email(customer)
                    
                    # Create welcome notification
                    Notification.objects.create(
                        user=customer,
                        notification_type='general',
                        title='🎉 BekoSIRS\'e Hoş Geldiniz!',
                        message='Ailemize katıldığınız için teşekkür ederiz. Ürünlerimizi keşfedin!'
                    )
                    self.results['notifications_created'] += 1
                
                sent_count += 1
                logger.info(f"Welcome email sent to {customer.email}")
                
            except Exception as e:
                logger.error(f"Welcome email failed for {customer.email}: {e}")
                self.results['errors'].append(str(e))
        
        return {
            'campaign': 'welcome',
            'new_customers': new_customers.count(),
            'emails_sent': sent_count,
            'dry_run': self.dry_run
        }
    
    def _generate_coupon_code(self, prefix: str = 'BEKO') -> str:
        """Generate unique coupon code."""
        random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        return f"{prefix}{random_part}"
    
    def _send_birthday_email(self, customer: CustomUser, coupon: str):
        """Send birthday discount email."""
        subject = f"🎂 Doğum Günü Hediyeniz Hazır, {customer.first_name}!"
        
        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%); padding: 40px; border-radius: 12px;">
            <div style="text-align: center; margin-bottom: 30px;">
                <h1 style="color: white; font-size: 32px; margin: 0;">🎂 Mutlu Yıllar!</h1>
            </div>
            <div style="background: white; padding: 30px; border-radius: 8px;">
                <p style="color: #333; font-size: 18px;">Merhaba {customer.first_name or 'Değerli Müşterimiz'},</p>
                <p style="color: #666; font-size: 16px;">Doğum gününüzü kutluyor ve size özel bir hediye sunuyoruz!</p>
                
                <div style="background: #fef3c7; padding: 20px; border-radius: 8px; text-align: center; margin: 20px 0;">
                    <p style="color: #92400e; margin: 0; font-size: 14px;">İndirim Kuponu</p>
                    <p style="color: #d97706; font-size: 32px; font-weight: bold; margin: 10px 0;">{coupon}</p>
                    <p style="color: #92400e; font-size: 24px; margin: 0;">%{self.BIRTHDAY_DISCOUNT_PERCENT} İNDİRİM</p>
                </div>
                
                <p style="color: #666; font-size: 14px;">Bu kupon {self.COUPON_VALIDITY_DAYS} gün geçerlidir.</p>
                
                <a href="{getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')}" 
                   style="display: inline-block; background: #f59e0b; color: white; padding: 15px 40px; 
                          text-decoration: none; border-radius: 8px; font-weight: bold; margin-top: 20px;">
                    Alışverişe Başla
                </a>
            </div>
        </div>
        """
        
        EmailService._send_email(
            subject=subject,
            message=f"Doğum günü kuponunuz: {coupon}",
            recipient_list=[customer.email],
            html_message=html_content
        )
        self.results['emails_sent'] += 1
        self.results['coupons_generated'] += 1
    
    def _send_churn_email(self, customer: CustomUser, days: int, coupon: str):
        """Send churn prevention email."""
        subject = f"💔 Sizi Özledik, {customer.first_name}!"
        
        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #f3f4f6; padding: 40px; border-radius: 12px;">
            <div style="text-align: center; margin-bottom: 30px;">
                <h1 style="color: #ef4444; font-size: 28px; margin: 0;">💔 Sizi Özledik!</h1>
            </div>
            <div style="background: white; padding: 30px; border-radius: 8px;">
                <p style="color: #333; font-size: 18px;">Merhaba {customer.first_name or 'Değerli Müşterimiz'},</p>
                <p style="color: #666; font-size: 16px;">{days} gündür sizi göremedik. Umarız her şey yolundadır!</p>
                <p style="color: #666; font-size: 16px;">Sizi geri kazanmak için özel bir teklif hazırladık:</p>
                
                <div style="background: #fef2f2; padding: 20px; border-radius: 8px; text-align: center; margin: 20px 0;">
                    <p style="color: #ef4444; font-size: 24px; font-weight: bold; margin: 0;">%15 İNDİRİM</p>
                    <p style="color: #dc2626; font-size: 20px; margin: 10px 0;">Kupon: {coupon}</p>
                </div>
                
                <p style="color: #666; font-size: 14px;">Bu kupon yalnızca siz için, {self.COUPON_VALIDITY_DAYS} gün geçerli!</p>
                
                <a href="{getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')}" 
                   style="display: inline-block; background: #ef4444; color: white; padding: 15px 40px; 
                          text-decoration: none; border-radius: 8px; font-weight: bold; margin-top: 20px;">
                    Yeni Ürünleri Keşfet
                </a>
            </div>
        </div>
        """
        
        EmailService._send_email(
            subject=subject,
            message=f"Sizi özledik! %15 indirim kuponunuz: {coupon}",
            recipient_list=[customer.email],
            html_message=html_content
        )
        self.results['emails_sent'] += 1
        self.results['coupons_generated'] += 1
    
    def _send_review_request_email(self, customer: CustomUser, product):
        """Send review request email."""
        subject = f"⭐ {product.name} hakkında ne düşünüyorsunuz?"
        
        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #f0fdf4; padding: 40px; border-radius: 12px;">
            <div style="text-align: center; margin-bottom: 30px;">
                <h1 style="color: #16a34a; font-size: 24px; margin: 0;">⭐ Görüşleriniz Bizim İçin Önemli!</h1>
            </div>
            <div style="background: white; padding: 30px; border-radius: 8px;">
                <p style="color: #333; font-size: 16px;">Merhaba {customer.first_name or 'Değerli Müşterimiz'},</p>
                <p style="color: #666; font-size: 15px;">
                    {self.REVIEW_REQUEST_DAYS} gün önce aldığınız <strong>{product.name}</strong> ürünümüz 
                    hakkındaki düşüncelerinizi merak ediyoruz.
                </p>
                <p style="color: #666; font-size: 15px;">
                    Değerlendirmeniz diğer müşterilerimize yardımcı olacak ve ürünlerimizi 
                    geliştirmemize katkı sağlayacaktır.
                </p>
                
                <a href="{getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')}/products/{product.id}" 
                   style="display: inline-block; background: #16a34a; color: white; padding: 15px 40px; 
                          text-decoration: none; border-radius: 8px; font-weight: bold; margin-top: 20px;">
                    Değerlendirme Yap
                </a>
            </div>
        </div>
        """
        
        EmailService._send_email(
            subject=subject,
            message=f"Lütfen {product.name} hakkındaki düşüncelerinizi paylaşın.",
            recipient_list=[customer.email],
            html_message=html_content
        )
        self.results['emails_sent'] += 1


# Helper function for management command
def run_marketing_campaigns(campaign_type: str = None, dry_run: bool = False) -> Dict:
    """
    Run marketing campaigns.
    
    Args:
        campaign_type: 'birthday', 'churn', 'review', 'welcome', or None for all
        dry_run: If True, don't send actual emails
        
    Returns:
        Campaign results
    """
    service = MarketingAutomationService(dry_run=dry_run)
    
    if campaign_type == 'birthday':
        return service.run_birthday_campaign()
    elif campaign_type == 'churn':
        return service.run_churn_prevention()
    elif campaign_type == 'review':
        return service.run_review_request()
    elif campaign_type == 'welcome':
        return service.run_welcome_campaign()
    else:
        return service.run_all_campaigns()
