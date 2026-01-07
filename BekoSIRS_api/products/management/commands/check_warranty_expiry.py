"""
Garanti süresi dolmak üzere olan ürünler için otomatik bildirim gönderen management command.

Kullanım:
    python manage.py check_warranty_expiry
    
Cron job olarak günlük çalıştırılabilir:
    0 9 * * * cd /path/to/project && python manage.py check_warranty_expiry
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from products.models import ProductOwnership, Notification


class Command(BaseCommand):
    help = 'Garanti süresi 30 gün içinde dolacak ürünler için bildirim gönderir'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Kaç gün önceden uyarı gönderilsin (default: 30)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Bildirimleri oluşturmadan sadece kontrol et'
        )

    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']
        
        today = timezone.now().date()
        warning_date = today + timedelta(days=days)
        
        self.stdout.write(f'Garanti süresi {warning_date} tarihine kadar dolacak ürünler kontrol ediliyor...')
        
        # Garanti süresi dolmak üzere olan ürün sahipliklerini bul
        expiring_ownerships = []
        
        for ownership in ProductOwnership.objects.select_related('customer', 'product'):
            warranty_end = ownership.warranty_end_date
            if warranty_end and today <= warranty_end <= warning_date:
                # Bu ownership için daha önce bildirim gönderilmiş mi?
                already_notified = Notification.objects.filter(
                    user=ownership.customer,
                    notification_type='warranty_expiry',
                    related_product=ownership.product,
                    created_at__gte=today - timedelta(days=7)  # Son 7 gün içinde
                ).exists()
                
                if not already_notified:
                    expiring_ownerships.append(ownership)
        
        self.stdout.write(f'{len(expiring_ownerships)} adet ürün için bildirim gönderilecek.')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN: Bildirimler oluşturulmadı.'))
            for o in expiring_ownerships:
                days_left = (o.warranty_end_date - today).days
                self.stdout.write(f'  - {o.customer.email}: {o.product.name} ({days_left} gün kaldı)')
            return
        
        # Bildirimleri oluştur
        notifications = []
        for ownership in expiring_ownerships:
            days_left = (ownership.warranty_end_date - today).days
            
            # Kullanıcının garanti bildirimi tercihi açık mı?
            if ownership.customer.notify_warranty_expiry:
                notifications.append(
                    Notification(
                        user=ownership.customer,
                        notification_type='warranty_expiry',
                        title='Garanti Süresi Dolmak Üzere!',
                        message=f'{ownership.product.name} ürününüzün garanti süresi {days_left} gün içinde ({ownership.warranty_end_date.strftime("%d.%m.%Y")}) dolacak.',
                        related_product=ownership.product
                    )
                )
        
        if notifications:
            Notification.objects.bulk_create(notifications)
            self.stdout.write(self.style.SUCCESS(f'{len(notifications)} bildirim başarıyla oluşturuldu.'))
        else:
            self.stdout.write('Gönderilecek bildirim yok.')
