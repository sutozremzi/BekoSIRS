# products/routing.py
"""
WebSocket URL Routing for Django Channels.

Maps WebSocket URLs to consumers:
- /ws/notifications/ - User notifications
- /ws/dashboard/ - Admin dashboard updates
"""

from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/notifications/$', consumers.NotificationConsumer.as_asgi()),
    re_path(r'ws/dashboard/$', consumers.DashboardConsumer.as_asgi()),
]
