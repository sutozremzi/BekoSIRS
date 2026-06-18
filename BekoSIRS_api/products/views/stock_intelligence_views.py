from rest_framework import views, response, permissions
from products.models import Product, ProductAssignment
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum
from django.db.models.functions import ExtractYear, ExtractMonth

from products.ml_sales_forecaster import get_sales_forecaster


# Sipariş önerisi parametreleri (ileride ayar ekranından değiştirilebilir yapılabilir)
LEAD_TIME_MONTHS = 1.0      # Tedarikçiden malın gelme süresi (ay)
SAFETY_STOCK_DAYS = 7       # Tedarik süresi boyunca tükenmeye karşı güvenlik tamponu (gün)


def _ym_minus(year: int, month: int, k: int):
    """year-month'tan k ay geriye gider, (yıl, ay) döndürür."""
    total = (year * 12 + (month - 1)) - k
    return total // 12, total % 12 + 1


class StockIntelligenceDashboardView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        now = timezone.now()
        thirty_days_ago = now - timedelta(days=30)

        products = Product.objects.select_related('category').all()
        total_products = products.count()

        critical_alerts = []
        warning_alerts = []
        opportunities = []

        # Son 30 günlük gerçek satış (velocity için)
        recent_sales_query = ProductAssignment.objects.filter(
            assigned_at__gte=thirty_days_ago
        ).values('product_id').annotate(total_sales=Sum('quantity'))
        sales_dict = {item['product_id']: item['total_sales'] for item in recent_sales_query}

        # Son 12 ayın aylık satışları (satış tahmin modeline lag girdisi için) — tek sorgu
        twelve_months_ago = now - timedelta(days=400)
        monthly_rows = (
            ProductAssignment.objects.filter(assigned_at__gte=twelve_months_ago)
            .annotate(yr=ExtractYear('assigned_at'), mo=ExtractMonth('assigned_at'))
            .values('product_id', 'yr', 'mo')
            .annotate(q=Sum('quantity'))
        )
        sales_by_ym = {
            (r['product_id'], r['yr'] * 100 + r['mo']): float(r['q'] or 0)
            for r in monthly_rows
        }

        # Eğitilmiş satış tahmin modeli (yoksa graceful fallback'e düşeriz)
        forecaster = get_sales_forecaster()

        def _last_12_months(product_id):
            """[11 ay önce ... bu ay] sırasıyla 12 aylık satış vektörü (eskiden yeniye)."""
            vec = []
            for offset in range(11, -1, -1):
                yy, mm = _ym_minus(now.year, now.month, offset)
                vec.append(sales_by_ym.get((product_id, yy * 100 + mm), 0.0))
            return vec

        healthy_count = 0

        for p in products:
            sales_30d = sales_dict.get(p.id, 0) or 0
            category_name = p.category.name if p.category else "Genel"

            # ── Satış tahmini (mümkünse AI modeli, değilse 30 günlük velocity) ──
            predicted_monthly = None
            forecast_source = "velocity"
            last_12 = _last_12_months(p.id)
            if forecaster and forecaster.is_trained and sum(last_12) > 0:
                fc = forecaster.predict_next_n_months(
                    last_12, category_name, float(p.price or 0), now, n_months=1
                )
                if fc and fc[0]['predicted'] > 0:
                    predicted_monthly = fc[0]['predicted']
                    forecast_source = "forecast"

            # Aylık satış beklentisi: tahmin varsa onu, yoksa son 30 günü kullan
            monthly_sales = predicted_monthly if predicted_monthly is not None else sales_30d
            velocity = monthly_sales / 30.0  # günlük satış hızı

            days_until_stockout = None
            if velocity > 0:
                days_until_stockout = p.stock / velocity

            # ── Nokta atışı sipariş önerisi ──
            # önerilen = (aylık satış × tedarik süresi) + güvenlik stoğu − mevcut stok
            safety_stock = velocity * SAFETY_STOCK_DAYS
            recommended_order_qty = max(
                0,
                int(round(monthly_sales * LEAD_TIME_MONTHS + safety_stock - p.stock))
            )
            est_cost = float(p.price) * recommended_order_qty if p.price else 0.0

            alert_data = {
                "product_id": p.id,
                "product_name": p.name,
                "brand": p.brand,
                "category": category_name,
                "current_stock": p.stock,
                "sales_last_30_days": sales_30d,
                "velocity": round(velocity, 3),
                "predicted_monthly_sales": predicted_monthly,
                "forecast_source": forecast_source,
                "days_until_stockout": days_until_stockout,
                "recommended_order_qty": recommended_order_qty,
            }

            if p.stock <= 5:
                critical_alerts.append({
                    **alert_data,
                    "urgency": "critical",
                    "message": "Stok kritik seviyede, acil müdahale gerekli.",
                    "estimated_order_cost": est_cost,
                })
            elif p.stock <= 15 and velocity > 0 and days_until_stockout and days_until_stockout < 30:
                warning_alerts.append({
                    **alert_data,
                    "urgency": "warning",
                    "message": f"Mevcut satış hızıyla {int(days_until_stockout)} gün içinde tükenecek.",
                    "estimated_order_cost": est_cost,
                })
            elif p.stock >= 20 and velocity < 0.2:
                opportunities.append({
                    **alert_data,
                    "urgency": "opportunity",
                    "message": "Yüksek atıl stok. Bir kampanya düzenlenmesi yararlı olabilir.",
                })
            else:
                healthy_count += 1

        # Gerçek en çok satanlar (Top 10)
        top_sellers = list(
            ProductAssignment.objects.filter(assigned_at__gte=thirty_days_ago)
            .values('product__name', 'product__brand')
            .annotate(sales_count=Sum('quantity'))
            .order_by('-sales_count')[:10]
        )

        # Gerçek düşük performanslılar (en az satan 10 ürün)
        product_sales_list = []
        for p in products:
            sales = sales_dict.get(p.id, 0)
            product_sales_list.append({
                "name": p.name,
                "brand": p.brand,
                "stock": p.stock,
                "sales_count": sales,
            })
        product_sales_list.sort(key=lambda x: (x["sales_count"], -x["stock"]))
        low_performers = product_sales_list[:10]

        data = {
            "summary": {
                "critical_count": len(critical_alerts),
                "warning_count": len(warning_alerts),
                "opportunity_count": len(opportunities),
                "healthy_count": healthy_count,
                "total_products": total_products,
                "forecast_model_active": bool(forecaster and forecaster.is_trained),
            },
            "critical_alerts": sorted(critical_alerts, key=lambda x: x['current_stock']),
            "warning_alerts": sorted(warning_alerts, key=lambda x: x['days_until_stockout'] or 999),
            "opportunities": sorted(opportunities, key=lambda x: x['current_stock'], reverse=True),
            "top_sellers": top_sellers,
            "low_performers": low_performers,
        }
        return response.Response(data)
