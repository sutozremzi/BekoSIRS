import json
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bekosirs_backend.settings')
django.setup()

from products.models import Product, CustomUser
User = CustomUser

with open(r'C:\Users\Remzi\Desktop\db_export.json', encoding='utf-8') as f:
    data = json.load(f)

products_data = [d for d in data if d['model'] == 'products.product']

try:
    admin_user = User.objects.get(username='admin')
except User.DoesNotExist:
    admin_user = None

for p_dict in products_data[:20]: # Load first 20 products
    fields = p_dict['fields']
    try:
        Product.objects.update_or_create(
            id=p_dict['pk'],
            defaults={
                'name': fields.get('name', 'Bilinmeyen Ürün'),
                'stock_code': fields.get('stock_code', ''),
                'barcode': fields.get('barcode', ''),
                'price': fields.get('price', 0),
                'stock_quantity': fields.get('stock_quantity', 0),
                'category_id': fields.get('category'), 
                'seller': admin_user
            }
        )
    except Exception as e:
        print(f"Error loading product {p_dict['pk']}: {e}")

print("Products loaded (max 20).")
