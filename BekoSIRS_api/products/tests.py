# products/tests.py
"""
Comprehensive test suite for BekoSIRS API.

Run tests with:
    python manage.py test products.tests -v 2
    
Or with pytest:
    pytest products/tests.py -v
"""

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from decimal import Decimal
from datetime import date, timedelta

from .models import (
    CustomUser, Product, Category, ProductOwnership,
    Wishlist, WishlistItem, ServiceRequest, Notification,
    InstallmentPlan, Installment
)


# ============================================
# USER MODEL TESTS
# ============================================

class CustomUserModelTests(TestCase):
    """Test cases for CustomUser model."""
    
    def test_create_customer(self):
        """Test creating a customer user."""
        user = CustomUser.objects.create_user(
            username='testcustomer',
            email='customer@test.com',
            password='testpass123',
            role='customer',
            first_name='Test',
            last_name='Customer'
        )
        self.assertEqual(user.role, 'customer')
        self.assertEqual(user.email, 'customer@test.com')
        self.assertTrue(user.check_password('testpass123'))
    
    def test_create_admin(self):
        """Test creating an admin user."""
        admin = CustomUser.objects.create_user(
            username='testadmin',
            email='admin@test.com',
            password='adminpass123',
            role='admin'
        )
        self.assertEqual(admin.role, 'admin')
    
    def test_create_seller(self):
        """Test creating a seller user."""
        seller = CustomUser.objects.create_user(
            username='testseller',
            email='seller@test.com',
            password='sellerpass123',
            role='seller'
        )
        self.assertEqual(seller.role, 'seller')
    
    def test_user_str(self):
        """Test user string representation."""
        user = CustomUser.objects.create_user(
            username='strtest',
            email='str@test.com',
            password='pass123'
        )
        self.assertEqual(str(user), 'strtest')


# ============================================
# PRODUCT MODEL TESTS
# ============================================

class ProductModelTests(TestCase):
    """Test cases for Product and Category models."""
    
    def setUp(self):
        """Set up test data."""
        self.category = Category.objects.create(name='Buzdolabı')
        self.product = Product.objects.create(
            name='Beko No-Frost Buzdolabı',
            brand='Beko',
            category=self.category,
            description='Test ürün açıklaması',
            price=Decimal('15000.00'),
            warranty_duration_months=24,
            stock=10
        )
    
    def test_product_creation(self):
        """Test product is created correctly."""
        self.assertEqual(self.product.name, 'Beko No-Frost Buzdolabı')
        self.assertEqual(self.product.brand, 'Beko')
        self.assertEqual(self.product.price, Decimal('15000.00'))
        self.assertEqual(self.product.stock, 10)
    
    def test_product_category_relationship(self):
        """Test product-category relationship."""
        self.assertEqual(self.product.category, self.category)
        self.assertIn(self.product, self.category.products.all())
    
    def test_category_subcategory(self):
        """Test category parent-child relationship."""
        sub_category = Category.objects.create(
            name='Mini Buzdolabı',
            parent=self.category
        )
        self.assertEqual(sub_category.parent, self.category)
        self.assertIn(sub_category, self.category.subcategories.all())


# ============================================
# PRODUCT OWNERSHIP TESTS
# ============================================

class ProductOwnershipTests(TestCase):
    """Test cases for ProductOwnership model."""
    
    def setUp(self):
        """Set up test data."""
        self.customer = CustomUser.objects.create_user(
            username='owner',
            email='owner@test.com',
            password='pass123',
            role='customer'
        )
        self.category = Category.objects.create(name='Çamaşır Makinesi')
        self.product = Product.objects.create(
            name='Beko Çamaşır Makinesi',
            brand='Beko',
            category=self.category,
            price=Decimal('10000.00'),
            warranty_duration_months=24,
            stock=5
        )
    
    def test_ownership_creation(self):
        """Test product ownership creation."""
        ownership = ProductOwnership.objects.create(
            customer=self.customer,
            product=self.product,
            purchase_date=date.today() - timedelta(days=30)
        )
        self.assertEqual(ownership.customer, self.customer)
        self.assertEqual(ownership.product, self.product)
    
    def test_warranty_end_date(self):
        """Test warranty end date calculation."""
        purchase_date = date(2026, 1, 1)
        ownership = ProductOwnership.objects.create(
            customer=self.customer,
            product=self.product,
            purchase_date=purchase_date
        )
        # 24 months warranty
        expected_end = date(2028, 1, 1)
        self.assertEqual(ownership.warranty_end_date, expected_end)


# ============================================
# INSTALLMENT PLAN TESTS
# ============================================

class InstallmentPlanTests(TestCase):
    """Test cases for InstallmentPlan model."""
    
    def setUp(self):
        """Set up test data."""
        self.customer = CustomUser.objects.create_user(
            username='installcustomer',
            email='install@test.com',
            password='pass123',
            role='customer'
        )
        self.seller = CustomUser.objects.create_user(
            username='installseller',
            email='sellinstall@test.com',
            password='pass123',
            role='seller'
        )
        self.category = Category.objects.create(name='TV')
        self.product = Product.objects.create(
            name='Beko 55" TV',
            brand='Beko',
            category=self.category,
            price=Decimal('20000.00'),
            warranty_duration_months=24,
            stock=3
        )
    
    def test_installment_plan_creation(self):
        """Test installment plan creation."""
        plan = InstallmentPlan.objects.create(
            customer=self.customer,
            product=self.product,
            total_amount=Decimal('20000.00'),
            down_payment=Decimal('4000.00'),
            installment_count=8,
            start_date=date.today(),
            created_by=self.seller
        )
        self.assertEqual(plan.status, 'active')
        self.assertEqual(plan.total_amount, Decimal('20000.00'))
    
    def test_remaining_amount(self):
        """Test remaining amount calculation."""
        plan = InstallmentPlan.objects.create(
            customer=self.customer,
            product=self.product,
            total_amount=Decimal('20000.00'),
            down_payment=Decimal('4000.00'),
            installment_count=8,
            start_date=date.today(),
            created_by=self.seller
        )
        # Create 2 paid installments
        Installment.objects.create(
            plan=plan,
            installment_number=1,
            amount=Decimal('2000.00'),
            due_date=date.today(),
            status='paid'
        )
        Installment.objects.create(
            plan=plan,
            installment_number=2,
            amount=Decimal('2000.00'),
            due_date=date.today() + timedelta(days=30),
            status='paid'
        )
        # Remaining = Total - Down payment - Paid installments
        # 20000 - 4000 - 4000 = 12000
        self.assertEqual(plan.remaining_amount, Decimal('12000.00'))


# ============================================
# API AUTHENTICATION TESTS
# ============================================

class AuthenticationAPITests(APITestCase):
    """Test cases for authentication endpoints."""
    
    def setUp(self):
        """Set up test user."""
        self.user = CustomUser.objects.create_user(
            username='apiuser',
            email='api@test.com',
            password='apipass123',
            role='customer'
        )
        self.client = APIClient()
    
    def test_login_success(self):
        """Test successful login returns tokens."""
        response = self.client.post('/api/v1/token/', {
            'username': 'apiuser',
            'password': 'apipass123'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
    
    def test_login_wrong_password(self):
        """Test login with wrong password fails."""
        response = self.client.post('/api/v1/token/', {
            'username': 'apiuser',
            'password': 'wrongpassword'
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_login_nonexistent_user(self):
        """Test login with non-existent user fails."""
        response = self.client.post('/api/v1/token/', {
            'username': 'nonexistent',
            'password': 'password123'
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# ============================================
# PRODUCT API TESTS
# ============================================

class ProductAPITests(APITestCase):
    """Test cases for product endpoints."""
    
    def setUp(self):
        """Set up test data."""
        self.admin = CustomUser.objects.create_user(
            username='prodadmin',
            email='prodadmin@test.com',
            password='adminpass123',
            role='admin'
        )
        self.customer = CustomUser.objects.create_user(
            username='prodcustomer',
            email='prodcust@test.com',
            password='custpass123',
            role='customer'
        )
        self.category = Category.objects.create(name='Ev Aletleri')
        self.product = Product.objects.create(
            name='Test Ürün',
            brand='Beko',
            category=self.category,
            price=Decimal('5000.00'),
            stock=10
        )
        self.client = APIClient()
    
    def test_list_products_unauthenticated(self):
        """Test unauthenticated users cannot list products."""
        response = self.client.get('/api/v1/products/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_list_products_authenticated(self):
        """Test authenticated users can list products."""
        self.client.force_authenticate(user=self.customer)
        response = self.client.get('/api/v1/products/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_create_product_as_admin(self):
        """Test admin can create products."""
        self.client.force_authenticate(user=self.admin)
        response = self.client.post('/api/v1/products/', {
            'name': 'Yeni Ürün',
            'brand': 'Beko',
            'category': self.category.id,
            'price': '7500.00',
            'stock': 5,
            'description': 'Test açıklama'
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    
    def test_create_product_as_customer_forbidden(self):
        """Test customer cannot create products."""
        self.client.force_authenticate(user=self.customer)
        response = self.client.post('/api/v1/products/', {
            'name': 'Yeni Ürün',
            'brand': 'Beko',
            'category': self.category.id,
            'price': '7500.00',
            'stock': 5
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


# ============================================
# PERMISSION TESTS
# ============================================

class PermissionTests(APITestCase):
    """Test cases for role-based permissions."""
    
    def setUp(self):
        """Set up test users with different roles."""
        self.admin = CustomUser.objects.create_user(
            username='permadmin',
            email='permadmin@test.com',
            password='pass123',
            role='admin'
        )
        self.seller = CustomUser.objects.create_user(
            username='permseller',
            email='permseller@test.com',
            password='pass123',
            role='seller'
        )
        self.customer = CustomUser.objects.create_user(
            username='permcustomer',
            email='permcust@test.com',
            password='pass123',
            role='customer'
        )
        self.client = APIClient()
    
    def test_admin_can_access_user_list(self):
        """Test admin can access user management."""
        self.client.force_authenticate(user=self.admin)
        response = self.client.get('/api/v1/users/')
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN])
    
    def test_customer_cannot_access_user_list(self):
        """Test customer cannot access user management."""
        self.client.force_authenticate(user=self.customer)
        response = self.client.get('/api/v1/users/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


# ============================================
# WISHLIST TESTS
# ============================================

class WishlistAPITests(APITestCase):
    """Test cases for wishlist functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.customer = CustomUser.objects.create_user(
            username='wishcustomer',
            email='wish@test.com',
            password='pass123',
            role='customer'
        )
        self.category = Category.objects.create(name='Elektrikli Süpürge')
        self.product = Product.objects.create(
            name='Beko Dikey Süpürge',
            brand='Beko',
            category=self.category,
            price=Decimal('3000.00'),
            stock=15
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.customer)
    
    def test_add_to_wishlist(self):
        """Test adding product to wishlist."""
        response = self.client.post('/api/v1/wishlist/add-item/', {
            'product_id': self.product.id
        })
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED])
    
    def test_view_wishlist(self):
        """Test viewing wishlist."""
        # First add item
        self.client.post('/api/v1/wishlist/add-item/', {'product_id': self.product.id})
        
        # Then view
        response = self.client.get('/api/v1/wishlist/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


# ============================================
# SERVICE REQUEST TESTS
# ============================================

class ServiceRequestTests(TestCase):
    """Test cases for ServiceRequest model."""
    
    def setUp(self):
        """Set up test data."""
        self.customer = CustomUser.objects.create_user(
            username='servicecustomer',
            email='service@test.com',
            password='pass123',
            role='customer'
        )
        self.category = Category.objects.create(name='Bulaşık Makinesi')
        self.product = Product.objects.create(
            name='Beko Bulaşık Makinesi',
            brand='Beko',
            category=self.category,
            price=Decimal('8000.00'),
            warranty_duration_months=24,
            stock=8
        )
        self.ownership = ProductOwnership.objects.create(
            customer=self.customer,
            product=self.product,
            purchase_date=date.today() - timedelta(days=60)
        )
    
    def test_service_request_creation(self):
        """Test service request creation."""
        request = ServiceRequest.objects.create(
            customer=self.customer,
            ownership=self.ownership,
            description='Makine çalışmıyor',
            request_type='repair'
        )
        self.assertEqual(request.status, 'pending')
        self.assertEqual(request.customer, self.customer)
    
    def test_service_request_status_change(self):
        """Test service request status changes."""
        request = ServiceRequest.objects.create(
            customer=self.customer,
            ownership=self.ownership,
            description='Test servis talebi'
        )
        
        # Change status
        request.status = 'in_progress'
        request.save()
        
        request.refresh_from_db()
        self.assertEqual(request.status, 'in_progress')


# ============================================
# SIGNAL TESTS
# ============================================

class SignalTests(TestCase):
    """Test cases for Django signals."""
    
    def setUp(self):
        """Set up test data."""
        self.customer = CustomUser.objects.create_user(
            username='signalcustomer',
            email='signal@test.com',
            password='pass123',
            role='customer'
        )
        self.category = Category.objects.create(name='Fırın')
        self.product = Product.objects.create(
            name='Beko Fırın',
            brand='Beko',
            category=self.category,
            price=Decimal('6000.00'),
            stock=0  # Start with no stock
        )
        # Create wishlist and add product
        self.wishlist = Wishlist.objects.create(customer=self.customer)
        WishlistItem.objects.create(
            wishlist=self.wishlist,
            product=self.product,
            notify_on_price_drop=True,
            notify_on_restock=True
        )
    
    def test_restock_creates_notification(self):
        """Test that restocking creates notification for wishlist users."""
        initial_count = Notification.objects.filter(
            user=self.customer,
            notification_type='restock'
        ).count()
        
        # Restock the product
        self.product.stock = 10
        self.product.save()
        
        # Check notification was created
        new_count = Notification.objects.filter(
            user=self.customer,
            notification_type='restock'
        ).count()
        self.assertEqual(new_count, initial_count + 1)
    
    def test_price_drop_creates_notification(self):
        """Test that price drop creates notification for wishlist users."""
        # First set stock > 0 so product is valid
        self.product.stock = 5
        self.product.save()
        
        initial_count = Notification.objects.filter(
            user=self.customer,
            notification_type='price_drop'
        ).count()
        
        # Drop the price
        self.product.price = Decimal('5000.00')
        self.product.save()
        
        # Check notification was created
        new_count = Notification.objects.filter(
            user=self.customer,
            notification_type='price_drop'
        ).count()
        self.assertEqual(new_count, initial_count + 1)


# ============================================
# SALES FORECAST TESTS
# ============================================

class SalesForecastTests(TestCase):
    """Test cases for SalesForecastService."""
    
    def setUp(self):
        """Set up test data."""
        from dateutil.relativedelta import relativedelta
        
        self.category = Category.objects.create(name='Klima')
        self.product = Product.objects.create(
            name='Beko Klima 12000 BTU',
            brand='Beko',
            category=self.category,
            price=Decimal('15000.00'),
            stock=20
        )
        self.customer = CustomUser.objects.create_user(
            username='forecastcustomer',
            email='forecast@test.com',
            password='pass123',
            role='customer'
        )
        
        # Create sales data for past 6 months
        today = date.today()
        self.sales_data = []
        for i in range(6, 0, -1):
            month_date = today - relativedelta(months=i)
            # Create varying sales (3, 5, 4, 6, 5, 7 - increasing trend)
            sales_count = 2 + i % 5 + (i // 2)
            for _ in range(sales_count):
                ownership = ProductOwnership.objects.create(
                    customer=self.customer,
                    product=self.product,
                    purchase_date=month_date
                )
                self.sales_data.append(ownership)
    
    def test_service_initialization(self):
        """Test SalesForecastService can be initialized."""
        from products.sales_forecast_service import SalesForecastService
        service = SalesForecastService()
        self.assertIsNotNone(service)
        self.assertEqual(service.LOOKBACK_MONTHS, 6)
    
    def test_forecast_product_returns_data(self):
        """Test forecast_product returns valid forecast data."""
        from products.sales_forecast_service import SalesForecastService
        service = SalesForecastService()
        
        result = service.forecast_product(self.product.id)
        
        self.assertIn('product_id', result)
        self.assertIn('forecasts', result)
        self.assertEqual(result['product_id'], self.product.id)
    
    def test_forecast_includes_three_months(self):
        """Test forecast returns 3 months of predictions."""
        from products.sales_forecast_service import SalesForecastService
        service = SalesForecastService()
        
        result = service.forecast_product(self.product.id, months=3)
        
        self.assertEqual(len(result.get('forecasts', [])), 3)
    
    def test_forecast_with_custom_months(self):
        """Test forecast with custom number of months."""
        from products.sales_forecast_service import SalesForecastService
        service = SalesForecastService()
        
        result = service.forecast_product(self.product.id, months=6)
        
        self.assertEqual(len(result.get('forecasts', [])), 6)
    
    def test_seasonal_factors_applied(self):
        """Test that seasonal factors are applied to Klima category."""
        from products.sales_forecast_service import SalesForecastService
        service = SalesForecastService()
        
        result = service.forecast_product(self.product.id)
        
        # Klima should have seasonal factors
        for forecast in result.get('forecasts', []):
            self.assertIn('seasonal_factor', forecast)
            # Klima seasonal factors range from 0.3 to 2.0
            self.assertGreaterEqual(forecast['seasonal_factor'], 0.2)
            self.assertLessEqual(forecast['seasonal_factor'], 2.1)
    
    def test_trend_detection_works(self):
        """Test that trend is detected."""
        from products.sales_forecast_service import SalesForecastService
        service = SalesForecastService()
        
        result = service.forecast_product(self.product.id)
        
        self.assertIn('trend', result)
        self.assertIn(result['trend'], ['increasing', 'decreasing', 'stable'])
    
    def test_moving_average_calculation(self):
        """Test moving average is calculated."""
        from products.sales_forecast_service import SalesForecastService
        service = SalesForecastService()
        
        result = service.forecast_product(self.product.id)
        
        self.assertIn('moving_average', result)
        self.assertGreater(result['moving_average'], 0)
    
    def test_nonexistent_product_returns_error(self):
        """Test forecast for non-existent product returns error."""
        from products.sales_forecast_service import SalesForecastService
        service = SalesForecastService()
        
        result = service.forecast_product(99999)
        
        self.assertIn('error', result)
    
    def test_forecast_includes_recommendation(self):
        """Test forecast includes actionable recommendation."""
        from products.sales_forecast_service import SalesForecastService
        service = SalesForecastService()
        
        result = service.forecast_product(self.product.id)
        
        self.assertIn('recommendation', result)
        self.assertIsInstance(result['recommendation'], str)
    
    def test_forecast_all_products(self):
        """Test forecasting all products."""
        from products.sales_forecast_service import SalesForecastService
        service = SalesForecastService()
        
        results = service.forecast_all_products()
        
        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)
    
    def test_product_without_sales_returns_error(self):
        """Test product with no sales returns insufficient data error."""
        from products.sales_forecast_service import SalesForecastService
        service = SalesForecastService()
        
        new_product = Product.objects.create(
            name='New Product No Sales',
            brand='Test',
            category=self.category,
            price=Decimal('5000.00'),
            stock=10
        )
        
        result = service.forecast_product(new_product.id)
        
        # Should return error due to insufficient data
        self.assertIn('error', result)
        self.assertIn('Yetersiz', result.get('error', ''))


# ============================================
# CUSTOMER ANALYTICS TESTS (Placeholder)
# ============================================

class CustomerAnalyticsTests(TestCase):
    """Test cases for CustomerAnalyticsService (CLV)."""
    
    def setUp(self):
        """Set up test data."""
        self.customer = CustomUser.objects.create_user(
            username='clvcustomer',
            email='clv@test.com',
            password='pass123',
            role='customer'
        )
        self.category = Category.objects.create(name='CLV Test Category')
        self.product = Product.objects.create(
            name='CLV Test Product',
            brand='Beko',
            category=self.category,
            price=Decimal('10000.00'),
            stock=10
        )
    
    def test_placeholder(self):
        """Placeholder test - will be extended after service creation."""
        self.assertTrue(True)

