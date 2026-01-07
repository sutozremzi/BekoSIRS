# BekoSIRS Backend API

![Django](https://img.shields.io/badge/Django-5.2.7-green)
![DRF](https://img.shields.io/badge/DRF-3.14.0-blue)
![Python](https://img.shields.io/badge/Python-3.8+-blue)
![License](https://img.shields.io/badge/License-MIT-yellow)

**Beko Smart Inventory and Recommendation System** - Akıllı Ürün Yönetimi ve Öneri Sistemi

## 📋 İçindekiler

- [Özellikler](#-özellikler)
- [Teknoloji Yığını](#-teknoloji-yığını)
- [Kurulum](#-kurulum)
- [Yapılandırma](#-yapılandırma)
- [Veritabanı](#-veritabanı)
- [API Dokümantasyonu](#-api-dokümantasyonu)
- [Test](#-test)
- [Deployment](#-deployment)
- [Güvenlik](#-güvenlik)
- [Katkıda Bulunma](#-katkıda-bulunma)

## ✨ Özellikler

### 🔐 Kimlik Doğrulama ve Yetkilendirme
- JWT (JSON Web Token) tabanlı authentication
- Role-based access control (Admin, Seller, Customer)
- Biyometrik giriş desteği (FaceID)
- Şifre sıfırlama sistemi

### 📦 Ürün Yönetimi
- CRUD operasyonları
- Hiyerarşik kategori yapısı
- Stok takibi
- Garanti yönetimi
- Excel export özelliği

### 🤖 ML Tabanlı Öneri Sistemi
- Hybrid Recommender (Collaborative + Content-based filtering)
- Kullanıcı davranış analizi
- Gerçek zamanlı öneri skorlaması
- Öneri performans takibi

### 🛠️ Servis Yönetimi
- Servis talep oluşturma ve takibi
- Kuyruk sistemi
- Teknisyen ataması
- Durum bildirimleri

### 🚚 Teslimat Optimizasyonu
- Rota planlama
- Teslimat durumu takibi
- Coğrafi optimizasyon

### 📊 Dashboard ve Raporlama
- Gerçek zamanlı istatistikler
- Satış analizi
- Servis metrikleri
- Performans göstergeleri

## 🛠 Teknoloji Yığını

### Backend Framework
- **Django 5.2.7** - Web framework
- **Django REST Framework 3.14.0** - RESTful API
- **SimpleJWT 5.3.0** - JWT authentication

### Veritabanı
- **SQLite** (Development)
- **Microsoft SQL Server** (Production)

### ML & Data Processing
- **pandas 2.2.2** - Veri analizi
- **numpy 1.26.4** - Sayısal hesaplamalar
- **scikit-learn 1.5.1** - ML algoritmaları

### Diğer Kütüphaneler
- **drf-spectacular 0.29.0** - OpenAPI/Swagger dokümantasyonu
- **django-cors-headers 4.3.1** - CORS yönetimi
- **python-dotenv 1.0.0** - Environment variables
- **Pillow 10.1.0** - Görsel işleme
- **openpyxl 3.1.5** - Excel operasyonları

## 🚀 Kurulum

### Gereksinimler

- Python 3.8+
- pip
- virtualenv (önerilir)
- Microsoft SQL Server (production için)

### Adımlar

1. **Repository'yi klonlayın**
```bash
git clone <repository-url>
cd BekoSIRS_api
```

2. **Virtual environment oluşturun**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# veya
venv\Scripts\activate  # Windows
```

3. **Bağımlılıkları yükleyin**
```bash
pip install -r requirements.txt
```

4. **Environment dosyasını oluşturun**
```bash
cp .env.example .env
# .env dosyasını düzenleyin
```

5. **Secret key oluşturun**
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

6. **Database migration**
```bash
python manage.py migrate
```

7. **Superuser oluşturun**
```bash
python manage.py createsuperuser
```

8. **Development server'ı başlatın**
```bash
python manage.py runserver
```

🎉 API şimdi `http://localhost:8000/api/v1/` adresinde çalışıyor!

## ⚙️ Yapılandırma

### Environment Variables

`.env` dosyasında aşağıdaki değişkenleri yapılandırın:

#### Zorunlu
```env
SECRET_KEY=your-secret-key-here
DB_NAME=your-database-name
DB_USER=your-database-user
DB_PASSWORD=your-database-password
DB_HOST=localhost
DB_PORT=1433
```

#### Opsiyonel
```env
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOW_ALL_ORIGINS=True
CORS_ALLOWED_ORIGINS=http://localhost:5173

# Email (Production)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# Redis (Production)
REDIS_URL=redis://127.0.0.1:6379/1
```

## 🗄️ Veritabanı

### Modeller

- **CustomUser** - Kullanıcı yönetimi
- **Product** - Ürün bilgileri
- **Category** - Hiyerarşik kategoriler
- **ProductOwnership** - Müşteri-ürün sahipliği
- **ServiceRequest** - Servis talepleri
- **Wishlist** - İstek listeleri
- **Notification** - Bildirim sistemi
- **Recommendation** - ML önerileri
- **Delivery** - Teslimat yönetimi

### Migrations

```bash
# Yeni migration oluştur
python manage.py makemigrations

# Migration'ları uygula
python manage.py migrate

# Migration'ları geri al
python manage.py migrate products 0008  # Belirli bir versiyona dön
```

### Management Commands

```bash
# Ürünleri Excel'den import et
python manage.py import_products <excel_file_path>

# Garanti sürelerini kontrol et
python manage.py check_warranty_expiry

# ML modelini eğit
python manage.py train_recommender
```

## 📚 API Dokümantasyonu

### Swagger/OpenAPI

Development modda:
- Swagger UI: `http://localhost:8000/api/v1/docs/`
- ReDoc: `http://localhost:8000/api/v1/redoc/`
- Schema: `http://localhost:8000/api/v1/schema/`

### Ana Endpointler

#### Authentication
```
POST   /api/v1/token/                    # Login (JWT)
POST   /api/v1/token/refresh/            # Token yenile
POST   /api/v1/register/                 # Kayıt ol
GET    /api/v1/profile/                  # Profil bilgileri
PUT    /api/v1/profile/                  # Profil güncelle
```

#### Products
```
GET    /api/v1/products/                 # Tüm ürünler
POST   /api/v1/products/                 # Ürün ekle (admin)
GET    /api/v1/products/{id}/            # Ürün detay
PUT    /api/v1/products/{id}/            # Ürün güncelle (admin)
DELETE /api/v1/products/{id}/            # Ürün sil (admin)
GET    /api/v1/products/my-products/     # Sahip olunan ürünler
GET    /api/v1/products/export/excel/    # Excel export
```

#### Service Requests
```
GET    /api/v1/service-requests/         # Servis talepleri
POST   /api/v1/service-requests/         # Yeni talep
GET    /api/v1/service-requests/{id}/    # Talep detay
POST   /api/v1/service-requests/{id}/assign/  # Teknisyen ata
GET    /api/v1/service-requests/queue-status/  # Kuyruk durumu
```

#### Recommendations
```
GET    /api/v1/recommendations/          # Kişiselleştirilmiş öneriler
GET    /api/v1/recommendations/similar/  # Benzer ürünler
POST   /api/v1/recommendations/generate/ # Öneri oluştur (admin)
POST   /api/v1/recommendations/retrain/  # Modeli yeniden eğit (admin)
```

### Rate Limiting

- Anonymous: 20 request/minute
- Authenticated: 100 request/minute

## 🧪 Test

### Test Çalıştırma

```bash
# Tüm testler
pytest

# Belirli bir dosya
pytest products/tests/test_models.py

# Belirli bir test
pytest products/tests/test_api.py::TestProductAPI::test_create_product

# Coverage ile
pytest --cov

# HTML coverage raporu
pytest --cov --cov-report=html
open htmlcov/index.html
```

### Test Yapısı

```
products/tests/
├── test_models.py              # Model testleri
├── test_serializers.py         # Serializer testleri
├── test_permissions.py         # Permission testleri
├── test_api.py                 # API integration testleri
├── test_password_reset.py      # Şifre sıfırlama testleri
├── test_biometric.py           # Biyometrik auth testleri
└── test_delivery.py            # Teslimat testleri
```

## 🚢 Deployment

### Production Checklist

- [ ] `DEBUG = False` ayarlandı
- [ ] `SECRET_KEY` güvenli ve unique
- [ ] `ALLOWED_HOSTS` doğru domain'lere ayarlandı
- [ ] Database production'a geçti (MSSQL)
- [ ] Static files yapılandırıldı
- [ ] HTTPS aktif
- [ ] Email SMTP yapılandırıldı
- [ ] Redis cache aktif
- [ ] Logging yapılandırıldı
- [ ] Sentry/error tracking kuruldu
- [ ] Backup stratejisi oluşturuldu

### Production Server

**Gunicorn ile:**
```bash
gunicorn bekosirs_backend.wsgi:application --bind 0.0.0.0:8000 --workers 4
```

**Nginx reverse proxy config örneği:**
```nginx
server {
    listen 80;
    server_name api.yourdomain.com;

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /path/to/static/;
    }

    location /media/ {
        alias /path/to/media/;
    }
}
```

### Docker (Opsiyonel)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["gunicorn", "bekosirs_backend.wsgi:application", "--bind", "0.0.0.0:8000"]
```

## 🔒 Güvenlik

### Implemented Security Measures

✅ **Authentication & Authorization**
- JWT with access and refresh tokens
- Token blacklisting
- Role-based permissions

✅ **HTTP Security Headers**
- HSTS (Strict-Transport-Security)
- X-Frame-Options: DENY
- X-Content-Type-Options: nosniff
- X-XSS-Protection

✅ **CORS**
- Whitelist-based CORS policy
- Credentials support

✅ **Password Security**
- Strong password validation
- PBKDF2 hashing
- Min 8 characters
- Common password check

✅ **Rate Limiting**
- DRF throttling enabled
- Per-user and per-IP limits

✅ **Input Validation**
- DRF serializer validation
- SQL injection protection (ORM)

### Security Best Practices

- Tüm production traffic HTTPS üzerinden
- Environment variables için `.env` kullan (Git'e commit etme!)
- Regular security updates: `pip list --outdated`
- Database düzenli backup
- Log monitoring ve alerting
- Dependency vulnerability scanning

## 🤝 Katkıda Bulunma

Katkılarınızı bekliyoruz! Lütfen aşağıdaki adımları takip edin:

1. Fork edin
2. Feature branch oluşturun (`git checkout -b feature/AmazingFeature`)
3. Değişikliklerinizi commit edin (`git commit -m 'Add some AmazingFeature'`)
4. Branch'inizi push edin (`git push origin feature/AmazingFeature`)
5. Pull Request açın

### Development Guidelines

- PEP 8 style guide'a uyun
- Yeni özellikler için test yazın
- Dokümantasyonu güncelleyin
- Commit mesajlarını açıklayıcı yazın

## 📝 Changelog

### v1.0.0 (2026-01-07)

**🔐 Security**
- ALLOWED_HOSTS wildcard kaldırıldı
- Security headers eklendi (HSTS, XSS, etc.)
- debug_token sadece DEBUG modunda

**⚡ Performance**
- N+1 query sorunları çözüldü (prefetch_related)
- Database index'leri eklendi
- Query optimization

**📦 Features**
- API versiyonlama (/api/v1/)
- Logging sistemi yapılandırıldı
- Test coverage ölçümü eklendi

**📚 Documentation**
- README.md oluşturuldu
- requirements.txt tam dokümante edildi
- .env.example güncellendi

## 📄 License

MIT License - detaylar için [LICENSE](LICENSE) dosyasına bakın.

## 👥 Ekip

BekoSIRS Development Team

## 📞 İletişim

- Email: support@bekosirs.com
- Documentation: https://docs.bekosirs.com
- Issue Tracker: https://github.com/yourorg/bekosirs/issues

---

**Made with ❤️ for Beko**
