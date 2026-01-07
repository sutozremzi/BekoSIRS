# BekoSIRS Backend - Production Deployment Guide

Bu dizin, BekoSIRS Backend API'sinin production ortamına deployment edilmesi için gerekli tüm konfigürasyon dosyalarını içerir.

## 📁 Dosyalar

```
deployment/
├── nginx.conf                # Nginx reverse proxy config
├── bekosirs.service          # Systemd service file
├── deploy.sh                 # Automated deployment script
├── .env.production.example   # Production environment variables
└── README.md                 # Bu dosya
```

## 🚀 Deployment Adımları

### 1. Server Hazırlığı

```bash
# Server paketlerini güncelle
sudo apt update && sudo apt upgrade -y

# Gerekli paketleri yükle
sudo apt install -y python3 python3-pip python3-venv nginx redis-server postgresql git

# Uygulama kullanıcısı oluştur
sudo useradd -m -s /bin/bash bekosirs
sudo usermod -aG www-data bekosirs
```

### 2. Uygulama Kurulumu

```bash
# Uygulama dizinini oluştur
sudo mkdir -p /var/www/bekosirs
sudo chown bekosirs:www-data /var/www/bekosirs

# bekosirs kullanıcısına geç
sudo su - bekosirs

# Kodu clone'la
cd /var/www/bekosirs
git clone <repository-url> BekoSIRS_api
cd BekoSIRS_api

# Virtual environment oluştur
python3 -m venv /var/www/bekosirs/venv
source /var/www/bekosirs/venv/bin/activate

# Bağımlılıkları yükle
pip install -r requirements.txt
pip install gunicorn

# Gunicorn'u requirements'a ekle
echo "gunicorn==21.2.0" >> requirements.txt
```

### 3. Environment Variables Yapılandırması

```bash
# Production .env dosyasını oluştur
cp deployment/.env.production.example /var/www/bekosirs/.env

# .env dosyasını düzenle (VIM/NANO ile)
vim /var/www/bekosirs/.env

# ÖNEMLI: SECRET_KEY, DB credentials, EMAIL settings değiştir!

# Dosya izinlerini sıkılaştır
chmod 600 /var/www/bekosirs/.env
```

### 4. Database Kurulumu

```bash
# PostgreSQL kullanıcısı oluştur (MSSQL için atlayın)
sudo -u postgres createuser bekosirs_user
sudo -u postgres createdb bekosirs_production --owner bekosirs_user

# Migration'ları çalıştır
source /var/www/bekosirs/venv/bin/activate
cd /var/www/bekosirs/BekoSIRS_api
python manage.py migrate

# Superuser oluştur
python manage.py createsuperuser

# Static files topla
python manage.py collectstatic --noinput
```

### 5. Nginx Konfigürasyonu

```bash
# Nginx config'i kopyala
sudo cp deployment/nginx.conf /etc/nginx/sites-available/bekosirs

# Symlink oluştur
sudo ln -s /etc/nginx/sites-available/bekosirs /etc/nginx/sites-enabled/

# Default site'ı devre dışı bırak (opsiyonel)
sudo rm /etc/nginx/sites-enabled/default

# Nginx config'i test et
sudo nginx -t

# Nginx'i restart et
sudo systemctl restart nginx
```

### 6. SSL Sertifikası (Let's Encrypt)

```bash
# Certbot yükle
sudo apt install -y certbot python3-certbot-nginx

# SSL sertifikası al
sudo certbot --nginx -d api.bekosirs.com

# Auto-renewal test et
sudo certbot renew --dry-run
```

### 7. Systemd Service Kurulumu

```bash
# Service dosyasını kopyala
sudo cp deployment/bekosirs.service /etc/systemd/system/

# Log dizinleri oluştur
sudo mkdir -p /var/log/bekosirs /var/run/bekosirs
sudo chown bekosirs:www-data /var/log/bekosirs /var/run/bekosirs

# Systemd'yi reload et
sudo systemctl daemon-reload

# Service'i enable ve start et
sudo systemctl enable bekosirs
sudo systemctl start bekosirs

# Status kontrol et
sudo systemctl status bekosirs
```

### 8. Firewall Yapılandırması

```bash
# UFW enable et
sudo ufw enable

# HTTP ve HTTPS'e izin ver
sudo ufw allow 'Nginx Full'

# SSH'e izin ver (kilitlenmemek için!)
sudo ufw allow OpenSSH

# Status kontrol et
sudo ufw status
```

## 🔄 Deployment (Güncelleme)

Kod güncellemesi için automated deployment script kullanın:

```bash
# Production deployment
sudo su - bekosirs
cd /var/www/bekosirs/BekoSIRS_api
./deployment/deploy.sh production
```

Script otomatik olarak:
- ✅ Kodu pull eder
- ✅ Dependencies günceller
- ✅ Static files toplar
- ✅ Migration çalıştırır
- ✅ Deployment check yapar
- ✅ Cache temizler
- ✅ Gunicorn'u restart eder
- ✅ Health check yapar

## 📊 Monitoring

### Logs

```bash
# Gunicorn logs
tail -f /var/log/bekosirs/gunicorn-error.log
tail -f /var/log/bekosirs/gunicorn-access.log

# Systemd logs
sudo journalctl -u bekosirs -f

# Nginx logs
tail -f /var/log/nginx/bekosirs-access.log
tail -f /var/log/nginx/bekosirs-error.log

# Django application logs
tail -f /var/www/bekosirs/BekoSIRS_api/logs/bekosirs.log
```

### Service Management

```bash
# Start/Stop/Restart
sudo systemctl start bekosirs
sudo systemctl stop bekosirs
sudo systemctl restart bekosirs
sudo systemctl reload bekosirs  # Graceful reload

# Status
sudo systemctl status bekosirs
sudo systemctl is-active bekosirs

# Enable/Disable auto-start
sudo systemctl enable bekosirs
sudo systemctl disable bekosirs
```

## 🔧 Troubleshooting

### Service başlamıyor

```bash
# Detaylı logs
sudo journalctl -u bekosirs -n 50 --no-pager

# Config test
source /var/www/bekosirs/venv/bin/activate
cd /var/www/bekosirs/BekoSIRS_api
python manage.py check --deploy

# Manuel başlatma (debug için)
/var/www/bekosirs/venv/bin/gunicorn \
    --config gunicorn.conf.py \
    bekosirs_backend.wsgi:application
```

### 502 Bad Gateway

```bash
# Gunicorn çalışıyor mu?
sudo systemctl status bekosirs

# Nginx config doğru mu?
sudo nginx -t

# Upstream connection test et
curl http://127.0.0.1:8000/api/v1/
```

### Database connection hatası

```bash
# Database erişilebilir mi?
python manage.py dbshell

# .env dosyası doğru mu?
cat /var/www/bekosirs/.env | grep DB_

# Credentials test et
psql -U bekosirs_user -d bekosirs_production -h localhost
```

## 📈 Performance Tuning

### Gunicorn Workers

```python
# gunicorn.conf.py
workers = (CPU_COUNT * 2) + 1  # Default

# Daha fazla RAM varsa:
workers = (CPU_COUNT * 4) + 1
```

### Nginx Caching

```nginx
# nginx.conf içine ekleyin
proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=api_cache:10m;

location /api/v1/products/ {
    proxy_cache api_cache;
    proxy_cache_valid 200 5m;
    # ...
}
```

### Redis Performance

```bash
# Redis config
sudo vim /etc/redis/redis.conf

# Ayarlar:
maxmemory 256mb
maxmemory-policy allkeys-lru
```

## 🔒 Security Checklist

- [ ] DEBUG = False
- [ ] SECRET_KEY unique ve güvenli
- [ ] ALLOWED_HOSTS doğru domain'ler
- [ ] SSL/HTTPS aktif
- [ ] Firewall yapılandırıldı
- [ ] Database güçlü şifre
- [ ] .env dosyası 600 permission
- [ ] Regular backups yapılandırıldı
- [ ] Fail2ban kuruldu
- [ ] Server güncellemeleri otomatik

## 🔄 Backup Strategy

```bash
# Database backup script
#!/bin/bash
BACKUP_DIR="/var/backups/bekosirs"
DATE=$(date +%Y%m%d_%H%M%S)

# Database backup
pg_dump -U bekosirs_user bekosirs_production | gzip > \
    $BACKUP_DIR/db_$DATE.sql.gz

# Media files backup
tar -czf $BACKUP_DIR/media_$DATE.tar.gz \
    /var/www/bekosirs/BekoSIRS_api/media/

# Retention: 30 günden eski backupları sil
find $BACKUP_DIR -name "*.gz" -mtime +30 -delete
```

Crontab'a ekle:
```bash
# Her gün 02:00'de backup
0 2 * * * /usr/local/bin/bekosirs-backup.sh
```

## 📞 Support

Deployment sorunları için:
- Email: devops@bekosirs.com
- Slack: #bekosirs-deployment
- Docs: https://docs.bekosirs.com/deployment
