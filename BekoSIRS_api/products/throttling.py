# products/throttling.py
"""
Custom Rate Limiting / Throttling for API Protection.

Provides different throttle rates for:
1. Anonymous users (strictest)
2. Authenticated users (normal)
3. Admin users (relaxed)
4. Sensitive endpoints (very strict)

Usage in views:
    from products.throttling import UserRateThrottle, LoginRateThrottle
    
    class MyView(APIView):
        throttle_classes = [UserRateThrottle]

Settings required:
    REST_FRAMEWORK = {
        'DEFAULT_THROTTLE_CLASSES': [
            'products.throttling.AnonRateThrottle',
            'products.throttling.UserRateThrottle',
        ],
        'DEFAULT_THROTTLE_RATES': {
            'anon': '20/minute',
            'user': '100/minute',
            'login': '5/minute',
            'password_reset': '3/hour',
            'admin': '500/minute',
            'burst': '10/second',
        }
    }
"""

from rest_framework.throttling import SimpleRateThrottle, AnonRateThrottle as BaseAnonThrottle
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)


class AnonRateThrottle(BaseAnonThrottle):
    """
    Throttle for anonymous (unauthenticated) users.
    Rate: 20 requests per minute
    """
    rate = '20/minute'
    scope = 'anon'


class UserRateThrottle(SimpleRateThrottle):
    """
    Throttle for authenticated users.
    Rate: 100 requests per minute
    """
    rate = '100/minute'
    scope = 'user'
    
    def get_cache_key(self, request, view):
        if request.user and request.user.is_authenticated:
            ident = request.user.pk
        else:
            ident = self.get_ident(request)
        return self.cache_format % {'scope': self.scope, 'ident': ident}


class AdminRateThrottle(SimpleRateThrottle):
    """
    Relaxed throttle for admin users.
    Rate: 500 requests per minute
    """
    rate = '500/minute'
    scope = 'admin'
    
    def get_cache_key(self, request, view):
        if request.user and request.user.is_authenticated:
            if hasattr(request.user, 'role') and request.user.role == 'admin':
                return None  # No throttling for admin
            ident = request.user.pk
        else:
            ident = self.get_ident(request)
        return self.cache_format % {'scope': self.scope, 'ident': ident}


class LoginRateThrottle(SimpleRateThrottle):
    """
    Strict throttle for login endpoint.
    Prevents brute force attacks.
    Rate: 5 attempts per minute
    """
    rate = '5/minute'
    scope = 'login'
    
    def get_cache_key(self, request, view):
        # Throttle by IP for login attempts
        return self.cache_format % {
            'scope': self.scope,
            'ident': self.get_ident(request)
        }
    
    def throttle_failure(self):
        """Log failed login attempt due to throttling."""
        logger.warning(f"Login throttled for IP: {self.key}")
        return False


class PasswordResetRateThrottle(SimpleRateThrottle):
    """
    Strict throttle for password reset.
    Prevents abuse of password reset emails.
    Rate: 3 requests per hour
    """
    rate = '3/hour'
    scope = 'password_reset'
    
    def get_cache_key(self, request, view):
        return self.cache_format % {
            'scope': self.scope,
            'ident': self.get_ident(request)
        }


class BurstRateThrottle(SimpleRateThrottle):
    """
    Burst protection throttle.
    Prevents rapid-fire requests.
    Rate: 10 requests per second
    """
    rate = '10/second'
    scope = 'burst'
    
    def get_cache_key(self, request, view):
        if request.user and request.user.is_authenticated:
            ident = request.user.pk
        else:
            ident = self.get_ident(request)
        return self.cache_format % {'scope': self.scope, 'ident': ident}


class SensitiveEndpointThrottle(SimpleRateThrottle):
    """
    Very strict throttle for sensitive operations.
    E.g., changing password, exporting data, deleting accounts.
    Rate: 3 requests per minute
    """
    rate = '3/minute'
    scope = 'sensitive'
    
    def get_cache_key(self, request, view):
        if request.user and request.user.is_authenticated:
            ident = request.user.pk
        else:
            ident = self.get_ident(request)
        return self.cache_format % {'scope': self.scope, 'ident': ident}


class ExportRateThrottle(SimpleRateThrottle):
    """
    Throttle for data export endpoints.
    Prevents resource-intensive export abuse.
    Rate: 5 exports per hour
    """
    rate = '5/hour'
    scope = 'export'
    
    def get_cache_key(self, request, view):
        if request.user and request.user.is_authenticated:
            ident = request.user.pk
        else:
            ident = self.get_ident(request)
        return self.cache_format % {'scope': self.scope, 'ident': ident}


# ==========================================
# Utility Functions
# ==========================================

def check_rate_limit(identifier: str, limit: int, window_seconds: int) -> tuple:
    """
    Manual rate limit check for custom scenarios.
    
    Args:
        identifier: Unique identifier (e.g., user_id, IP, email)
        limit: Maximum requests allowed
        window_seconds: Time window in seconds
        
    Returns:
        (allowed: bool, remaining: int, reset_at: int)
    
    Usage:
        allowed, remaining, reset_at = check_rate_limit(f"otp_{user_id}", 3, 300)
        if not allowed:
            return Response({"error": "Too many OTP requests"}, status=429)
    """
    cache_key = f"rate_limit:{identifier}"
    
    current = cache.get(cache_key, {'count': 0, 'started': None})
    
    import time
    now = time.time()
    
    if current['started'] is None or now - current['started'] > window_seconds:
        # New window
        current = {'count': 1, 'started': now}
        cache.set(cache_key, current, window_seconds)
        return True, limit - 1, int(now + window_seconds)
    
    if current['count'] >= limit:
        # Rate limit exceeded
        reset_at = int(current['started'] + window_seconds)
        return False, 0, reset_at
    
    # Increment counter
    current['count'] += 1
    cache.set(cache_key, current, window_seconds)
    remaining = limit - current['count']
    reset_at = int(current['started'] + window_seconds)
    
    return True, remaining, reset_at


def reset_rate_limit(identifier: str):
    """Reset rate limit for a specific identifier."""
    cache_key = f"rate_limit:{identifier}"
    cache.delete(cache_key)


# ==========================================
# Default Throttle Configuration
# ==========================================

DEFAULT_THROTTLE_RATES = {
    'anon': '20/minute',
    'user': '100/minute',
    'login': '5/minute',
    'password_reset': '3/hour',
    'admin': '500/minute',
    'burst': '10/second',
    'sensitive': '3/minute',
    'export': '5/hour',
}
