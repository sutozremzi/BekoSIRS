# products/test_serializers.py
"""
Unit tests for Django REST Framework serializers.
Tests serialization, deserialization, and validation logic.
"""

from decimal import Decimal
from datetime import date
from dateutil.relativedelta import relativedelta
from django.test import TestCase
from rest_framework.exceptions import ValidationError

from products.models import (
    CustomUser, Category, Product, ProductOwnership
)
from products.serializers import (
    RegisterSerializer, ProductSerializer, CategorySerializer,
    ProductOwnershipSerializer, UserSerializer, WishlistItemSerializer
)
from products.conftest import BaseTestCase


class RegisterSerializerTest(TestCase):
    """Tests for RegisterSerializer."""

    def test_valid_registration_data(self):
        """Valid data should pass validation."""
        data = {
            'username': 'newuser',
            'email': 'newuser@test.com',
            'password': 'StrongPass123!',
            'first_name': 'New',
            'last_name': 'User',
            'phone_number': '+905551234567'
        }
        serializer = RegisterSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_create_user_with_serializer(self):
        """Serializer should create user with hashed password."""
        data = {
            'username': 'createuser',
            'email': 'create@test.com',
            'password': 'StrongPass123!',
            'first_name': 'Create',
            'last_name': 'User'
        }
        serializer = RegisterSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        user = serializer.save()
        
        # Password should be hashed, not plain text
        self.assertNotEqual(user.password, 'StrongPass123!')
        self.assertTrue(user.check_password('StrongPass123!'))
        
        # Role should default to customer
        self.assertEqual(user.role, 'customer')

    def test_duplicate_username_rejected(self):
        """Duplicate username should be rejected."""
        CustomUser.objects.create_user(
            username='existinguser',
            email='existing@test.com',
            password='pass123'
        )
        data = {
            'username': 'existinguser',
            'email': 'new@test.com',
            'password': 'StrongPass123!'
        }
        serializer = RegisterSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('username', serializer.errors)

    def test_duplicate_email_rejected(self):
        """Duplicate email should be rejected."""
        CustomUser.objects.create_user(
            username='user1',
            email='duplicate@test.com',
            password='pass123'
        )
        data = {
            'username': 'user2',
            'email': 'duplicate@test.com',
            'password': 'StrongPass123!'
        }
        serializer = RegisterSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('email', serializer.errors)

    def test_missing_required_fields(self):
        """Missing required fields should be rejected."""
        data = {'username': 'onlyuser'}
        serializer = RegisterSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('password', serializer.errors)
        self.assertIn('email', serializer.errors)

    def test_phone_number_optional(self):
        """Phone number should be optional."""
        data = {
            'username': 'nophone',
            'email': 'nophone@test.com',
            'password': 'StrongPass123!'
        }
        serializer = RegisterSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)


class CategorySerializerTest(TestCase):
    """Tests for CategorySerializer."""

    def test_serialize_category(self):
        """Category should serialize with id and name."""
        category = Category.objects.create(name='Test Category')
        serializer = CategorySerializer(category)
        self.assertEqual(serializer.data['id'], category.id)
        self.assertEqual(serializer.data['name'], 'Test Category')

    def test_deserialize_category(self):
        """Category should deserialize from valid data."""
        data = {'name': 'New Category'}
        serializer = CategorySerializer(data=data)
        self.assertTrue(serializer.is_valid())


class ProductSerializerTest(BaseTestCase):
    """Tests for ProductSerializer."""

    def test_serialize_product(self):
        """Product should serialize with all fields."""
        serializer = ProductSerializer(self.product_fridge)
        data = serializer.data
        
        self.assertEqual(data['id'], self.product_fridge.id)
        self.assertEqual(data['name'], 'Buzdolabı Pro')
        self.assertEqual(data['brand'], 'Beko')
        self.assertEqual(Decimal(data['price']), Decimal('15999.99'))
        self.assertEqual(data['stock'], 10)

    def test_product_includes_nested_category(self):
        """Product serialization should include nested category."""
        serializer = ProductSerializer(self.product_fridge)
        data = serializer.data
        
        self.assertIn('category', data)
        self.assertEqual(data['category']['name'], 'Beyaz Eşya')

    def test_product_includes_category_name(self):
        """Product should have category_name field."""
        serializer = ProductSerializer(self.product_fridge)
        data = serializer.data
        
        self.assertIn('category_name', data)
        self.assertEqual(data['category_name'], 'Beyaz Eşya')

    def test_serialize_multiple_products(self):
        """Serializer should handle multiple products."""
        products = Product.objects.all()[:2]
        serializer = ProductSerializer(products, many=True)
        self.assertEqual(len(serializer.data), 2)


class ProductOwnershipSerializerTest(BaseTestCase):
    """Tests for ProductOwnershipSerializer."""

    def test_serialize_ownership(self):
        """ProductOwnership should serialize with warranty_end_date."""
        ownership = ProductOwnership.objects.create(
            customer=self.customer_user,
            product=self.product_fridge,  # 24 months warranty
            purchase_date=date(2024, 1, 15),
            serial_number='SN-TEST-001'
        )
        serializer = ProductOwnershipSerializer(ownership)
        data = serializer.data
        
        self.assertEqual(data['serial_number'], 'SN-TEST-001')
        self.assertIn('warranty_end_date', data)
        
        # Check warranty calculation
        expected_end = date(2024, 1, 15) + relativedelta(months=24)
        self.assertEqual(data['warranty_end_date'], str(expected_end))

    def test_ownership_includes_nested_product(self):
        """Ownership should include nested product details."""
        ownership = ProductOwnership.objects.create(
            customer=self.customer_user,
            product=self.product_fridge,
            purchase_date=date.today()
        )
        serializer = ProductOwnershipSerializer(ownership)
        data = serializer.data
        
        self.assertIn('product', data)
        self.assertEqual(data['product']['name'], 'Buzdolabı Pro')


class UserSerializerTest(BaseTestCase):
    """Tests for UserSerializer."""

    def test_serialize_user(self):
        """User should serialize with expected fields."""
        serializer = UserSerializer(self.customer_user)
        data = serializer.data
        
        self.assertEqual(data['username'], 'test_customer')
        self.assertEqual(data['email'], 'customer@test.com')
        self.assertEqual(data['role'], 'customer')
        self.assertIn('first_name', data)
        self.assertIn('last_name', data)
        
        # Password should NOT be in serialized output
        self.assertNotIn('password', data)

    def test_serialize_admin_user(self):
        """Admin user should have correct role."""
        serializer = UserSerializer(self.admin_user)
        self.assertEqual(serializer.data['role'], 'admin')
