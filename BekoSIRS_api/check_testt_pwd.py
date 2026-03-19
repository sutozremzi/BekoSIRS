import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bekosirs_backend.settings')
django.setup()
from products.models import CustomUser

user = CustomUser.objects.filter(username='testt').first()
if user:
    match = user.check_password('test')
    print(f"Password 'test' for 'testt' matches: {match}")
else:
    print("User 'testt' not found")
