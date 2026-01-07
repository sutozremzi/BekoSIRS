import pytest
from django.urls import reverse
from rest_framework import status
from products.models import Delivery, DeliveryRoute
from datetime import date
from .conftest import APITestCase

@pytest.mark.django_db
class TestDeliverySystem(APITestCase):
    def setUp(self):
        super().setUp()
        
        # Django Rest Framework IsAdminUser permission checks for is_staff
        self.admin_user.is_staff = True
        self.admin_user.save()
        
        # URL'ler
        self.list_url = reverse('delivery-list')
        self.optimize_url = reverse('delivery-route-optimize')

    def test_create_delivery_as_admin(self):
        self.authenticate_admin()
        data = {
            'customer_id': self.customer_user.id,
            'address': 'Test Adresi',
            'delivery_date': str(date.today()),
            'notes': 'Test Notu',
            'status': 'pending'
        }
        response = self.client.post(self.list_url, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert Delivery.objects.count() == 1
        assert Delivery.objects.get().customer == self.customer_user

    def test_customer_cannot_create_delivery(self):
        self.authenticate_customer()
        data = {
            'customer_id': self.customer_user.id,
            'address': 'Test',
            'delivery_date': str(date.today())
        }
        response = self.client.post(self.list_url, data)
        # Sadece adminler teslimat oluşturabilir
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_route_optimization_logic(self):
        self.authenticate_admin()
        
        # 2 Farklı noktada teslimat oluşturalım
        from products.models import CustomUser
        customer2 = CustomUser.objects.create_user(
            username='c2', 
            password='123', 
            email='c2@t.com', 
            role='customer',
            address_lat=35.3323,
            address_lng=33.3184
        )

        d1 = Delivery.objects.create(
            customer=self.customer_user,
            address='Yakın',
            address_lat=35.1900,
            address_lng=33.3850,
            delivery_date=date.today(),
            status='pending'
        )
        
        d2 = Delivery.objects.create(
            customer=customer2,
            address='Uzak',
            address_lat=35.3323,
            address_lng=33.3184,
            delivery_date=date.today(),
            status='pending'
        )
        
        data = {'date': str(date.today())}
        response = self.client.post(self.optimize_url, data)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True
        
        route = DeliveryRoute.objects.get(date=date.today())
        stops = route.stops.all().order_by('stop_order')
        
        # En yakın komşu mantığı
        assert stops[0].delivery == d1
        assert stops[1].delivery == d2
        
        d1.refresh_from_db()
        assert d1.status == 'assigned'

    def test_optimization_handles_missing_coordinates(self):
        self.authenticate_admin()
        
        Delivery.objects.create(
            customer=self.customer_user,
            address='Koordinatsız',
            address_lat=None,
            address_lng=None,
            delivery_date=date.today(),
            status='pending'
        )
        
        data = {'date': str(date.today())}
        response = self.client.post(self.optimize_url, data)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
