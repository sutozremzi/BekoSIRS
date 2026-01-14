from rest_framework import views, response, permissions
from products.models import Product
import random

class StockIntelligenceDashboardView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        # Retrieve real products if possible, or mock
        products = Product.objects.all()[:20]
        
        critical_alerts = []
        opportunities = []
        
        # Generate mock intelligence based on real products
        for p in products:
            if p.stock < 5:
                critical_alerts.append({
                    "product_id": p.id,
                    "product_name": p.name,
                    "brand": p.brand,
                    "category": p.category.name if p.category else "Genel",
                    "current_stock": p.stock,
                    "sales_last_30_days": random.randint(10, 50),
                    "velocity": random.uniform(0.5, 2.0),
                    "days_until_stockout": random.randint(1, 5),
                    "recommended_order_qty": 20,
                    "urgency": "critical",
                    "message": "Stok tükenmek üzere, acil sipariş gerekli.",
                    "estimated_order_cost": float(p.price) * 20 * 0.8  # Approx cost
                })
            elif p.stock > 50:
                opportunities.append({
                    "product_id": p.id,
                    "product_name": p.name,
                    "brand": p.brand,
                    "message": "Yüksek stok seviyesi, kampanya önerilir.",
                    "urgency": "opportunity"
                })

        # Fill with mock if empty
        if not critical_alerts:
             critical_alerts.append({
                    "product_id": 999,
                    "product_name": "Mock Bulaşık Makinesi",
                    "brand": "Beko",
                    "category": "Beyaz Eşya",
                    "current_stock": 2,
                    "sales_last_30_days": 15,
                    "velocity": 1.2,
                    "days_until_stockout": 2,
                    "recommended_order_qty": 10,
                    "urgency": "critical",
                    "message": "Demo: Stok kritik seviyede.",
                    "estimated_order_cost": 50000
             })

        data = {
            "summary": {
                "critical_count": len(critical_alerts),
                "warning_count": random.randint(2, 5),
                "opportunity_count": len(opportunities),
                "healthy_count": Product.objects.count(),
                "total_products": Product.objects.count(),
            },
            "critical_alerts": critical_alerts,
            "opportunities": opportunities,
            "top_sellers": [
                {"product__name": "Buzdolabı XL", "product__brand": "Beko", "sales_count": 120},
                {"product__name": "TV 55 Inch", "product__brand": "Beko", "sales_count": 85},
            ],
            "low_performers": [
                {"name": "Eski Ütü", "brand": "Beko", "stock": 45}
            ]
        }
        return response.Response(data)
