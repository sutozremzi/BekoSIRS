# products/test_permissions.py
"""
Unit tests for permission classes.
Tests verify that role-based access control works correctly.
"""

from django.test import TestCase, RequestFactory
from rest_framework.views import APIView
from rest_framework.response import Response

from products.models import CustomUser
from products.permissions import (
    IsAdmin,
    IsAdminOrReadOnly,
    IsSeller,
    IsCustomer,
    IsOwnerOrAdmin,
)


class DummyView(APIView):
    """Dummy view for testing permissions."""
    pass


class PermissionTestCase(TestCase):
    """Base test case with user fixtures."""

    @classmethod
    def setUpTestData(cls):
        """Create test users with different roles."""
        cls.admin_user = CustomUser.objects.create_user(
            username='admin_test',
            email='admin@test.com',
            password='testpass123',
            role='admin'
        )
        cls.seller_user = CustomUser.objects.create_user(
            username='seller_test',
            email='seller@test.com',
            password='testpass123',
            role='seller'
        )
        cls.customer_user = CustomUser.objects.create_user(
            username='customer_test',
            email='customer@test.com',
            password='testpass123',
            role='customer'
        )

    def setUp(self):
        """Set up request factory."""
        self.factory = RequestFactory()
        self.view = DummyView()


class IsAdminPermissionTest(PermissionTestCase):
    """Tests for IsAdmin permission class."""

    def test_admin_has_permission(self):
        """Admin user should have permission."""
        request = self.factory.get('/')
        request.user = self.admin_user
        permission = IsAdmin()
        self.assertTrue(permission.has_permission(request, self.view))

    def test_seller_denied(self):
        """Seller user should be denied."""
        request = self.factory.get('/')
        request.user = self.seller_user
        permission = IsAdmin()
        self.assertFalse(permission.has_permission(request, self.view))

    def test_customer_denied(self):
        """Customer user should be denied."""
        request = self.factory.get('/')
        request.user = self.customer_user
        permission = IsAdmin()
        self.assertFalse(permission.has_permission(request, self.view))


class IsAdminOrReadOnlyPermissionTest(PermissionTestCase):
    """Tests for IsAdminOrReadOnly permission class."""

    def test_get_allowed_for_customer(self):
        """GET request should be allowed for any authenticated user."""
        request = self.factory.get('/')
        request.user = self.customer_user
        permission = IsAdminOrReadOnly()
        self.assertTrue(permission.has_permission(request, self.view))

    def test_post_denied_for_customer(self):
        """POST request should be denied for customer."""
        request = self.factory.post('/')
        request.user = self.customer_user
        permission = IsAdminOrReadOnly()
        self.assertFalse(permission.has_permission(request, self.view))

    def test_post_allowed_for_admin(self):
        """POST request should be allowed for admin."""
        request = self.factory.post('/')
        request.user = self.admin_user
        permission = IsAdminOrReadOnly()
        self.assertTrue(permission.has_permission(request, self.view))

    def test_put_denied_for_seller(self):
        """PUT request should be denied for seller."""
        request = self.factory.put('/')
        request.user = self.seller_user
        permission = IsAdminOrReadOnly()
        self.assertFalse(permission.has_permission(request, self.view))


class IsSellerPermissionTest(PermissionTestCase):
    """Tests for IsSeller permission class."""

    def test_admin_has_permission(self):
        """Admin should have permission (admin is always a seller)."""
        request = self.factory.get('/')
        request.user = self.admin_user
        permission = IsSeller()
        self.assertTrue(permission.has_permission(request, self.view))

    def test_seller_has_permission(self):
        """Seller should have permission."""
        request = self.factory.get('/')
        request.user = self.seller_user
        permission = IsSeller()
        self.assertTrue(permission.has_permission(request, self.view))

    def test_customer_denied(self):
        """Customer should be denied."""
        request = self.factory.get('/')
        request.user = self.customer_user
        permission = IsSeller()
        self.assertFalse(permission.has_permission(request, self.view))


class IsCustomerPermissionTest(PermissionTestCase):
    """Tests for IsCustomer permission class."""

    def test_customer_has_permission(self):
        """Customer should have permission."""
        request = self.factory.get('/')
        request.user = self.customer_user
        permission = IsCustomer()
        self.assertTrue(permission.has_permission(request, self.view))

    def test_admin_denied(self):
        """Admin should be denied (not a customer)."""
        request = self.factory.get('/')
        request.user = self.admin_user
        permission = IsCustomer()
        self.assertFalse(permission.has_permission(request, self.view))

    def test_seller_denied(self):
        """Seller should be denied."""
        request = self.factory.get('/')
        request.user = self.seller_user
        permission = IsCustomer()
        self.assertFalse(permission.has_permission(request, self.view))
