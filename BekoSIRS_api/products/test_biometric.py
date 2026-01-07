from django.urls import reverse
from rest_framework import status
from .conftest import APITestCase

class BiometricAPITest(APITestCase):
    """Tests for biometric API endpoints."""

    def setUp(self):
        super().setUp()
        self.enable_url = reverse('biometric_enable')
        self.disable_url = reverse('biometric_disable')
        self.status_url = reverse('biometric_status')
        self.verify_url = reverse('biometric_verify_device')

    def test_enable_biometric_requires_auth(self):
        """Enable endpoint should require authentication."""
        response = self.client.post(self.enable_url, {
            'device_id': 'test-device-123',
            'refresh_token': 'test-token'
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_enable_biometric_success(self):
        """Authenticated user can enable biometric."""
        self.authenticate_customer()
        
        response = self.client.post(self.enable_url, {
            'device_id': 'ios_test_device_123',
            'refresh_token': 'test-refresh-token'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertTrue(response.data['biometric_enabled'])
        
        # Verify in database
        self.customer_user.refresh_from_db()
        self.assertTrue(self.customer_user.biometric_enabled)
        self.assertEqual(self.customer_user.biometric_device_id, 'ios_test_device_123')

    def test_disable_biometric_success(self):
        """Authenticated user can disable biometric."""
        self.authenticate_customer()
        
        # First enable
        self.customer_user.biometric_enabled = True
        self.customer_user.biometric_device_id = 'test-device'
        self.customer_user.save()
        
        response = self.client.post(self.disable_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertFalse(response.data['biometric_enabled'])
        
        # Verify in database
        self.customer_user.refresh_from_db()
        self.assertFalse(self.customer_user.biometric_enabled)
        self.assertIsNone(self.customer_user.biometric_device_id)

    def test_get_biometric_status(self):
        """Can get biometric status for authenticated user."""
        self.authenticate_customer()
        
        response = self.client.get(self.status_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('biometric_enabled', response.data)
        self.assertIn('has_device', response.data)

    def test_verify_device_valid(self):
        """Valid device should be verified."""
        # Enable biometric for customer
        self.customer_user.biometric_enabled = True
        self.customer_user.biometric_device_id = 'valid-device-id'
        self.customer_user.save()
        
        response = self.client.post(self.verify_url, {
            'device_id': 'valid-device-id',
            'user_id': self.customer_user.id
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['user_id'], self.customer_user.id)

    def test_verify_device_invalid_device(self):
        """Invalid device ID should fail verification."""
        self.customer_user.biometric_enabled = True
        self.customer_user.biometric_device_id = 'valid-device-id'
        self.customer_user.save()
        
        response = self.client.post(self.verify_url, {
            'device_id': 'wrong-device-id',
            'user_id': self.customer_user.id
        })
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])

    def test_verify_device_biometric_disabled(self):
        """Should fail if biometric not enabled for user."""
        self.customer_user.biometric_enabled = False
        self.customer_user.save()
        
        response = self.client.post(self.verify_url, {
            'device_id': 'any-device',
            'user_id': self.customer_user.id
        })
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])

    def test_verify_device_nonexistent_user(self):
        """Should fail for nonexistent user."""
        response = self.client.post(self.verify_url, {
            'device_id': 'any-device',
            'user_id': 99999
        })
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
