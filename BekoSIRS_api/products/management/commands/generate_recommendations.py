"""
Generate product recommendations for all customers.

Usage:
    python manage.py generate_recommendations
    python manage.py generate_recommendations --user testuser
    python manage.py generate_recommendations --dry-run
    
Cron job (daily at 3 AM):
    0 3 * * * cd /path/to/project && python manage.py generate_recommendations
"""

from django.core.management.base import BaseCommand
from products.models import CustomUser
from products.recommendation_service import RecommendationService, generate_all_user_recommendations


class Command(BaseCommand):
    help = 'Tüm müşteriler için kişiselleştirilmiş ürün önerileri oluştur'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user',
            type=str,
            help='Sadece belirli bir kullanıcı için öneriler oluştur (username)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Veritabanına kaydetmeden sadece önerileri göster'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=10,
            help='Kullanıcı başına maksimum öneri sayısı (default: 10)'
        )

    def handle(self, *args, **options):
        username = options['user']
        dry_run = options['dry_run']
        limit = options['limit']

        if username:
            # Single user mode
            try:
                user = CustomUser.objects.get(username=username)
                self._generate_for_user(user, limit, dry_run)
            except CustomUser.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Kullanıcı bulunamadı: {username}'))
                return
        else:
            # All users mode
            if dry_run:
                self.stdout.write(self.style.WARNING('DRY RUN: Öneriler veritabanına kaydedilmeyecek'))
            
            customers = CustomUser.objects.filter(
                role='customer',
                is_active=True
            )
            
            self.stdout.write(f'Toplam {customers.count()} müşteri için öneriler oluşturuluyor...')
            
            total_generated = 0
            for customer in customers:
                count = self._generate_for_user(customer, limit, dry_run)
                total_generated += count
            
            self.stdout.write('')
            self.stdout.write('=' * 50)
            self.stdout.write(self.style.SUCCESS(
                f'Toplam {total_generated} öneri oluşturuldu.'
            ))

    def _generate_for_user(self, user, limit, dry_run):
        """Generate recommendations for a single user."""
        service = RecommendationService(user)
        recommendations = service.generate_recommendations(limit=limit)
        
        self.stdout.write('')
        self.stdout.write(f'📊 {user.username} için öneriler:')
        self.stdout.write('-' * 40)
        
        for idx, rec in enumerate(recommendations, 1):
            product = rec['product']
            score = rec['score']
            reasons = ', '.join(rec['reasons'])
            
            self.stdout.write(
                f'  {idx}. {product.name} ({product.brand})'
            )
            self.stdout.write(
                f'     Skor: {score:.2f} | Sebep: {reasons}'
            )
        
        if not dry_run:
            saved = service.save_recommendations(recommendations)
            self.stdout.write(
                self.style.SUCCESS(f'  ✅ {saved} öneri kaydedildi.')
            )
            return saved
        else:
            self.stdout.write(
                self.style.WARNING(f'  ⚠️ DRY RUN - kaydedilmedi.')
            )
            return len(recommendations)
