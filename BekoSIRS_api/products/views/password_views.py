# products/views/password_views.py
"""
Password reset views.
"""

import logging
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from django.utils import timezone
from django.conf import settings

from products.models import CustomUser, PasswordResetToken
from products.serializers import PasswordResetRequestSerializer, PasswordResetConfirmSerializer

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([AllowAny])
def password_reset_request(request):
    """
    POST /api/password-reset/
    Request a password reset link via email.
    """
    serializer = PasswordResetRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    email = serializer.validated_data['email']

    try:
        user = CustomUser.objects.get(email=email)
        
        # Invalidate any existing tokens
        PasswordResetToken.objects.filter(user=user, is_used=False).update(is_used=True)
        
        # Create new token
        token = PasswordResetToken.create_for_user(user)
        
        # Send email
        try:
            from products.email_service import EmailService
            EmailService.send_password_reset_email(user, token.token)
        except Exception as e:
            logger.error(f"Failed to send password reset email to {user.email}: {e}", exc_info=True)
            # Still return success to prevent email enumeration

        # Build response
        response_data = {
            'success': True,
            'message': 'Şifre sıfırlama bağlantısı e-posta adresinize gönderildi.',
        }

        # SECURITY: Only include token in DEBUG mode for testing
        # NEVER expose tokens in production
        if settings.DEBUG:
            response_data['debug_token'] = str(token.token)

        return Response(response_data)
    except CustomUser.DoesNotExist:
        # Don't reveal that email doesn't exist
        return Response({
            'success': True,
            'message': 'E-posta adresiniz kayıtlıysa, şifre sıfırlama bağlantısı gönderildi.'
        })


@api_view(['POST'])
@permission_classes([AllowAny])
def password_reset_confirm(request):
    """
    POST /api/password-reset/confirm/
    Confirm password reset with token.
    """
    serializer = PasswordResetConfirmSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    token_str = serializer.validated_data['token']
    new_password = serializer.validated_data['new_password']
    confirm_password = serializer.validated_data['confirm_password']

    if new_password != confirm_password:
        return Response({
            'success': False,
            'error': 'Şifreler eşleşmiyor.'
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        token = PasswordResetToken.objects.get(token=token_str)
        
        if token.is_used:
            return Response({
                'success': False,
                'error': 'Bu şifre sıfırlama bağlantısı zaten kullanılmış.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if token.expires_at < timezone.now():
            return Response({
                'success': False,
                'error': 'Şifre sıfırlama bağlantısının süresi dolmuş.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Reset password
        user = token.user
        user.set_password(new_password)
        user.save()
        
        # Mark token as used
        token.is_used = True
        token.save()
        
        return Response({
            'success': True,
            'message': 'Şifreniz başarıyla değiştirildi.'
        })
    except PasswordResetToken.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Geçersiz şifre sıfırlama bağlantısı.'
        }, status=status.HTTP_400_BAD_REQUEST)
