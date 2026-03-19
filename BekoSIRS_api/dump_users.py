import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bekosirs_backend.settings')
django.setup()
from products.models import CustomUser

print('--- All Custom Users ---')
users = CustomUser.objects.all()
for u in users:
    print(f'Username: "{u.username}", Role: {u.role}, Active: {u.is_active}')

print('\n--- Search for "testt" ---')
testt = CustomUser.objects.filter(username__icontains='test').first()
if testt:
    print(f'Found: "{testt.username}", Role: {testt.role}, Active: {testt.is_active}, Password len: {len(testt.password)}')
else:
    print('No user found containing "test"')
