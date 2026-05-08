from unittest.mock import patch, MagicMock
import base64
from django.urls import reverse
from rest_framework import status
from .conftest import APITestCase
from django.core.files.uploadedfile import SimpleUploadedFile

class BiometricAPITest(APITestCase):
    """Tests for true biometric/Face ID API endpoints."""

    def setUp(self):
        super().setUp()
        # Clear throttle cache between tests to prevent rate-limiter state leaking
        from django.core.cache import cache
        cache.clear()
        
        self.enable_url = reverse('biometric_enable')
        self.disable_url = reverse('biometric_disable')
        self.status_url = reverse('biometric_status')
        self.login_url = reverse('biometric_login')
        
        # Create a tiny 1x1 PNG image to pass DRF's ImageField validation
        tiny_png_b64 = b"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
        tiny_png_bytes = base64.b64decode(tiny_png_b64)
        
        self.test_image = SimpleUploadedFile(
            "test_face.png",
            tiny_png_bytes,
            content_type="image/png"
        )
        
        # Test encoding
        self.test_encoding = [0.1] * 128

    def _make_test_image(self, name="test.png"):
        """Helper to create a fresh test image (file cursor at 0)."""
        return SimpleUploadedFile(
            name,
            base64.b64decode(b"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="),
            content_type="image/png"
        )

    # ---------------------------------------------------------------
    # Existing Tests (updated with _check_liveness mock)
    # ---------------------------------------------------------------

    def test_enable_biometric_requires_auth(self):
        """Enable endpoint should require authentication."""
        response = self.client.post(self.enable_url, {'face_image': self.test_image})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch('products.views.biometric_views._check_liveness_frames', return_value=(True, 0.92, None))
    @patch('products.views.biometric_views.cv2.imdecode')
    @patch('deepface.DeepFace.represent')
    def test_enable_biometric_success(self, mock_represent, mock_imdecode, mock_liveness):
        """Authenticated user can enable biometric with a face image."""
        self.authenticate_customer()
        self.test_image.seek(0)
        
        # Mock DeepFace.represent to return a dummy encoding
        mock_represent.return_value = [{"embedding": self.test_encoding}]
        
        mock_imdecode.return_value = 'dummy_image_array'
        
        response = self.client.post(self.enable_url, {'face_image': self.test_image}, format='multipart')
        
        print("Enable Response:", response.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertTrue(response.data['biometric_enabled'])
        
        # Verify in database
        self.customer_user.refresh_from_db()
        self.assertTrue(self.customer_user.biometric_enabled)
        # face_encoding should now be an encrypted string, NOT a plain list
        self.assertIsNotNone(self.customer_user.face_encoding)

    @patch('products.views.biometric_views._check_liveness_frames', return_value=(True, 0.92, None))
    @patch('products.views.biometric_views.cv2.imdecode')
    @patch('deepface.DeepFace.represent')
    def test_face_encoding_stored_encrypted(self, mock_represent, mock_imdecode, mock_liveness):
        """Issue #29: face_encoding in DB must be an encrypted string, not a plain list."""
        self.authenticate_customer()
        self.test_image.seek(0)
        
        mock_represent.return_value = [{"embedding": self.test_encoding}]
        mock_imdecode.return_value = 'dummy_image_array'
        
        self.client.post(self.enable_url, {'face_image': self.test_image}, format='multipart')
        
        self.customer_user.refresh_from_db()
        stored = self.customer_user.face_encoding
        
        # Must be a string (Fernet token), not a list
        self.assertIsInstance(stored, str)
        self.assertNotEqual(stored, self.test_encoding)
        
        # Decrypt and verify it matches the original embedding
        from products.encryption import decrypt_face_encoding
        decrypted = decrypt_face_encoding(stored)
        self.assertEqual(decrypted, self.test_encoding)

    def test_disable_biometric_success(self):
        """Authenticated user can disable biometric."""
        self.authenticate_customer()
        
        # First enable (store encrypted)
        from products.encryption import encrypt_face_encoding
        self.customer_user.biometric_enabled = True
        self.customer_user.face_encoding = encrypt_face_encoding(self.test_encoding)
        self.customer_user.save()
        
        response = self.client.post(self.disable_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertFalse(response.data['biometric_enabled'])
        
        # Verify in database
        self.customer_user.refresh_from_db()
        self.assertFalse(self.customer_user.biometric_enabled)
        self.assertIsNone(self.customer_user.face_encoding)

    def test_get_biometric_status(self):
        """Can get biometric status for authenticated user."""
        self.authenticate_customer()
        
        response = self.client.get(self.status_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('biometric_enabled', response.data)
        self.assertIn('has_encoding', response.data)

    @patch('products.views.biometric_views._check_liveness_frames', return_value=(True, 0.92, None))
    @patch('products.views.biometric_views.cv2.imdecode')
    @patch('deepface.modules.verification.find_threshold')
    @patch('deepface.modules.verification.find_distance')
    @patch('deepface.DeepFace.represent')
    def test_biometric_login_success(self, mock_represent, mock_find_distance, mock_find_threshold, mock_imdecode, mock_liveness):
        """Valid face login should return tokens."""
        self.test_image.seek(0)
        # Enable biometric for customer (store encrypted)
        from products.encryption import encrypt_face_encoding
        self.customer_user.biometric_enabled = True
        self.customer_user.face_encoding = encrypt_face_encoding(self.test_encoding)
        self.customer_user.save()
        
        # Mock DeepFace.represent to return the same encoding
        mock_represent.return_value = [{"embedding": self.test_encoding}]
        
        # Mock distance and threshold so distance <= lenient_threshold
        mock_find_distance.return_value = 0.1
        mock_find_threshold.return_value = 0.4
        mock_imdecode.return_value = 'dummy_image_array'
        
        response = self.client.post(self.login_url, {
            'username': self.customer_user.username,
            'face_image': self.test_image
        }, format='multipart')
        
        print("Login Response:", response.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('refresh', response.data['tokens'])
        self.assertIn('access', response.data['tokens'])
        self.assertIn('user_id', response.data)

    def test_biometric_login_missing_params(self):
        """Login without username or face_image should fail."""
        response = self.client.post(self.login_url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch('products.views.biometric_views._check_liveness_frames', return_value=(True, 0.92, None))
    @patch('products.views.biometric_views.cv2.imdecode')
    @patch('deepface.modules.verification.find_threshold')
    @patch('deepface.modules.verification.find_distance')
    @patch('deepface.DeepFace.represent')
    def test_biometric_login_rate_limited(self, mock_represent, mock_find_distance, mock_find_threshold, mock_imdecode, mock_liveness):
        """Issue #37: Biometric login endpoint should be rate-limited to 5 requests/minute."""
        from django.core.cache import cache
        cache.clear()  # Start clean

        # Enable biometric for customer (store encrypted)
        from products.encryption import encrypt_face_encoding
        self.customer_user.biometric_enabled = True
        self.customer_user.face_encoding = encrypt_face_encoding(self.test_encoding)
        self.customer_user.save()

        mock_represent.return_value = [{"embedding": self.test_encoding}]
        mock_find_distance.return_value = 0.1
        mock_find_threshold.return_value = 0.4
        mock_imdecode.return_value = 'dummy_image_array'

        # Make 5 allowed requests
        for i in range(5):
            img = self._make_test_image(f"face_{i}.png")
            resp = self.client.post(self.login_url, {
                'username': self.customer_user.username,
                'face_image': img,
            }, format='multipart')
            self.assertNotEqual(
                resp.status_code,
                status.HTTP_429_TOO_MANY_REQUESTS,
                f"Request {i+1} should be allowed but got 429"
            )

        # 6th request should be throttled
        img = self._make_test_image("face_extra.png")
        resp = self.client.post(self.login_url, {
            'username': self.customer_user.username,
            'face_image': img,
        }, format='multipart')
        self.assertEqual(resp.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    # ---------------------------------------------------------------
    # Issue #30 — Liveness Detection Tests
    # ---------------------------------------------------------------

    @patch('products.views.biometric_views._check_liveness_frames')
    @patch('products.views.biometric_views.cv2.imdecode')
    def test_enable_rejects_spoof(self, mock_imdecode, mock_liveness):
        """Issue #30: biometric_enable must reject spoofed (printed/screen) faces."""
        self.authenticate_customer()
        self.test_image.seek(0)
        mock_imdecode.return_value = 'dummy_image_array'
        
        # Simulate spoof detection
        mock_liveness.return_value = (
            False,
            0.31,
            "Canlılık doğrulaması başarısız. "
            "Lütfen gerçek yüzünüzü kameraya gösterin "
            "(basılmış fotoğraf veya ekran kabul edilmez)."
        )
        
        response = self.client.post(
            self.enable_url,
            {
                'face_image': self.test_image,
                'frame_left': self._make_test_image('left.jpg'),
                'frame_center': self._make_test_image('center.jpg'),
                'frame_right': self._make_test_image('right.jpg'),
            },
            format='multipart'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertIn('Canlılık doğrulaması', response.data['error'])
        self.assertIn('liveness_score', response.data)
        
        # User's biometric should NOT be enabled
        self.customer_user.refresh_from_db()
        self.assertFalse(self.customer_user.biometric_enabled)

    @patch('products.views.biometric_views._check_liveness_frames')
    @patch('products.views.biometric_views.cv2.imdecode')
    def test_login_rejects_spoof(self, mock_imdecode, mock_liveness):
        """Issue #30: biometric_login must reject spoofed faces with 403."""
        # Enable biometric first
        from products.encryption import encrypt_face_encoding
        self.customer_user.biometric_enabled = True
        self.customer_user.face_encoding = encrypt_face_encoding(self.test_encoding)
        self.customer_user.save()

        self.test_image.seek(0)
        mock_imdecode.return_value = 'dummy_image_array'
        
        # Simulate spoof detection
        mock_liveness.return_value = (
            False,
            0.28,
            "Canlılık doğrulaması başarısız. "
            "Lütfen gerçek yüzünüzü kameraya gösterin "
            "(basılmış fotoğraf veya ekran kabul edilmez)."
        )
        
        response = self.client.post(self.login_url, {
            'username': self.customer_user.username,
            'face_image': self.test_image,
            'frame_left': self._make_test_image('left.jpg'),
            'frame_center': self._make_test_image('center.jpg'),
            'frame_right': self._make_test_image('right.jpg'),
        }, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(response.data['success'])
        self.assertIn('Canlılık doğrulaması', response.data['error'])
        self.assertIn('liveness_score', response.data)

    @patch('products.views.biometric_views._check_liveness_frames', return_value=(True, 0.95, None))
    @patch('products.views.biometric_views.cv2.imdecode')
    @patch('deepface.modules.verification.find_threshold')
    @patch('deepface.modules.verification.find_distance')
    @patch('deepface.DeepFace.represent')
    def test_login_accepts_real_face_liveness(self, mock_represent, mock_find_distance, mock_find_threshold, mock_imdecode, mock_liveness):
        """Issue #30: real face (high antispoof score) should pass liveness and log in."""
        from products.encryption import encrypt_face_encoding
        self.customer_user.biometric_enabled = True
        self.customer_user.face_encoding = encrypt_face_encoding(self.test_encoding)
        self.customer_user.save()

        self.test_image.seek(0)
        mock_represent.return_value = [{"embedding": self.test_encoding}]
        mock_find_distance.return_value = 0.05
        mock_find_threshold.return_value = 0.4
        mock_imdecode.return_value = 'dummy_image_array'

        response = self.client.post(self.login_url, {
            'username': self.customer_user.username,
            'face_image': self.test_image,
        }, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('tokens', response.data)

    # ---------------------------------------------------------------
    # Login-With-Liveness (Unified Endpoint) Tests
    # ---------------------------------------------------------------

    def test_login_with_liveness_missing_username(self):
        """login-with-liveness should require username."""
        url = reverse('biometric_login_with_liveness')
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])

    def test_login_with_liveness_insufficient_frames(self):
        """login-with-liveness should reject fewer than 3 frames."""
        url = reverse('biometric_login_with_liveness')
        img = self._make_test_image("frame_0.jpg")
        response = self.client.post(url, {
            'username': self.customer_user.username,
            'frame_0': img,
        }, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Yetersiz frame', response.data.get('error', ''))

    @patch('products.views.biometric_views.run_liveness_check_multiframe')
    def test_login_with_liveness_fails_when_not_live(self, mock_liveness):
        """login-with-liveness should return 403 when liveness check fails."""
        from products.liveness_detection import LivenessResult
        mock_liveness.return_value = LivenessResult(
            is_live=False,
            score=0.15,
            reason="Hareket algılanamadı (sabit görüntü).",
        )

        from products.encryption import encrypt_face_encoding
        self.customer_user.biometric_enabled = True
        self.customer_user.face_encoding = encrypt_face_encoding(self.test_encoding)
        self.customer_user.save()

        url = reverse('biometric_login_with_liveness')
        data = {'username': self.customer_user.username}
        for i in range(4):
            data[f'frame_{i}'] = self._make_test_image(f"frame_{i}.jpg")

        response = self.client.post(url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(response.data['success'])

    @patch('products.views.biometric_views.cv2.imdecode')
    @patch('deepface.DeepFace.represent')
    @patch('deepface.modules.verification.find_distance')
    @patch('deepface.modules.verification.find_threshold')
    @patch('products.views.biometric_views.run_liveness_check_multiframe')
    def test_login_with_liveness_face_mismatch(
        self, mock_liveness, mock_threshold, mock_distance, mock_represent, mock_imdecode
    ):
        """login-with-liveness: liveness passes but face doesn't match → 401."""
        from products.liveness_detection import LivenessResult
        mock_liveness.return_value = LivenessResult(is_live=True, score=0.85, reason="OK")

        mock_represent.return_value = [{"embedding": [0.9] * 128}]
        mock_distance.return_value = 0.8  # High distance → mismatch
        mock_threshold.return_value = 0.4
        mock_imdecode.return_value = MagicMock()

        from products.encryption import encrypt_face_encoding
        self.customer_user.biometric_enabled = True
        self.customer_user.face_encoding = encrypt_face_encoding(self.test_encoding)
        self.customer_user.save()

        url = reverse('biometric_login_with_liveness')
        data = {'username': self.customer_user.username}
        for i in range(4):
            data[f'frame_{i}'] = self._make_test_image(f"frame_{i}.jpg")

        response = self.client.post(url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertFalse(response.data['success'])
        self.assertIn('eşleşmedi', response.data.get('error', ''))

    @patch('products.views.biometric_views.cv2.imdecode')
    @patch('deepface.DeepFace.represent')
    @patch('deepface.modules.verification.find_distance')
    @patch('deepface.modules.verification.find_threshold')
    @patch('products.views.biometric_views.run_liveness_check_multiframe')
    def test_login_with_liveness_full_success(
        self, mock_liveness, mock_threshold, mock_distance, mock_represent, mock_imdecode
    ):
        """login-with-liveness: liveness + face match → tokens returned."""
        from products.liveness_detection import LivenessResult
        mock_liveness.return_value = LivenessResult(is_live=True, score=0.92, reason="OK")

        mock_represent.return_value = [{"embedding": self.test_encoding}]
        mock_distance.return_value = 0.1
        mock_threshold.return_value = 0.4
        mock_imdecode.return_value = MagicMock()

        from products.encryption import encrypt_face_encoding
        self.customer_user.biometric_enabled = True
        self.customer_user.face_encoding = encrypt_face_encoding(self.test_encoding)
        self.customer_user.save()

        url = reverse('biometric_login_with_liveness')
        data = {'username': self.customer_user.username}
        for i in range(5):
            data[f'frame_{i}'] = self._make_test_image(f"frame_{i}.jpg")

        response = self.client.post(url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('tokens', response.data)
        self.assertIn('liveness_score', response.data)

    def test_login_with_liveness_user_not_found(self):
        """login-with-liveness with a nonexistent username → 404."""
        url = reverse('biometric_login_with_liveness')
        data = {'username': 'nonexistent_user_xyz'}
        for i in range(4):
            data[f'frame_{i}'] = self._make_test_image(f"frame_{i}.jpg")

        with patch('products.views.biometric_views.run_liveness_check_multiframe') as mock_lv:
            from products.liveness_detection import LivenessResult
            mock_lv.return_value = LivenessResult(is_live=True, score=0.9, reason="OK")
            response = self.client.post(url, data, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # ---------------------------------------------------------------
    # Liveness Check Multi (Standalone) Tests
    # ---------------------------------------------------------------

    @patch('products.views.biometric_views.run_liveness_check_multiframe')
    def test_liveness_check_multi_success(self, mock_liveness):
        """liveness-check-multi should return liveness result on valid frames."""
        from products.liveness_detection import LivenessResult
        mock_liveness.return_value = LivenessResult(
            is_live=True, score=0.88, reason="Canlı algılandı."
        )

        url = reverse('biometric_liveness_check_multi')
        data = {}
        for i in range(4):
            data[f'frame_{i}'] = self._make_test_image(f"frame_{i}.jpg")

        response = self.client.post(url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['is_live'])

    def test_liveness_check_multi_no_frames(self):
        """liveness-check-multi with no frames should fail."""
        url = reverse('biometric_liveness_check_multi')
        response = self.client.post(url, {}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
