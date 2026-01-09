import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

# Test kullanıcısı oluştur veya güncelle
username = 'testmobile'
email = 'testmobile@gmail.com'
password = 'test123'

try:
    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            'email': email,
            'role': 'customer',
            'first_name': 'Test',
            'last_name': 'Mobile'
        }
    )
    user.set_password(password)
    user.save()
    
    if created:
        print(f'✅ User {username} created successfully!')
    else:
        print(f'✅ User {username} updated successfully!')
    
    print(f'   Email: {email}')
    print(f'   Password: {password}')
    print(f'   Role: {user.role}')
    
except Exception as e:
    print(f'❌ Error: {e}')
