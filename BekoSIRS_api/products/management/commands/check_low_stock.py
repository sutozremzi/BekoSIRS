"""
Low stock alert management command.

Checks for products with stock below minimum threshold and notifies admins.

Usage:
    python manage.py check_low_stock
    python manage.py check_low_stock --threshold 10
    python manage.py check_low_stock --dry-run
    
Cron job (daily at 8 AM):
    0 8 * * * cd /path/to/project && python manage.py check_low_stock
"""

from django.core.management.base import BaseCommand
from django.conf import settings
from products.models import Product, CustomUser, Notification


class Command(BaseCommand):
    help = 'Düşük stoklu ürünleri kontrol et ve admin/seller kullanıcılarını bilgilendir'

    def add_arguments(self, parser):
        parser.add_argument(
            '--threshold',
            type=int,
            default=getattr(settings, 'MIN_STOCK_LEVEL', 5),
            help='Minimum stok eşiği (default: settings.MIN_STOCK_LEVEL veya 5)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Bildirimleri oluşturmadan sadece kontrol et'
        )
        parser.add_argument(
            '--include-zero',
            action='store_true',
            help='Stoksuz (0) ürünleri de dahil et'
        )

    def handle(self, *args, **options):
        threshold = options['threshold']
        dry_run = options['dry_run']
        include_zero = options['include_zero']

        self.stdout.write(f'Stok eşiği: {threshold}')
        self.stdout.write(f'Düşük stoklu ürünler kontrol ediliyor...')

        # Find low stock products
        if include_zero:
            low_stock_products = Product.objects.filter(stock__lte=threshold).order_by('stock')
        else:
            low_stock_products = Product.objects.filter(
                stock__gt=0,
                stock__lte=threshold
            ).order_by('stock')

        # Find out of stock products
        out_of_stock_products = Product.objects.filter(stock=0)

        self.stdout.write(f'Düşük stoklu ürün sayısı: {low_stock_products.count()}')
        self.stdout.write(f'Stoksuz ürün sayısı: {out_of_stock_products.count()}')

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN: Bildirimler oluşturulmayacak'))
            self.stdout.write('')
            
            if low_stock_products.exists():
                self.stdout.write(self.style.WARNING('⚠️ Düşük Stoklu Ürünler:'))
                for p in low_stock_products:
                    self.stdout.write(f'  - [{p.stock} adet] {p.name} ({p.brand})')
            
            if out_of_stock_products.exists():
                self.stdout.write('')
                self.stdout.write(self.style.ERROR('❌ Stoksuz Ürünler:'))
                for p in out_of_stock_products:
                    self.stdout.write(f'  - {p.name} ({p.brand})')
            return

        # Get admin and seller users for notifications
        staff_users = CustomUser.objects.filter(
            role__in=['admin', 'seller'],
            is_active=True
        )

        if not staff_users.exists():
            self.stdout.write(self.style.WARNING('Bildirilecek admin/seller kullanıcı yok.'))
            return

        notifications = []
        
        # Create low stock notification
        if low_stock_products.exists():
            product_list = ', '.join([f"{p.name} ({p.stock})" for p in low_stock_products[:5]])
            if low_stock_products.count() > 5:
                product_list += f' ve {low_stock_products.count() - 5} ürün daha'
            
            for user in staff_users:
                notifications.append(
                    Notification(
                        user=user,
                        notification_type='general',
                        title='⚠️ Düşük Stok Uyarısı',
                        message=f'{low_stock_products.count()} ürünün stoğu kritik seviyede ({threshold} ve altı): {product_list}'
                    )
                )

        # Create out of stock notification
        if out_of_stock_products.exists():
            product_list = ', '.join([p.name for p in out_of_stock_products[:5]])
            if out_of_stock_products.count() > 5:
                product_list += f' ve {out_of_stock_products.count() - 5} ürün daha'
            
            for user in staff_users:
                notifications.append(
                    Notification(
                        user=user,
                        notification_type='general',
                        title='❌ Stoksuz Ürün Uyarısı',
                        message=f'{out_of_stock_products.count()} ürün tamamen stoksuz: {product_list}'
                    )
                )

        if notifications:
            Notification.objects.bulk_create(notifications)
            self.stdout.write(
                self.style.SUCCESS(
                    f'{len(notifications)} bildirim {staff_users.count()} kullanıcıya gönderildi.'
                )
            )
        else:
            self.stdout.write(self.style.SUCCESS('Tüm ürünlerin stoğu yeterli.'))

        # Summary
        self.stdout.write('')
        self.stdout.write('=' * 50)
        self.stdout.write('STOK DURUMU ÖZETİ')
        self.stdout.write('=' * 50)
        self.stdout.write(f'  Toplam ürün sayısı:     {Product.objects.count()}')
        self.stdout.write(f'  Yeterli stoklu:         {Product.objects.filter(stock__gt=threshold).count()}')
        self.stdout.write(self.style.WARNING(f'  Düşük stoklu (1-{threshold}):   {low_stock_products.count()}'))
        self.stdout.write(self.style.ERROR(f'  Stoksuz (0):            {out_of_stock_products.count()}'))
        self.stdout.write('=' * 50)
