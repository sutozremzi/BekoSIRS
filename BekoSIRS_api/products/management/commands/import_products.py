import pandas as pd
from django.core.management.base import BaseCommand
from products.models import Product, Category
#bu remzininki
class Command(BaseCommand):
    help = "Beko Excel dosyasındaki ürünleri veritabanına aktarır"

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str, help='Excel dosyasının yolu')

    def handle(self, *args, **kwargs):
        file_path = kwargs['file_path']

        # 🧩 Başlık satırı 4. satırda (ilk 3 satır açıklama)
        df = pd.read_excel(file_path, header=3)

        # 🧹 Gereksiz boş sütunları at
        df = df.dropna(how="all")

        for index, row in df.iterrows():
            try:
                product_code = str(row.get("EK GARANTİ KODU", "")).strip()
                description = str(row.get(df.columns[1], "")).strip()
                list_price = row.get("Liste Fiyatı", 0)
                campaign = str(row.get("KAMPANYASI", "")).strip()

                if pd.isna(product_code) or product_code == "":
                    continue  # boş satırları atla

                # Kategoriye göre sınıflandırma (örnek: "Buzdolabı")
                category, _ = Category.objects.get_or_create(name="Buzdolabı")

                # Ürün oluştur
                product, created = Product.objects.get_or_create(
                    name=product_code,
                    brand="BEKO",
                    category=category,
                    defaults={
                        "description": description,
                        "price": list_price if pd.notna(list_price) else 0.0,
                        "warranty_duration_months": 24,
                    },
                )

                if created:
                    self.stdout.write(self.style.SUCCESS(f"{product.name} eklendi"))
                else:
                    self.stdout.write(self.style.WARNING(f"{product.name} zaten var"))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Hata satır {index}: {e}"))
