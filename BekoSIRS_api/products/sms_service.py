# products/sms_service.py
"""
SMS Notification Service using Twilio.

Provides SMS notifications for:
1. Service status updates
2. Delivery notifications
3. Payment reminders
4. Security codes (2FA/OTP)
5. Marketing campaigns

Usage:
    from products.sms_service import SMSService
    
    sms = SMSService()
    sms.send_service_update(customer, "Servis talebiniz tamamlandı!")
    sms.send_otp(customer, "123456")

Environment Variables Required:
    TWILIO_ACCOUNT_SID=your_account_sid
    TWILIO_AUTH_TOKEN=your_auth_token
    TWILIO_PHONE_NUMBER=+1234567890
"""

import os
import logging
from typing import Optional, Dict, List
from django.conf import settings

logger = logging.getLogger(__name__)


class SMSService:
    """
    SMS Service using Twilio API.
    
    Falls back to logging if Twilio is not configured.
    """
    
    def __init__(self):
        self.account_sid = os.getenv('TWILIO_ACCOUNT_SID', '')
        self.auth_token = os.getenv('TWILIO_AUTH_TOKEN', '')
        self.from_number = os.getenv('TWILIO_PHONE_NUMBER', '')
        self.client = None
        self.is_configured = False
        
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Twilio client if credentials are available."""
        if self.account_sid and self.auth_token and self.from_number:
            try:
                from twilio.rest import Client
                self.client = Client(self.account_sid, self.auth_token)
                self.is_configured = True
                logger.info("Twilio SMS service initialized successfully")
            except ImportError:
                logger.warning("Twilio library not installed. Run: pip install twilio")
            except Exception as e:
                logger.error(f"Failed to initialize Twilio client: {e}")
        else:
            logger.warning("Twilio credentials not configured. SMS will be logged only.")
    
    def send_sms(self, to_number: str, message: str, 
                 log_for_audit: bool = True) -> Dict:
        """
        Send an SMS message.
        
        Args:
            to_number: Recipient phone number (E.164 format: +905551234567)
            message: SMS content (max 1600 chars, 160 per segment)
            log_for_audit: Whether to log this SMS for audit
            
        Returns:
            Dict with success status and message SID or error
        """
        # Validate phone number format
        if not to_number or not to_number.startswith('+'):
            return {
                'success': False,
                'error': 'Geçersiz telefon numarası formatı. +90... şeklinde olmalı.'
            }
        
        # Truncate message if too long
        if len(message) > 1600:
            message = message[:1597] + '...'
        
        if self.is_configured and self.client:
            try:
                sms = self.client.messages.create(
                    body=message,
                    from_=self.from_number,
                    to=to_number
                )
                
                logger.info(f"SMS sent to {to_number[-4:]}: SID={sms.sid}")
                
                if log_for_audit:
                    self._log_sms(to_number, message, sms.sid, 'sent')
                
                return {
                    'success': True,
                    'message_sid': sms.sid,
                    'status': sms.status
                }
                
            except Exception as e:
                logger.error(f"Failed to send SMS to {to_number[-4:]}: {e}")
                
                if log_for_audit:
                    self._log_sms(to_number, message, None, 'failed', str(e))
                
                return {
                    'success': False,
                    'error': str(e)
                }
        else:
            # Development mode: log instead of sending
            logger.info(f"[DEV SMS] To: {to_number}, Message: {message[:100]}...")
            
            if log_for_audit:
                self._log_sms(to_number, message, 'DEV_MODE', 'logged')
            
            return {
                'success': True,
                'message_sid': 'DEV_MODE',
                'status': 'logged',
                'note': 'SMS logged (Twilio not configured)'
            }
    
    def _log_sms(self, to_number: str, message: str, sid: str, 
                 status: str, error: str = None):
        """Log SMS for audit purposes."""
        try:
            from .models import AuditLog
            AuditLog.objects.create(
                action='api_access',
                model_name='SMS',
                extra_data={
                    'to': to_number[-4:] if to_number else None,  # Last 4 digits only
                    'message_preview': message[:50] + '...' if len(message) > 50 else message,
                    'sid': sid,
                    'status': status,
                    'error': error
                }
            )
        except Exception as e:
            logger.error(f"Failed to log SMS: {e}")
    
    # ==========================================
    # Convenience Methods for Common SMS Types
    # ==========================================
    
    def send_service_update(self, customer, status: str, 
                           service_id: int = None) -> Dict:
        """
        Send service request status update.
        
        Args:
            customer: CustomUser instance
            status: New status ('in_progress', 'completed', etc.)
            service_id: Service request ID
        """
        if not customer.phone_number:
            return {'success': False, 'error': 'Müşterinin telefon numarası yok'}
        
        status_messages = {
            'in_progress': 'işleme alındı',
            'completed': 'tamamlandı',
            'pending': 'alındı, beklemede',
            'cancelled': 'iptal edildi',
        }
        
        status_text = status_messages.get(status, status)
        message = f"BekoSIRS: Servis talebiniz (#{service_id}) {status_text}. Detaylar için uygulamayı kontrol edin."
        
        return self.send_sms(customer.phone_number, message)
    
    def send_delivery_notification(self, customer, delivery_date: str,
                                   time_window: str = None) -> Dict:
        """
        Send delivery notification.
        
        Args:
            customer: CustomUser instance
            delivery_date: Delivery date string
            time_window: Optional time window ("10:00-12:00")
        """
        if not customer.phone_number:
            return {'success': False, 'error': 'Müşterinin telefon numarası yok'}
        
        if time_window:
            message = f"BekoSIRS: Teslimatınız {delivery_date} tarihinde {time_window} saatleri arasında yapılacaktır."
        else:
            message = f"BekoSIRS: Teslimatınız {delivery_date} tarihinde yapılacaktır."
        
        return self.send_sms(customer.phone_number, message)
    
    def send_payment_reminder(self, customer, amount: float, 
                              due_date: str, installment_no: int = None) -> Dict:
        """
        Send payment/installment reminder.
        """
        if not customer.phone_number:
            return {'success': False, 'error': 'Müşterinin telefon numarası yok'}
        
        if installment_no:
            message = f"BekoSIRS: {installment_no}. taksit ödemeniz ({amount:.2f} TL) {due_date} tarihinde vadesi dolacak."
        else:
            message = f"BekoSIRS: {amount:.2f} TL tutarındaki ödemeniz {due_date} tarihinde vadesi dolacak."
        
        return self.send_sms(customer.phone_number, message)
    
    def send_otp(self, customer, otp_code: str, 
                 purpose: str = 'doğrulama') -> Dict:
        """
        Send OTP/verification code.
        
        Args:
            customer: CustomUser instance
            otp_code: 6-digit OTP code
            purpose: Purpose of OTP (doğrulama, giriş, şifre sıfırlama)
        """
        if not customer.phone_number:
            return {'success': False, 'error': 'Müşterinin telefon numarası yok'}
        
        message = f"BekoSIRS {purpose} kodu: {otp_code}. Bu kodu kimseyle paylaşmayın. 5 dakika geçerlidir."
        
        # OTP should not be logged in detail for security
        return self.send_sms(customer.phone_number, message, log_for_audit=False)
    
    def send_welcome_sms(self, customer) -> Dict:
        """Send welcome SMS to new customer."""
        if not customer.phone_number:
            return {'success': False, 'error': 'Müşterinin telefon numarası yok'}
        
        message = f"Merhaba {customer.first_name or 'Değerli Müşterimiz'}! BekoSIRS ailesine hoş geldiniz. Ürünlerimizi keşfetmek için uygulamayı ziyaret edin."
        
        return self.send_sms(customer.phone_number, message)
    
    def send_bulk_sms(self, customers: List, message: str) -> Dict:
        """
        Send SMS to multiple customers.
        
        Args:
            customers: List of CustomUser instances
            message: SMS message
            
        Returns:
            Dict with success count and failures
        """
        results = {
            'total': len(customers),
            'sent': 0,
            'failed': 0,
            'no_phone': 0,
            'errors': []
        }
        
        for customer in customers:
            if not customer.phone_number:
                results['no_phone'] += 1
                continue
            
            result = self.send_sms(customer.phone_number, message)
            
            if result.get('success'):
                results['sent'] += 1
            else:
                results['failed'] += 1
                results['errors'].append({
                    'customer_id': customer.id,
                    'error': result.get('error')
                })
        
        return results


# Singleton instance for convenience
_sms_service = None

def get_sms_service() -> SMSService:
    """Get or create SMS service singleton."""
    global _sms_service
    if _sms_service is None:
        _sms_service = SMSService()
    return _sms_service
