# products/conftest.py
"""
Shared test fixtures for the products app.
Provides reusable test data for users, products, categories, etc.
"""

import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase
from rest_framework.test import APIClient

from products.models import (
    CustomUser, Category, Product, ProductOwnership,
    Wishlist, WishlistItem, ServiceRequest, Review, Notification
)


class BaseTestCase(TestCase):
    """Base test case with common fixtures."""

    @classmethod
    def setUpTestData(cls):
        """Create shared test data for all test methods."""
        # Create users with different roles
        cls.admin_user = CustomUser.objects.create_user(
            username='test_admin',
            email='admin@test.com',
            password='AdminPass123!',
            first_name='Admin',
            last_name='User',
            role='admin'
        )
        cls.seller_user = CustomUser.objects.create_user(
            username='test_seller',
            email='seller@test.com',
            password='SellerPass123!',
            first_name='Seller',
            last_name='User',
            role='seller'
        )
        cls.customer_user = CustomUser.objects.create_user(
            username='test_customer',
            email='customer@test.com',
            password='CustomerPass123!',
            first_name='Customer',
            last_name='User',
            role='customer',
            phone_number='+905551234567'
        )

        # Create categories
        cls.category_appliances = Category.objects.create(name='Beyaz Eşya')
        cls.category_electronics = Category.objects.create(name='Elektronik')

        # Create products
        cls.product_fridge = Product.objects.create(
            name='Buzdolabı Pro',
            brand='Beko',
            category=cls.category_appliances,
            description='Enerji verimli buzdolabı',
            price=Decimal('15999.99'),
            stock=10,
            warranty_duration_months=24
        )
        cls.product_washer = Product.objects.create(
            name='Çamaşır Makinesi',
            brand='Beko',
            category=cls.category_appliances,
            description='Akıllı çamaşır makinesi',
            price=Decimal('12499.50'),
            stock=5,
            warranty_duration_months=36
        )
        cls.product_tv = Product.objects.create(
            name='Smart TV 55"',
            brand='Grundig',
            category=cls.category_electronics,
            description='4K Ultra HD Smart TV',
            price=Decimal('24999.00'),
            stock=0,  # Out of stock
            warranty_duration_months=24
        )

    def setUp(self):
        """Set up API client for each test."""
        self.client = APIClient()

    def authenticate_as(self, user):
        """Helper to authenticate the API client as a specific user."""
        self.client.force_authenticate(user=user)

    def authenticate_admin(self):
        """Authenticate as admin user."""
        self.authenticate_as(self.admin_user)

    def authenticate_seller(self):
        """Authenticate as seller user."""
        self.authenticate_as(self.seller_user)

    def authenticate_customer(self):
        """Authenticate as customer user."""
        self.authenticate_as(self.customer_user)

    def create_product_ownership(self, customer=None, product=None, purchase_date=None):
        """Helper to create a ProductOwnership record."""
        return ProductOwnership.objects.create(
            customer=customer or self.customer_user,
            product=product or self.product_fridge,
            purchase_date=purchase_date or date.today(),
            serial_number='SN-TEST-001'
        )

    def create_wishlist_for_customer(self, customer=None):
        """Helper to create a Wishlist for a customer."""
        return Wishlist.objects.create(
            customer=customer or self.customer_user
        )

    def create_service_request(self, customer=None, ownership=None, status='pending'):
        """Helper to create a ServiceRequest."""
        if ownership is None:
            ownership = self.create_product_ownership(customer)
        return ServiceRequest.objects.create(
            customer=customer or self.customer_user,
            product_ownership=ownership,
            request_type='repair',
            status=status,
            description='Test service request description'
        )


class APITestCase(BaseTestCase):
    """Test case specifically for API endpoint testing."""

    def get_tokens_for_user(self, user):
        """Get JWT tokens for a user by logging in."""
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(user)
        return {
            'access': str(refresh.access_token),
            'refresh': str(refresh)
        }

    def authenticate_with_token(self, user):
        """Authenticate using JWT token."""
        tokens = self.get_tokens_for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        return tokens
