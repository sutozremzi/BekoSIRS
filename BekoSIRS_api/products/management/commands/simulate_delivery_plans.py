import uuid
from datetime import date
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from products.models import (
    Area,
    Category,
    CustomUser,
    CustomerAddress,
    Delivery,
    DeliveryRoute,
    DeliveryRouteStop,
    DepotLocation,
    District,
    Product,
    ProductAssignment,
)
from products.services.auto_planner import approve_plan, generate_auto_plan, recalculate_route_metrics


class Command(BaseCommand):
    help = "Run delivery planning simulations and generate a PDF report."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            default=None,
            help="PDF output path. Defaults to reports/delivery_simulation_report.pdf",
        )

    def handle(self, *args, **options):
        self.prefix = f"sim-{uuid.uuid4().hex[:8]}"
        self.category = None
        self.product_counter = 0

        scenarios = [
            self.scenario_same_customer_many_products,
            self.scenario_mixed_districts_active_days,
            self.scenario_passive_day_distribution,
            self.scenario_existing_route_new_product,
            self.scenario_missing_coordinates,
            self.scenario_capacity_split,
        ]

        results = []
        for scenario in scenarios:
            with transaction.atomic():
                result = scenario()
                results.append(result)
                transaction.set_rollback(True)

        output_path = options["output"]
        if output_path:
            pdf_path = Path(output_path)
        else:
            pdf_path = Path.cwd() / "reports" / "delivery_simulation_report.pdf"
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        self.write_pdf(results, pdf_path)

        passed = sum(1 for item in results if item["status"] == "PASS")
        failed = len(results) - passed
        self.stdout.write(self.style.SUCCESS(f"Simulasyon tamamlandi: {passed} basarili, {failed} basarisiz"))
        self.stdout.write(self.style.SUCCESS(f"PDF raporu: {pdf_path}"))

    def ensure_base_data(self):
        if self.category is None:
            self.category = Category.objects.create(name=f"{self.prefix}-Kategori")
        depot = DepotLocation.objects.filter(is_default=True).first()
        if not depot:
            depot = DepotLocation.objects.create(
                name=f"{self.prefix}-Lefkoşa Depo",
                latitude=35.1856,
                longitude=33.3823,
                is_default=True,
            )
        return depot

    def create_district(self, name, lat, lng):
        district = District.objects.create(name=f"{self.prefix}-{name}", center_lat=lat, center_lng=lng)
        area = Area.objects.create(district=district, name=f"{name} Merkez")
        return district, area

    def create_customer(self, label, district, area, lat=None, lng=None):
        suffix = uuid.uuid4().hex[:8]
        user = CustomUser.objects.create_user(
            username=f"{self.prefix}-{label}-{suffix}",
            email=f"{self.prefix}-{label}-{suffix}@example.com",
            password="testpass123",
            first_name=label.split("-")[0].title(),
            last_name="Test",
            role="customer",
            phone_number=f"9{suffix[:7]}",
        )
        CustomerAddress.objects.create(
            user=user,
            district=district,
            area=area,
            open_address=f"{label} test adresi",
            latitude=lat,
            longitude=lng,
        )
        return user

    def create_customer_without_coords(self, label):
        suffix = uuid.uuid4().hex[:8]
        return CustomUser.objects.create_user(
            username=f"{self.prefix}-{label}-{suffix}",
            email=f"{self.prefix}-{label}-{suffix}@example.com",
            password="testpass123",
            first_name=label.title(),
            last_name="Koordinatsız",
            role="customer",
            phone_number=f"8{suffix[:7]}",
        )

    def create_product(self, name):
        self.product_counter += 1
        return Product.objects.create(
            name=f"{name} {self.product_counter}",
            brand="Beko",
            category=self.category,
            price=10000,
            model_code=f"{self.prefix}-P{self.product_counter}",
            stock=100,
        )

    def create_assignment(self, customer, product=None):
        product = product or self.create_product("Test Ürün")
        return ProductAssignment.objects.create(customer=customer, product=product, quantity=1, status="PLANNED")

    def approve(self, plan, depot):
        result = approve_plan({"days": plan.get("days", []), "depot_id": depot.id})
        route_ids = [item["route_id"] for item in result.get("created_routes", [])]
        routes = list(DeliveryRoute.objects.filter(id__in=route_ids).prefetch_related("stops"))
        return result, routes

    def result(self, name, passed, metrics, analysis):
        return {
            "name": name,
            "status": "PASS" if passed else "FAIL",
            "metrics": metrics,
            "analysis": analysis,
        }

    def scenario_same_customer_many_products(self):
        depot = self.ensure_base_data()
        district, area = self.create_district("Güzelyurt", 35.1990054, 32.9899666)
        customer = self.create_customer("ahu", district, area, 35.1990054, 32.9899666)
        assignments = [self.create_assignment(customer) for _ in range(3)]

        plan = generate_auto_plan(date(2026, 5, 8), allowed_weekdays=[0, 2, 4], max_hours_per_day=8, depot_id=depot.id, assignment_ids=[a.id for a in assignments])
        _, routes = self.approve(plan, depot)
        route = routes[0] if routes else None
        deliveries = Delivery.objects.filter(assignment_id__in=[a.id for a in assignments])
        same_route = route and deliveries.filter(route_stop__route=route).count() == 3
        total_km = float(route.total_distance_km or 0) if route else 0
        zero_same_address = DeliveryRouteStop.objects.filter(route=route, distance_from_previous_km=0).count() >= 2 if route else False

        return self.result(
            "Aynı müşteriye 3 ürün",
            bool(same_route and total_km > 0 and zero_same_address),
            {
                "Teslimat": "3 ürün / 1 müşteri",
                "Rota": f"{route.id if route else '-'} / {route.date if route else '-'}",
                "Toplam km": f"{total_km:.2f}",
                "Durak sayısı": route.stops.count() if route else 0,
            },
            "Aynı müşteriye ait ürünler aynı rota ve aynı teslimat gününde toplandı; aynı adresteki ek ürünlerin ara mesafesi 0 km kaldı.",
        )

    def scenario_mixed_districts_active_days(self):
        depot = self.ensure_base_data()
        lef, lef_area = self.create_district("Lefkoşa", 35.1856, 33.3823)
        gir, gir_area = self.create_district("Girne", 35.3362494, 33.3161282)
        customers = [
            self.create_customer("lef-1", lef, lef_area, 35.1856, 33.3823),
            self.create_customer("lef-2", lef, lef_area, 35.1956, 33.3923),
            self.create_customer("gir-1", gir, gir_area, 35.3362494, 33.3161282),
            self.create_customer("gir-2", gir, gir_area, 35.33, 33.32),
        ]
        assignments = [self.create_assignment(customer) for customer in customers]

        plan = generate_auto_plan(date(2026, 5, 8), allowed_weekdays=[0, 2, 4], max_hours_per_day=8, depot_id=depot.id, assignment_ids=[a.id for a in assignments])
        _, routes = self.approve(plan, depot)
        allowed_ok = all(route.date.weekday() in [0, 2, 4] for route in routes)
        total_km = sum(float(route.total_distance_km or 0) for route in routes)

        return self.result(
            "Karışık ilçeler ve aktif günler",
            bool(routes and allowed_ok and total_km > 0),
            {
                "Aktif günler": "Pzt, Çar, Cum",
                "Rota sayısı": len(routes),
                "Toplam km": f"{total_km:.2f}",
                "Plan tarihleri": ", ".join(str(route.date) for route in routes),
            },
            "Plan motoru teslimatları yalnızca aktif günlere yerleştirdi ve gerçek koordinatlarla rota km hesapladı.",
        )

    def scenario_passive_day_distribution(self):
        depot = self.ensure_base_data()
        district, area = self.create_district("Mağusa", 35.1250, 33.9500)
        assignments = [
            self.create_assignment(self.create_customer(f"magusa-{idx}", district, area, 35.1250 + idx * 0.01, 33.9500 + idx * 0.01))
            for idx in range(4)
        ]

        plan = generate_auto_plan(date(2026, 5, 11), allowed_weekdays=[2, 4], max_hours_per_day=8, depot_id=depot.id, assignment_ids=[a.id for a in assignments])
        _, routes = self.approve(plan, depot)
        passive_ok = all(route.date.weekday() != 1 for route in routes)

        return self.result(
            "Salı pasif, aktif güne kaydırma",
            bool(routes and passive_ok),
            {
                "Pasif gün": "Salı",
                "Aktif günler": "Çar, Cum",
                "Plan tarihleri": ", ".join(str(route.date) for route in routes),
            },
            "Salı kapalı olduğunda teslimatlar ilk uygun aktif güne kaydırıldı.",
        )

    def scenario_existing_route_new_product(self):
        depot = self.ensure_base_data()
        district, area = self.create_district("Güzelyurt-2", 35.1990054, 32.9899666)
        customer = self.create_customer("mevcut-musteri", district, area, 35.1990054, 32.9899666)
        old_assignment = self.create_assignment(customer)
        route = DeliveryRoute.objects.create(
            date=date(2026, 5, 13),
            store_address=depot.name,
            store_lat=depot.latitude,
            store_lng=depot.longitude,
            status="PLANNED",
        )
        old_delivery = Delivery.objects.create(
            assignment=old_assignment,
            scheduled_date=route.date,
            address_lat=35.1990054,
            address_lng=32.9899666,
            status="WAITING",
            depot=depot,
        )
        DeliveryRouteStop.objects.create(route=route, delivery=old_delivery, stop_order=1)
        old_assignment.status = "SCHEDULED"
        old_assignment.save(update_fields=["status"])
        recalculate_route_metrics(route)

        new_assignment = self.create_assignment(customer)
        plan = generate_auto_plan(date(2026, 5, 8), allowed_weekdays=[0, 2, 4], max_hours_per_day=8, depot_id=depot.id, assignment_ids=[new_assignment.id])
        self.approve(plan, depot)
        route.refresh_from_db()
        recalculate_route_metrics(route)

        route_stop_count = route.stops.count()
        new_delivery = Delivery.objects.filter(assignment=new_assignment, route_stop__route=route).first()

        return self.result(
            "Mevcut rotadaki müşteriye yeni ürün",
            bool(new_delivery and route_stop_count == 2 and float(route.total_distance_km or 0) > 0),
            {
                "Mevcut rota": f"{route.id} / {route.date}",
                "Yeni teslimat aynı rotada": "Evet" if new_delivery else "Hayır",
                "Durak sayısı": route_stop_count,
                "Toplam km": f"{float(route.total_distance_km or 0):.2f}",
            },
            "Yeni gelen ürün, müşterinin açık teslimat rotasına eklendi; ayrı güne veya ayrı rotaya bölünmedi.",
        )

    def scenario_missing_coordinates(self):
        depot = self.ensure_base_data()
        customer = self.create_customer_without_coords("koordinatsiz")
        assignment = self.create_assignment(customer)

        plan = generate_auto_plan(date(2026, 5, 8), allowed_weekdays=[0, 2, 4], max_hours_per_day=8, depot_id=depot.id, assignment_ids=[assignment.id])
        no_coords = plan.get("warnings", {}).get("no_coordinates", [])

        return self.result(
            "Koordinatı eksik müşteri",
            assignment.id in no_coords and not plan.get("days"),
            {
                "Planlanan gün": len(plan.get("days", [])),
                "Koordinat uyarısı": len(no_coords),
            },
            "Koordinatı olmayan müşteri rota dışı bırakıldı ve uyarı listesine eklendi.",
        )

    def scenario_capacity_split(self):
        depot = self.ensure_base_data()
        district, area = self.create_district("Yoğun Bölge", 35.2500, 33.3000)
        assignments = []
        for idx in range(12):
            customer = self.create_customer(f"yogun-{idx}", district, area, 35.25 + idx * 0.005, 33.30 + idx * 0.005)
            assignments.append(self.create_assignment(customer))

        plan = generate_auto_plan(date(2026, 5, 8), allowed_weekdays=[0, 2, 4], max_hours_per_day=8, depot_id=depot.id, assignment_ids=[a.id for a in assignments])
        _, routes = self.approve(plan, depot)
        max_stops = max((route.stops.count() for route in routes), default=0)

        return self.result(
            "Yoğun hafta kapasite bölme",
            len(routes) >= 2 and max_stops <= 10,
            {
                "Teslimat sayısı": len(assignments),
                "Rota sayısı": len(routes),
                "En yoğun rota": max_stops,
                "Plan tarihleri": ", ".join(str(route.date) for route in routes),
            },
            "10 teslimat/gün sınırı nedeniyle yoğun talep birden fazla aktif güne bölündü.",
        )

    def write_pdf(self, results, pdf_path):
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

        font_name = "Helvetica"
        bold_font = "Helvetica-Bold"
        arial = Path("C:/Windows/Fonts/arial.ttf")
        arial_bold = Path("C:/Windows/Fonts/arialbd.ttf")
        if arial.exists() and arial_bold.exists():
            pdfmetrics.registerFont(TTFont("Arial", str(arial)))
            pdfmetrics.registerFont(TTFont("Arial-Bold", str(arial_bold)))
            font_name = "Arial"
            bold_font = "Arial-Bold"

        styles = getSampleStyleSheet()
        title = ParagraphStyle("TitleTR", parent=styles["Title"], fontName=bold_font, fontSize=18, leading=22)
        heading = ParagraphStyle("HeadingTR", parent=styles["Heading2"], fontName=bold_font, fontSize=12, leading=15)
        body = ParagraphStyle("BodyTR", parent=styles["BodyText"], fontName=font_name, fontSize=9, leading=12)

        doc = SimpleDocTemplate(str(pdf_path), pagesize=A4, rightMargin=1.4 * cm, leftMargin=1.4 * cm, topMargin=1.2 * cm, bottomMargin=1.2 * cm)
        story = [
            Paragraph("BekoSIRS Teslimat Planlama Simülasyon Raporu", title),
            Paragraph(f"Çalıştırma tarihi: {date.today().isoformat()}", body),
            Spacer(1, 0.4 * cm),
        ]

        summary_data = [["Senaryo", "Durum", "Kısa analiz"]]
        for item in results:
            summary_data.append([Paragraph(item["name"], body), item["status"], Paragraph(item["analysis"], body)])

        summary_table = Table(summary_data, colWidths=[5.0 * cm, 2.2 * cm, 10.0 * cm])
        summary_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4e79")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), bold_font),
            ("FONTNAME", (0, 1), (-1, -1), font_name),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d9e2ec")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7fbff")]),
        ]))
        story.extend([summary_table, Spacer(1, 0.5 * cm)])

        for item in results:
            story.append(Paragraph(f"{item['name']} - {item['status']}", heading))
            metric_rows = [["Metrik", "Değer"]]
            for key, value in item["metrics"].items():
                metric_rows.append([Paragraph(str(key), body), Paragraph(str(value), body)])
            metric_table = Table(metric_rows, colWidths=[5.5 * cm, 11.7 * cm])
            metric_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef5ff")),
                ("FONTNAME", (0, 0), (-1, 0), bold_font),
                ("FONTNAME", (0, 1), (-1, -1), font_name),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d9e2ec")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]))
            story.extend([
                metric_table,
                Spacer(1, 0.15 * cm),
                Paragraph(f"Analiz: {item['analysis']}", body),
                Spacer(1, 0.4 * cm),
            ])

        doc.build(story)
