import pytest
from django.urls import reverse
from rest_framework import status
from products.models import CustomUser
from .conftest import APITestCase

@pytest.mark.django_db
class TestProfileAddress(APITestCase):
    def setUp(self):
        super().setUp()
        # self.customer_user APITestCase içinde mevcut
        self.profile_url = reverse('user-profile') 

    def test_get_profile_includes_address_fields(self):
        self.authenticate_customer()
        response = self.client.get(self.profile_url)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'address' in response.data
        assert 'address_city' in response.data
        assert 'address_lat' in response.data
        assert 'address_lng' in response.data

    def test_update_profile_address_fields(self):
        self.authenticate_customer()
        
        data = {
            'first_name': 'Yeni',
            'last_name': 'İsim',
            'address': 'Gönyeli, Atatürk Cad, No:5',
            'address_city': 'Lefkoşa',
            'address_lat': 35.2000,
            'address_lng': 33.3000
        }
        
        response = self.client.patch(self.profile_url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        self.customer_user.refresh_from_db()
        
        assert self.customer_user.first_name == 'Yeni'
        assert self.customer_user.address == 'Gönyeli, Atatürk Cad, No:5'
        assert self.customer_user.address_city == 'Lefkoşa'
        # DecimalField olduğu için str karşılaştırması veya approx gerekebilir
        assert float(self.customer_user.address_lat) == 35.2000
        assert float(self.customer_user.address_lng) == 33.3000

    def test_partial_update_only_city(self):
        self.authenticate_customer()
        
        # Önce bir adres set edelim
        self.customer_user.address = "Eski Adres"
        self.customer_user.address_city = "Girne"
        self.customer_user.save()
        
        # Sadece şehri değiştirelim
        data = {'address_city': 'Gazimağusa'}
        response = self.client.patch(self.profile_url, data, format='json')
        
        self.customer_user.refresh_from_db()
        assert self.customer_user.address_city == 'Gazimağusa'
        assert self.customer_user.address == "Eski Adres" # Değişmemeli
