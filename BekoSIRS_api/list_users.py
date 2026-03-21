import os
import django

# Django ayarlarını yükle
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bekosirs_backend.settings')
django.setup()

from products.models import CustomUser

def list_all_users():
    users = CustomUser.objects.all().order_by('id')
    
    print(f"{'ID':<5} | {'Kullanıcı Adı':<20} | {'Rol (Yetki)':<15} | {'Email':<30} | {'Aktif':<6}")
    print("-" * 85)
    
    for u in users:
        print(f"{u.id:<5} | {u.username:<20} | {u.role:<15} | {u.email:<30} | {str(u.is_active):<6}")
        
    print("-" * 85)
    print("Not: Güvenlik (şifreleme) nedeniyle Django veritabanındaki şifreler '*pbkdf2_sha256*' formatında kriptolu tutulur, bu yüzden şifreleri düz metin olarak veremiyoruz. Yeni şifre belirlemek için admin panelini veya şifre sıfırlama scriptlerini kullanabilirsin.")

if __name__ == '__main__':
    list_all_users()
