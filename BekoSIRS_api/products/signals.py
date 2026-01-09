# products/signals.py
"""
Django signals for automatic email notifications.

Triggers:
- Product price drop → Notify wishlist users
- Product restock → Notify wishlist users
- Service request status change → Notify customer
"""

import logging
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.db import transaction

from .models import Product, ServiceRequest, WishlistItem, Notification
from .email_service import EmailService

logger = logging.getLogger(__name__)


# ============================================
# Product Price Drop & Restock Signals
# ============================================

@receiver(pre_save, sender=Product)
def track_product_changes(sender, instance, **kwargs):
    """
    Track price and stock changes before save.
    Stores old values in instance attributes for post_save comparison.
    """
    if instance.pk:
        try:
            old_product = Product.objects.get(pk=instance.pk)
            instance._old_price = old_product.price
            instance._old_stock = old_product.stock
        except Product.DoesNotExist:
            instance._old_price = None
            instance._old_stock = None
    else:
        instance._old_price = None
        instance._old_stock = None


@receiver(post_save, sender=Product)
def notify_price_drop(sender, instance, created, **kwargs):
    """
    Send price drop notification to wishlist users.
    Only triggers if:
    - Product is not newly created
    - New price is lower than old price
    - User has notify_on_price_drop enabled
    """
    if created:
        return
    
    old_price = getattr(instance, '_old_price', None)
    if old_price is None:
        return
    
    # Check if price dropped
    if instance.price >= old_price:
        return
    
    logger.info(f"Price drop detected for {instance.name}: {old_price} → {instance.price}")
    
    # Find wishlist items with notification enabled
    wishlist_items = WishlistItem.objects.filter(
        product=instance,
        notify_on_price_drop=True
    ).select_related('wishlist__customer')
    
    for item in wishlist_items:
        customer = item.wishlist.customer
        
        # Create in-app notification
        Notification.objects.create(
            user=customer,
            notification_type='price_drop',
            title=f'🔥 Fiyat Düştü! {instance.name}',
            message=f'{instance.name} ürününün fiyatı {old_price}₺\'den {instance.price}₺\'ye düştü!',
            related_product=instance
        )
        
        # Send email (async in production)
        try:
            EmailService.send_price_drop_notification(
                customer, instance, old_price, instance.price
            )
            logger.info(f"Price drop email sent to {customer.email}")
        except Exception as e:
            logger.error(f"Failed to send price drop email to {customer.email}: {e}")


@receiver(post_save, sender=Product)
def notify_restock(sender, instance, created, **kwargs):
    """
    Send restock notification to wishlist users.
    Only triggers if:
    - Product is not newly created
    - Old stock was 0
    - New stock is > 0
    - User has notify_on_restock enabled
    """
    if created:
        return
    
    old_stock = getattr(instance, '_old_stock', None)
    if old_stock is None:
        return
    
    # Check if restocked (was 0, now > 0)
    if old_stock != 0 or instance.stock <= 0:
        return
    
    logger.info(f"Restock detected for {instance.name}: 0 → {instance.stock}")
    
    # Find wishlist items with notification enabled
    wishlist_items = WishlistItem.objects.filter(
        product=instance,
        notify_on_restock=True
    ).select_related('wishlist__customer')
    
    for item in wishlist_items:
        customer = item.wishlist.customer
        
        # Create in-app notification
        Notification.objects.create(
            user=customer,
            notification_type='restock',
            title=f'✅ Stok Geldi! {instance.name}',
            message=f'{instance.name} ürünü tekrar stokta! Şu an {instance.stock} adet mevcut.',
            related_product=instance
        )
        
        # Send email
        try:
            EmailService.send_restock_notification(customer, instance)
            logger.info(f"Restock email sent to {customer.email}")
        except Exception as e:
            logger.error(f"Failed to send restock email to {customer.email}: {e}")


# ============================================
# Service Request Status Change Signal
# ============================================

@receiver(pre_save, sender=ServiceRequest)
def track_service_status_change(sender, instance, **kwargs):
    """
    Track service request status changes before save.
    """
    if instance.pk:
        try:
            old_request = ServiceRequest.objects.get(pk=instance.pk)
            instance._old_status = old_request.status
        except ServiceRequest.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


@receiver(post_save, sender=ServiceRequest)
def notify_service_status_change(sender, instance, created, **kwargs):
    """
    Send notification when service request status changes.
    """
    old_status = getattr(instance, '_old_status', None)
    
    # Skip if newly created (will have separate logic if needed)
    if created:
        return
    
    # Skip if status didn't change
    if old_status is None or old_status == instance.status:
        return
    
    logger.info(f"Service request #{instance.id} status changed: {old_status} → {instance.status}")
    
    customer = instance.customer
    
    # Status display names
    status_display = {
        'pending': 'Beklemede',
        'in_queue': 'Sırada',
        'in_progress': 'İşlemde',
        'completed': 'Tamamlandı',
        'cancelled': 'İptal Edildi'
    }
    
    new_display = status_display.get(instance.status, instance.status)
    
    # Create in-app notification
    Notification.objects.create(
        user=customer,
        notification_type='service_update',
        title=f'🔧 Servis Talebi Güncellendi',
        message=f'#{instance.id} numaralı servis talebinizin durumu "{new_display}" olarak güncellendi.',
        related_service_request=instance
    )
    
    # Send email
    try:
        EmailService.send_service_update_notification(
            customer, instance, old_status, instance.status
        )
        logger.info(f"Service update email sent to {customer.email}")
    except Exception as e:
        logger.error(f"Failed to send service update email to {customer.email}: {e}")
