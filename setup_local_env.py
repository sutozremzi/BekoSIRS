import os
import socket
import re

def get_local_ip():
    """Cihazın yerel ağdaki (LAN) IP adresini bulur."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Bağlantı kurulmasına gerek yok, sadece route belirlemek için 10.255.255.255 adresine gitmeyi deniyoruz
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
    except Exception:
        # Hata durumunda fallback (geri çekilme) adresi
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

def setup_frontend_env(ip_address, base_dir):
    """Frontend projesi için .env dosyasını oluşturur/günceller."""
    frontend_dir = os.path.join(base_dir, 'BekoSIRS_Frontend')
    env_path = os.path.join(frontend_dir, '.env')
    
    # Frontend klasörü yoksa uyar
    if not os.path.exists(frontend_dir):
        print(f"❌ Uyarı: {frontend_dir} klasörü bulunamadı.")
        return

    # Eğer .env varsa oku ve EXPO_PUBLIC_API_URL'i değiştir, yoksa yarat
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if 'EXPO_PUBLIC_API_URL' in content:
            content = re.sub(
                r'EXPO_PUBLIC_API_URL=.*', 
                f'EXPO_PUBLIC_API_URL=http://{ip_address}:8000/', 
                content
            )
        else:
            content += f"\nEXPO_PUBLIC_API_URL=http://{ip_address}:8000/\n"
    else:
        content = f"EXPO_PUBLIC_API_URL=http://{ip_address}:8000/\n"

    with open(env_path, 'w', encoding='utf-8') as f:
        f.write(content)
        
    print(f"✅ Frontend .env ayarlandı: EXPO_PUBLIC_API_URL=http://{ip_address}:8000/")

def setup_backend_env(base_dir):
    """Backend projesi için .env dosyasındaki ALLOWED_HOSTS ayarını yapar."""
    backend_dir = os.path.join(base_dir, 'BekoSIRS_api')
    env_path = os.path.join(backend_dir, '.env')
    example_env_path = os.path.join(backend_dir, '.env.example')
    
    if not os.path.exists(backend_dir):
        print(f"❌ Uyarı: {backend_dir} klasörü bulunamadı.")
        return

    content = ""
    # Eğer .env.example varsa kopyala, yoksa ve .env varsa direk değişiklik yap
    if not os.path.exists(env_path) and os.path.exists(example_env_path):
        with open(example_env_path, 'r', encoding='utf-8') as f:
            content = f.read()
    elif os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            content = f.read()

    # ALLOWED_HOSTS kontrolü (herkes ağdan erişebilsin diye * yapıyoruz)
    if 'ALLOWED_HOSTS' in content:
        content = re.sub(
            r'ALLOWED_HOSTS=.*', 
            'ALLOWED_HOSTS=*', 
            content
        )
    else:
        content += "\nALLOWED_HOSTS=*\n"

    with open(env_path, 'w', encoding='utf-8') as f:
        f.write(content)
        
    print(f"✅ Backend .env ayarlandı: ALLOWED_HOSTS=*")

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 BekoSIRS Yerel Geliştirme (Local Environment) Kurulumu")
    print("=" * 60)
    
    # Script'in çalıştığı dizini al (BekoSIRS ana klasörü olması beklenir)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    local_ip = get_local_ip()
    print(f"\n📡 Tespit Edilen Yerel IP Adresiniz: {local_ip}")
    print("-" * 60)
    
    setup_frontend_env(local_ip, base_dir)
    setup_backend_env(base_dir)
    
    print("-" * 60)
    print("🎉 Kurulum başarıyla tamamlandı!\n")
    print("👉 Projeyi başlatmak için aşağıdaki komutları kullanabilirsiniz:")
    print("1) Backend (Yeni bir CMD penceresinde):")
    print("   cd BekoSIRS_api")
    print("   .\\venv\\Scripts\\activate")
    print("   python manage.py runserver 0.0.0.0:8000")
    print("\n2) Frontend / Mobil Uygulama (Yeni bir CMD penceresinde):")
    print("   cd BekoSIRS_Frontend")
    print("   set EXPO_OFFLINE=1")
    print("   npx expo start --lan -c")
    print("=" * 60)
