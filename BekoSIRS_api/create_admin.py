import os
import django
os.environ['DJANGO_SETTINGS_MODULE'] = 'bekosirs_backend.settings'
django.setup()

from products.models import CustomUser

# Create or get admin user
admin, created = CustomUser.objects.get_or_create(
    username='admin',
    defaults={
        'role': 'admin',
        'email': 'admin@beko.com',
        'is_staff': True,
        'is_superuser': True,
        'first_name': 'Admin',
        'last_name': 'User'
    }
)

if created:
    admin.set_password('admin123')
    admin.save()
    print('Admin user created!')
else:
    # Reset password anyway
    admin.set_password('admin123')
    admin.save()
    print('Admin user exists, password reset!')

print(f'Username: admin')
print(f'Password: admin123')
