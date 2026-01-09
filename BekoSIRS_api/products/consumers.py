# products/consumers.py
"""
WebSocket Consumers for Real-time Notifications.

Provides WebSocket connections for:
1. User notifications (personal)
2. Admin dashboard updates
3. Service request status changes

Usage (Frontend):
    const ws = new WebSocket('ws://localhost:8000/ws/notifications/');
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log('Notification:', data);
    };

Requires:
    pip install channels channels-redis
"""

import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone

logger = logging.getLogger(__name__)


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for user-specific notifications.
    
    Each user joins their own group: notification_user_{user_id}
    Admins also join: notification_admin
    """
    
    async def connect(self):
        """Handle WebSocket connection."""
        self.user = self.scope.get('user')
        self.groups = []
        
        if self.user and self.user.is_authenticated:
            # User-specific notifications
            self.user_group = f'notification_user_{self.user.id}'
            await self.channel_layer.group_add(self.user_group, self.channel_name)
            self.groups.append(self.user_group)
            
            # Admin group
            if hasattr(self.user, 'role') and self.user.role == 'admin':
                await self.channel_layer.group_add('notification_admin', self.channel_name)
                self.groups.append('notification_admin')
            
            # Seller group
            if hasattr(self.user, 'role') and self.user.role == 'seller':
                await self.channel_layer.group_add('notification_seller', self.channel_name)
                self.groups.append('notification_seller')
            
            await self.accept()
            
            # Send connection confirmation
            await self.send(text_data=json.dumps({
                'type': 'connection_established',
                'message': 'Connected to notification service',
                'user_id': self.user.id,
                'groups': self.groups
            }))
            
            logger.info(f"WebSocket connected: User {self.user.id}")
        else:
            # Reject unauthenticated connections
            await self.close()
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        for group in self.groups:
            await self.channel_layer.group_discard(group, self.channel_name)
        
        if hasattr(self, 'user') and self.user:
            logger.info(f"WebSocket disconnected: User {self.user.id}")
    
    async def receive(self, text_data):
        """Handle incoming messages from client."""
        try:
            data = json.loads(text_data)
            message_type = data.get('type', 'unknown')
            
            if message_type == 'ping':
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'timestamp': timezone.now().isoformat()
                }))
            
            elif message_type == 'mark_read':
                notification_id = data.get('notification_id')
                if notification_id:
                    await self.mark_notification_read(notification_id)
            
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON'
            }))
    
    # ==========================================
    # Event Handlers (called from channel layer)
    # ==========================================
    
    async def notification_message(self, event):
        """Handle notification message from channel layer."""
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'data': event['data']
        }))
    
    async def order_update(self, event):
        """Handle order/sale notification."""
        await self.send(text_data=json.dumps({
            'type': 'order_update',
            'data': event['data']
        }))
    
    async def service_update(self, event):
        """Handle service request status update."""
        await self.send(text_data=json.dumps({
            'type': 'service_update',
            'data': event['data']
        }))
    
    async def stock_alert(self, event):
        """Handle low stock alert."""
        await self.send(text_data=json.dumps({
            'type': 'stock_alert',
            'data': event['data']
        }))
    
    async def dashboard_update(self, event):
        """Handle dashboard metrics update."""
        await self.send(text_data=json.dumps({
            'type': 'dashboard_update',
            'data': event['data']
        }))
    
    # ==========================================
    # Database Operations
    # ==========================================
    
    @database_sync_to_async
    def mark_notification_read(self, notification_id):
        """Mark a notification as read."""
        from products.models import Notification
        try:
            Notification.objects.filter(
                id=notification_id,
                user=self.user
            ).update(is_read=True)
            return True
        except Exception as e:
            logger.error(f"Failed to mark notification read: {e}")
            return False


class DashboardConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for admin dashboard real-time updates.
    
    Broadcasts:
    - New orders
    - Service request updates
    - Stock alerts
    - Key metrics changes
    """
    
    async def connect(self):
        """Handle dashboard WebSocket connection."""
        self.user = self.scope.get('user')
        
        if self.user and self.user.is_authenticated:
            if hasattr(self.user, 'role') and self.user.role in ['admin', 'seller']:
                await self.channel_layer.group_add('dashboard_updates', self.channel_name)
                await self.accept()
                
                # Send initial dashboard data
                dashboard_data = await self.get_dashboard_summary()
                await self.send(text_data=json.dumps({
                    'type': 'dashboard_init',
                    'data': dashboard_data
                }))
                
                logger.info(f"Dashboard WebSocket connected: User {self.user.id}")
            else:
                await self.close()
        else:
            await self.close()
    
    async def disconnect(self, close_code):
        """Handle dashboard WebSocket disconnection."""
        await self.channel_layer.group_discard('dashboard_updates', self.channel_name)
    
    async def dashboard_metric(self, event):
        """Handle metric update."""
        await self.send(text_data=json.dumps({
            'type': 'metric_update',
            'data': event['data']
        }))
    
    async def new_order(self, event):
        """Handle new order notification."""
        await self.send(text_data=json.dumps({
            'type': 'new_order',
            'data': event['data']
        }))
    
    async def new_service_request(self, event):
        """Handle new service request."""
        await self.send(text_data=json.dumps({
            'type': 'new_service_request',
            'data': event['data']
        }))
    
    @database_sync_to_async
    def get_dashboard_summary(self):
        """Get initial dashboard summary."""
        from products.models import ProductOwnership, ServiceRequest, CustomUser
        from django.db.models import Sum
        
        today = timezone.now().date()
        
        return {
            'today_sales': ProductOwnership.objects.filter(
                purchase_date=today
            ).count(),
            'today_revenue': float(
                ProductOwnership.objects.filter(
                    purchase_date=today
                ).aggregate(total=Sum('product__price'))['total'] or 0
            ),
            'pending_services': ServiceRequest.objects.filter(
                status__in=['pending', 'in_queue']
            ).count(),
            'total_customers': CustomUser.objects.filter(role='customer').count()
        }
