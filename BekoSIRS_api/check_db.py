import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bekosirs_backend.settings')
django.setup()

from products.models import Product, CustomUser

print(f"Products: {Product.objects.count()}")
print(f"Users: {CustomUser.objects.count()}")
print(f"Admins: {CustomUser.objects.filter(role='admin').count()}")

admin_exists = CustomUser.objects.filter(username='admin').exists()
print(f"Admin User 'admin' exists: {admin_exists}")
