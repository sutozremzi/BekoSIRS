#!/usr/bin/env python3
"""
BekoSIRS Backend - Load Testing Script
Uses locust for load testing

Installation:
    pip install locust

Usage:
    locust -f testing/load_test.py --host=http://localhost:8000

    Then open: http://localhost:8089
"""

from locust import HttpUser, task, between
import random
import json


class BekoSIRSUser(HttpUser):
    """Simulates a typical BekoSIRS user"""

    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks

    def on_start(self):
        """Called when a simulated user starts"""
        # Try to login (if you have test credentials)
        self.login()

    def login(self):
        """Login to get JWT token"""
        response = self.client.post("/api/v1/token/", json={
            "username": "testuser",
            "password": "testpass123",
            "platform": "web"
        })

        if response.status_code == 200:
            data = response.json()
            self.token = data.get("access")
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            self.headers = {}

    @task(10)
    def view_products(self):
        """List products - most common operation"""
        self.client.get("/api/v1/products/", headers=self.headers)

    @task(5)
    def view_product_detail(self):
        """View a specific product"""
        product_id = random.randint(1, 100)
        self.client.get(f"/api/v1/products/{product_id}/", headers=self.headers)

    @task(3)
    def search_products(self):
        """Search for products"""
        search_terms = ["Buzdolabı", "Çamaşır Makinesi", "Fırın", "Televizyon"]
        term = random.choice(search_terms)
        self.client.get(f"/api/v1/products/?search={term}", headers=self.headers)

    @task(2)
    def view_categories(self):
        """List categories"""
        self.client.get("/api/v1/categories/", headers=self.headers)

    @task(1)
    def view_recommendations(self):
        """Get product recommendations"""
        self.client.get("/api/v1/recommendations/", headers=self.headers)

    @task(1)
    def view_notifications(self):
        """Check notifications"""
        self.client.get("/api/v1/notifications/", headers=self.headers)


class AdminUser(HttpUser):
    """Simulates admin user creating products"""

    wait_time = between(5, 10)

    def on_start(self):
        """Login as admin"""
        response = self.client.post("/api/v1/token/", json={
            "username": "admin",
            "password": "admin123",
            "platform": "web"
        })

        if response.status_code == 200:
            data = response.json()
            self.token = data.get("access")
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            self.headers = {}

    @task(1)
    def create_product(self):
        """Create a new product (heavy operation)"""
        product_data = {
            "name": f"Test Product {random.randint(1, 1000)}",
            "brand": "Beko",
            "price": str(random.uniform(1000, 10000)),
            "stock": random.randint(0, 100),
            "category": 1
        }
        self.client.post("/api/v1/products/", json=product_data, headers=self.headers)

    @task(2)
    def dashboard_summary(self):
        """View dashboard (complex query)"""
        self.client.get("/api/v1/dashboard/summary/", headers=self.headers)


# Load test scenarios
class QuickTest(HttpUser):
    """Quick smoke test - low load"""
    tasks = [BekoSIRSUser]
    weight = 1


class HeavyLoad(HttpUser):
    """Heavy load test - simulates many users"""
    tasks = [BekoSIRSUser, AdminUser]
    weight = 9


if __name__ == "__main__":
    print("""
    BekoSIRS Load Testing
    =====================

    Run with:
        locust -f testing/load_test.py --host=http://localhost:8000

    Recommended test scenarios:

    1. Smoke Test (Quick):
       - Users: 10
       - Spawn rate: 1/sec
       - Duration: 1 minute

    2. Load Test (Normal):
       - Users: 100
       - Spawn rate: 10/sec
       - Duration: 5 minutes

    3. Stress Test (Peak):
       - Users: 500
       - Spawn rate: 50/sec
       - Duration: 10 minutes

    4. Spike Test:
       - Users: 1000
       - Spawn rate: 100/sec
       - Duration: 2 minutes

    Monitor:
    - Response times (should be <200ms for 95th percentile)
    - Error rate (should be <1%)
    - Throughput (requests/second)
    - Database connections
    - Memory usage
    """)
