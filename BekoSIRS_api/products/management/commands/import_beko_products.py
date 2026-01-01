import os
import pandas as pd
from django.core.management.base import BaseCommand
from products.models import Product, Category

class Command(BaseCommand):
    help = 'Beko ürün listesini XLS (Eski Excel) dosyasından içe aktarır'

    def handle(self, *args, **options):
        # Dosya adının uzantısı .xls olmalı
        file_path = 'bekoproducts.xls'

        if not os.path.exists(file_path):
            # Eğer .xls bulamazsa .xlsx var mı diye bakar (Kullanıcı adı değiştirmiş olabilir)
            if os.path.exists('bekoproducts.xlsx'):
                file_path = 'bekoproducts.xlsx'
            else:
                self.stdout.write(self.style.ERROR(f'Dosya bulunamadı: {file_path}'))
                return

        self.stdout.write(self.style.WARNING(f'{file_path} dosyası okunuyor...'))

        current_category = None
        created_count = 0
        updated_count = 0

        try:
            # Pandas ile Excel okuma (xlrd kütüphanesi yüklü olmalı)
            # header=None: Başlıkları veri olarak al
            df = pd.read_excel(file_path, header=None)
            
            # NaN (Boş) değerleri boş string ile doldur
            df = df.fillna("")

            # Satır satır dön
            for index, row in df.iterrows():
                
                # Sütun verilerini string olarak al ve temizle
                col0 = str(row[0]).strip() # Kod / Kategori belirteci
                col1 = str(row[1]).strip() # Ürün Adı
                col2 = str(row[2]).strip() # Açıklama
                
                # Fiyat hücresi (G sütunu -> index 6)
                raw_price = row[6] if len(row) > 6 else 0

                # --- 1. KATEGORİ TESPİTİ ---
                if "EK GARANTİ KODU" in col0:
                    # "BUZDOLAPLARI (xyz)" -> "BUZDOLAPLARI"
                    category_name = col1.split('(')[0].strip()
                    
                    if category_name and category_name != "Ürün Adı":
                        current_category, _ = Category.objects.get_or_create(name=category_name)
                        self.stdout.write(self.style.SUCCESS(f'📂 Kategori Seçildi: {category_name}'))
                    continue

                if not current_category:
                    continue

                # --- 2. ÜRÜN TESPİTİ ---
                # Başlık satırlarını atla
                if col1 in ["Ürün Adı", "Liste Fiyatı", ""] or str(raw_price) == "Fiyat":
                    continue
                
                if not col1:
                    continue

                # --- FİYAT TEMİZLEME ---
                price = 0.0
                try:
                    # Excel bazen sayıyı direkt float verir, bazen string ("15.000 TL")
                    if isinstance(raw_price, (int, float)):
                        price = float(raw_price)
                    else:
                        price_str = str(raw_price).replace('TL', '').strip()
                        if not price_str:
                            continue
                            
                        # 14.000,00 formatını düzelt
                        if ',' in price_str:
                            price_str = price_str.replace('.', '').replace(',', '.')
                        else:
                            price_str = price_str.replace('.', '')
                            
                        price = float(price_str)
                except ValueError:
                    continue

                if price <= 0:
                    continue

                # --- VERİTABANI KAYDI ---
                product, created = Product.objects.update_or_create(
                    name=col1,
                    defaults={
                        'description': col2,
                        'price': price,
                        'category': current_category,
                        'brand': 'Beko',
                        'stock': 15,
                        'warranty_duration_months': 24
                    }
                )

                if created:
                    created_count += 1
                else:
                    updated_count += 1

        except ImportError:
             self.stdout.write(self.style.ERROR("Hata: 'xlrd' kütüphanesi eksik. Lütfen 'pip install xlrd' komutunu çalıştırın."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Hata oluştu: {str(e)}'))

        self.stdout.write(self.style.SUCCESS(f'\nİşlem Tamamlandı!'))
        self.stdout.write(f'Yeni Eklenen: {created_count}')
        self.stdout.write(f'Güncellenen: {updated_count}')