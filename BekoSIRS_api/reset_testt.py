import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bekosirs_backend.settings')
django.setup()
from products.models import CustomUser

user = CustomUser.objects.filter(username='testt').first()
if user:
    user.set_password('test')
    user.save()
    print(f"Password for '{user.username}' has been reset.")
    print(f"Check match for 'test': {user.check_password('test')}")
else:
    print("User 'testt' not found")
