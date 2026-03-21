import json
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bekosirs_backend.settings')
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()

with open(r'C:\Users\Remzi\Desktop\db_export.json', encoding='utf-8') as f:
    data = json.load(f)

users_data = [d for d in data if d['model'] == 'products.customuser']

for user_dict in users_data:
    fields = user_dict['fields']
    username = fields['username']
    
    user, created = User.objects.update_or_create(
        username=username,
        defaults={
            'email': fields.get('email', f"{username}@test.com"),
            'is_staff': fields.get('is_staff', False),
            'is_superuser': fields.get('is_superuser', False),
            'role': fields.get('role', 'customer'),
            'first_name': fields.get('first_name', ''),
            'last_name': fields.get('last_name', ''),
        }
    )
    user.set_password('Test1234!')
    user.save()
    print(f"{'Created' if created else 'Updated'} user: {username} (Role: {user.role}) with password 'Test1234!'")
