# products/websocket_utils.py
"""
WebSocket Utility Functions for Sending Notifications.

Provides helper functions to send messages through channel layer
from anywhere in the Django application (views, signals, tasks).

Usage:
    from products.websocket_utils import (
        send_user_notification,
        send_admin_alert,
        send_dashboard_update
    )
    
    # Send to specific user
    await send_user_notification(user_id, {
        'title': 'Yeni Bildirim',
        'message': 'Siparişiniz hazırlandı'
    })
    
    # Send to all admins
    await send_admin_alert({
        'type': 'low_stock',
        'product': 'Beko Buzdolabı',
        'stock': 2
    })
"""

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


def get_channel():
    """Get channel layer instance."""
    return get_channel_layer()


# ==========================================
# Sync Functions (for use in regular Django code)
# ==========================================

def send_user_notification(user_id: int, data: dict):
    """
    Send notification to a specific user.
    
    Args:
        user_id: Target user ID
        data: Notification data dict
    """
    channel_layer = get_channel()
    if not channel_layer:
        logger.warning("Channel layer not configured")
        return False
    
    group_name = f'notification_user_{user_id}'
    
    message = {
        'type': 'notification_message',
        'data': {
            **data,
            'timestamp': timezone.now().isoformat()
        }
    }
    
    try:
        async_to_sync(channel_layer.group_send)(group_name, message)
        logger.info(f"Notification sent to user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to send notification to user {user_id}: {e}")
        return False


def send_admin_alert(data: dict):
    """
    Send alert to all admin users.
    
    Args:
        data: Alert data dict
    """
    channel_layer = get_channel()
    if not channel_layer:
        logger.warning("Channel layer not configured")
        return False
    
    message = {
        'type': 'notification_message',
        'data': {
            **data,
            'timestamp': timezone.now().isoformat(),
            'is_admin_alert': True
        }
    }
    
    try:
        async_to_sync(channel_layer.group_send)('notification_admin', message)
        logger.info("Alert sent to admin group")
        return True
    except Exception as e:
        logger.error(f"Failed to send admin alert: {e}")
        return False


def send_seller_notification(data: dict):
    """Send notification to all sellers."""
    channel_layer = get_channel()
    if not channel_layer:
        return False
    
    message = {
        'type': 'notification_message',
        'data': {
            **data,
            'timestamp': timezone.now().isoformat()
        }
    }
    
    try:
        async_to_sync(channel_layer.group_send)('notification_seller', message)
        return True
    except Exception as e:
        logger.error(f"Failed to send seller notification: {e}")
        return False


def send_dashboard_update(data: dict):
    """
    Send update to all connected dashboard clients.
    
    Args:
        data: Update data dict
    """
    channel_layer = get_channel()
    if not channel_layer:
        return False
    
    message = {
        'type': 'dashboard_metric',
        'data': {
            **data,
            'timestamp': timezone.now().isoformat()
        }
    }
    
    try:
        async_to_sync(channel_layer.group_send)('dashboard_updates', message)
        return True
    except Exception as e:
        logger.error(f"Failed to send dashboard update: {e}")
        return False


def broadcast_new_order(order_data: dict):
    """Broadcast new order to admin/seller dashboards."""
    channel_layer = get_channel()
    if not channel_layer:
        return False
    
    message = {
        'type': 'new_order',
        'data': {
            **order_data,
            'timestamp': timezone.now().isoformat()
        }
    }
    
    try:
        async_to_sync(channel_layer.group_send)('dashboard_updates', message)
        async_to_sync(channel_layer.group_send)('notification_admin', message)
        async_to_sync(channel_layer.group_send)('notification_seller', message)
        return True
    except Exception as e:
        logger.error(f"Failed to broadcast new order: {e}")
        return False


def broadcast_service_request(service_data: dict):
    """Broadcast new service request."""
    channel_layer = get_channel()
    if not channel_layer:
        return False
    
    message = {
        'type': 'new_service_request',
        'data': {
            **service_data,
            'timestamp': timezone.now().isoformat()
        }
    }
    
    try:
        async_to_sync(channel_layer.group_send)('dashboard_updates', message)
        return True
    except Exception as e:
        logger.error(f"Failed to broadcast service request: {e}")
        return False


def broadcast_stock_alert(product_id: int, product_name: str, stock: int):
    """Broadcast low stock alert."""
    channel_layer = get_channel()
    if not channel_layer:
        return False
    
    message = {
        'type': 'stock_alert',
        'data': {
            'product_id': product_id,
            'product_name': product_name,
            'current_stock': stock,
            'alert_type': 'low_stock',
            'timestamp': timezone.now().isoformat()
        }
    }
    
    try:
        async_to_sync(channel_layer.group_send)('notification_admin', message)
        async_to_sync(channel_layer.group_send)('notification_seller', message)
        return True
    except Exception as e:
        logger.error(f"Failed to broadcast stock alert: {e}")
        return False


# ==========================================
# Async Functions (for use in async code)
# ==========================================

async def async_send_user_notification(user_id: int, data: dict):
    """Async version of send_user_notification."""
    channel_layer = get_channel()
    if not channel_layer:
        return False
    
    group_name = f'notification_user_{user_id}'
    
    await channel_layer.group_send(group_name, {
        'type': 'notification_message',
        'data': {
            **data,
            'timestamp': timezone.now().isoformat()
        }
    })
    return True


async def async_send_admin_alert(data: dict):
    """Async version of send_admin_alert."""
    channel_layer = get_channel()
    if not channel_layer:
        return False
    
    await channel_layer.group_send('notification_admin', {
        'type': 'notification_message',
        'data': {
            **data,
            'timestamp': timezone.now().isoformat()
        }
    })
    return True
