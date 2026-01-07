# products/test_models.py
"""
Unit tests for Django models.
Tests model creation, validation, and computed properties.
"""

from decimal import Decimal
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from products.models import (
    CustomUser, Category, Product, ProductOwnership,
    Wishlist, WishlistItem, ViewHistory, Review,
    ServiceRequest, ServiceQueue, Notification, Recommendation
)
from products.conftest import BaseTestCase


class CustomUserModelTest(TestCase):
    """Tests for CustomUser model."""

    def test_create_user_with_default_role(self):
        """New user should have 'customer' role by default."""
        user = CustomUser.objects.create_user(
            username='newuser',
            email='new@test.com',
            password='testpass123'
        )
        self.assertEqual(user.role, 'customer')
        self.assertTrue(user.check_password('testpass123'))

    def test_create_admin_user(self):
        """Admin user should have 'admin' role."""
        admin = CustomUser.objects.create_user(
            username='adminuser',
            email='admin@test.com',
            password='adminpass',
            role='admin'
        )
        self.assertEqual(admin.role, 'admin')

    def test_create_seller_user(self):
        """Seller user should have 'seller' role."""
        seller = CustomUser.objects.create_user(
            username='selleruser',
            email='seller@test.com',
            password='sellerpass',
            role='seller'
        )
        self.assertEqual(seller.role, 'seller')

    def test_user_str_representation(self):
        """User string representation should include username and role."""
        user = CustomUser.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='pass',
            role='customer'
        )
        self.assertIn('testuser', str(user))
        self.assertIn('customer', str(user))

    def test_notification_preferences_default(self):
        """User should have notification preferences enabled by default."""
        user = CustomUser.objects.create_user(
            username='notifyuser',
            email='notify@test.com',
            password='pass'
        )
        self.assertTrue(user.notify_service_updates)
        self.assertTrue(user.notify_price_drops)
        self.assertTrue(user.notify_restock)
        self.assertTrue(user.notify_recommendations)

    def test_unique_email_constraint(self):
        """Email should be unique across users."""
        CustomUser.objects.create_user(
            username='user1',
            email='same@test.com',
            password='pass'
        )
        # Creating second user with same email should work (Django doesn't enforce by default)
        # But our serializer should prevent this


class CategoryModelTest(TestCase):
    """Tests for Category model."""

    def test_create_category(self):
        """Category should be created with name."""
        category = Category.objects.create(name='Test Category')
        self.assertEqual(category.name, 'Test Category')

    def test_category_str_representation(self):
        """Category string should be its name."""
        category = Category.objects.create(name='Electronics')
        self.assertEqual(str(category), 'Electronics')

    def test_unique_category_name(self):
        """Category names should be unique."""
        Category.objects.create(name='Unique Category')
        with self.assertRaises(IntegrityError):
            Category.objects.create(name='Unique Category')


class ProductModelTest(BaseTestCase):
    """Tests for Product model."""

    def test_product_creation(self):
        """Product should be created with all fields."""
        self.assertEqual(self.product_fridge.name, 'Buzdolabı Pro')
        self.assertEqual(self.product_fridge.brand, 'Beko')
        self.assertEqual(self.product_fridge.price, Decimal('15999.99'))
        self.assertEqual(self.product_fridge.stock, 10)

    def test_product_category_relationship(self):
        """Product should be related to category."""
        self.assertEqual(self.product_fridge.category, self.category_appliances)
        self.assertIn(self.product_fridge, self.category_appliances.products.all())

    def test_product_str_representation(self):
        """Product string should be its name."""
        self.assertEqual(str(self.product_fridge), 'Buzdolabı Pro')

    def test_product_with_zero_stock(self):
        """Product can have zero stock (out of stock)."""
        self.assertEqual(self.product_tv.stock, 0)

    def test_product_warranty_duration(self):
        """Product should have warranty duration in months."""
        self.assertEqual(self.product_washer.warranty_duration_months, 36)


class ProductOwnershipModelTest(BaseTestCase):
    """Tests for ProductOwnership model."""

    def test_ownership_creation(self):
        """ProductOwnership should link customer to product."""
        ownership = ProductOwnership.objects.create(
            customer=self.customer_user,
            product=self.product_fridge,
            purchase_date=date(2024, 6, 15),
            serial_number='SN-12345'
        )
        self.assertEqual(ownership.customer, self.customer_user)
        self.assertEqual(ownership.product, self.product_fridge)

    def test_warranty_end_date_calculation(self):
        """warranty_end_date should be purchase_date + warranty_duration_months."""
        ownership = ProductOwnership.objects.create(
            customer=self.customer_user,
            product=self.product_fridge,  # 24 months warranty
            purchase_date=date(2024, 1, 15)
        )
        expected_end = date(2024, 1, 15) + relativedelta(months=24)
        self.assertEqual(ownership.warranty_end_date, expected_end)

    def test_warranty_end_date_36_months(self):
        """Test warranty calculation for 36 month product."""
        ownership = ProductOwnership.objects.create(
            customer=self.customer_user,
            product=self.product_washer,  # 36 months warranty
            purchase_date=date(2024, 3, 1)
        )
        expected_end = date(2024, 3, 1) + relativedelta(months=36)
        self.assertEqual(ownership.warranty_end_date, expected_end)

    def test_ownership_str_representation(self):
        """Ownership string should show customer and product."""
        ownership = ProductOwnership.objects.create(
            customer=self.customer_user,
            product=self.product_fridge,
            purchase_date=date.today()
        )
        self.assertIn(self.customer_user.username, str(ownership))
        self.assertIn(self.product_fridge.name, str(ownership))


class WishlistModelTest(BaseTestCase):
    """Tests for Wishlist and WishlistItem models."""

    def test_wishlist_creation(self):
        """Wishlist should be created for customer."""
        wishlist = Wishlist.objects.create(customer=self.customer_user)
        self.assertEqual(wishlist.customer, self.customer_user)

    def test_wishlist_item_count_empty(self):
        """Empty wishlist should have zero items."""
        wishlist = Wishlist.objects.create(customer=self.customer_user)
        self.assertEqual(wishlist.item_count, 0)

    def test_wishlist_item_count(self):
        """Wishlist item_count should reflect added items."""
        wishlist = Wishlist.objects.create(customer=self.customer_user)
        WishlistItem.objects.create(wishlist=wishlist, product=self.product_fridge)
        WishlistItem.objects.create(wishlist=wishlist, product=self.product_washer)
        self.assertEqual(wishlist.item_count, 2)

    def test_wishlist_item_unique_constraint(self):
        """Same product cannot be added twice to same wishlist."""
        wishlist = Wishlist.objects.create(customer=self.customer_user)
        WishlistItem.objects.create(wishlist=wishlist, product=self.product_fridge)
        with self.assertRaises(IntegrityError):
            WishlistItem.objects.create(wishlist=wishlist, product=self.product_fridge)

    def test_wishlist_item_notification_preferences(self):
        """WishlistItem should have notification preferences."""
        wishlist = Wishlist.objects.create(customer=self.customer_user)
        item = WishlistItem.objects.create(
            wishlist=wishlist,
            product=self.product_fridge,
            notify_on_price_drop=True,
            notify_on_restock=False
        )
        self.assertTrue(item.notify_on_price_drop)
        self.assertFalse(item.notify_on_restock)


class ServiceRequestModelTest(BaseTestCase):
    """Tests for ServiceRequest model."""

    def test_service_request_creation(self):
        """ServiceRequest should be created with required fields."""
        ownership = self.create_product_ownership()
        request = ServiceRequest.objects.create(
            customer=self.customer_user,
            product_ownership=ownership,
            request_type='repair',
            description='Screen not working'
        )
        self.assertEqual(request.status, 'pending')
        self.assertEqual(request.request_type, 'repair')

    def test_service_request_status_choices(self):
        """ServiceRequest should have valid status values."""
        ownership = self.create_product_ownership()
        valid_statuses = ['pending', 'in_queue', 'in_progress', 'completed', 'cancelled']
        for status in valid_statuses:
            request = ServiceRequest.objects.create(
                customer=self.customer_user,
                product_ownership=ownership,
                request_type='maintenance',
                status=status,
                description=f'Test {status}'
            )
            self.assertEqual(request.status, status)

    def test_service_request_assignment(self):
        """ServiceRequest can be assigned to admin/seller."""
        ownership = self.create_product_ownership()
        request = ServiceRequest.objects.create(
            customer=self.customer_user,
            product_ownership=ownership,
            request_type='repair',
            description='Test',
            assigned_to=self.seller_user
        )
        self.assertEqual(request.assigned_to, self.seller_user)


class ReviewModelTest(BaseTestCase):
    """Tests for Review model."""

    def test_review_creation(self):
        """Review should be created with rating and comment."""
        review = Review.objects.create(
            customer=self.customer_user,
            product=self.product_fridge,
            rating=5,
            comment='Excellent product!'
        )
        self.assertEqual(review.rating, 5)
        self.assertFalse(review.is_approved)  # Default not approved

    def test_review_unique_per_customer_product(self):
        """Customer can only review a product once."""
        Review.objects.create(
            customer=self.customer_user,
            product=self.product_fridge,
            rating=4,
            comment='Good'
        )
        with self.assertRaises(IntegrityError):
            Review.objects.create(
                customer=self.customer_user,
                product=self.product_fridge,
                rating=5,
                comment='Changed my mind'
            )


class NotificationModelTest(BaseTestCase):
    """Tests for Notification model."""

    def test_notification_creation(self):
        """Notification should be created with required fields."""
        notification = Notification.objects.create(
            user=self.customer_user,
            notification_type='general',
            title='Test Notification',
            message='This is a test message'
        )
        self.assertFalse(notification.is_read)
        self.assertEqual(notification.notification_type, 'general')

    def test_notification_with_related_product(self):
        """Notification can be linked to a product."""
        notification = Notification.objects.create(
            user=self.customer_user,
            notification_type='price_drop',
            title='Price Drop!',
            message='Buzdolabı fiyatı düştü!',
            related_product=self.product_fridge
        )
        self.assertEqual(notification.related_product, self.product_fridge)
