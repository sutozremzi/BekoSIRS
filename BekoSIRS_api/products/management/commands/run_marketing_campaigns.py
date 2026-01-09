"""
Run marketing automation campaigns.

Usage:
    # Run all campaigns
    python manage.py run_marketing_campaigns
    
    # Run specific campaign
    python manage.py run_marketing_campaigns --campaign birthday
    python manage.py run_marketing_campaigns --campaign churn
    python manage.py run_marketing_campaigns --campaign review
    python manage.py run_marketing_campaigns --campaign welcome
    
    # Dry run (don't send actual emails)
    python manage.py run_marketing_campaigns --dry-run
    
Cron job examples:
    # Run all campaigns daily at 9 AM
    0 9 * * * cd /path/to/project && python manage.py run_marketing_campaigns
    
    # Run birthday campaign weekly
    0 10 * * 1 cd /path/to/project && python manage.py run_marketing_campaigns --campaign birthday
"""

from django.core.management.base import BaseCommand
from products.marketing_automation import MarketingAutomationService


class Command(BaseCommand):
    help = 'Pazarlama otomasyonu kampanyalarını çalıştır'

    def add_arguments(self, parser):
        parser.add_argument(
            '--campaign',
            type=str,
            choices=['birthday', 'churn', 'review', 'welcome', 'all'],
            default='all',
            help='Çalıştırılacak kampanya tipi (birthday, churn, review, welcome, all)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Gerçek email göndermeden sadece simüle et'
        )

    def handle(self, *args, **options):
        campaign = options['campaign']
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('⚠️ DRY RUN: Email gönderimleri simüle edilecek'))
        
        self.stdout.write('')
        self.stdout.write('=' * 50)
        self.stdout.write(self.style.HTTP_INFO('🚀 Pazarlama Otomasyonu Başlatılıyor'))
        self.stdout.write('=' * 50)
        self.stdout.write('')

        service = MarketingAutomationService(dry_run=dry_run)

        campaign_funcs = {
            'birthday': ('🎂 Doğum Günü Kampanyası', service.run_birthday_campaign),
            'churn': ('💔 Kayıp Önleme Kampanyası', service.run_churn_prevention),
            'review': ('⭐ Yorum İsteği Kampanyası', service.run_review_request),
            'welcome': ('🎉 Hoş Geldin Kampanyası', service.run_welcome_campaign),
        }

        if campaign == 'all':
            campaigns_to_run = campaign_funcs.items()
        else:
            campaigns_to_run = [(campaign, campaign_funcs[campaign])]

        total_emails = 0
        total_eligible = 0

        for camp_key, (name, func) in campaigns_to_run:
            self.stdout.write(f'\n{name}')
            self.stdout.write('-' * 40)
            
            result = func()
            
            eligible = result.get('eligible_customers', result.get('new_customers', 0))
            sent = result.get('emails_sent', 0)
            
            total_eligible += eligible
            total_emails += sent
            
            self.stdout.write(f'  Uygun müşteri sayısı: {eligible}')
            self.stdout.write(f'  Gönderilen email: {sent}')
            
            if sent > 0:
                self.stdout.write(self.style.SUCCESS(f'  ✅ {sent} email gönderildi'))
            elif eligible > 0:
                self.stdout.write(self.style.WARNING(f'  ⚠️ {eligible} uygun müşteri var ama email gönderilemedi'))
            else:
                self.stdout.write(self.style.NOTICE(f'  ℹ️ Uygun müşteri bulunamadı'))

        # Summary
        self.stdout.write('')
        self.stdout.write('=' * 50)
        self.stdout.write(self.style.SUCCESS('📊 ÖZET'))
        self.stdout.write('=' * 50)
        self.stdout.write(f'  Toplam uygun müşteri: {total_eligible}')
        self.stdout.write(f'  Toplam gönderilen email: {total_emails}')
        self.stdout.write(f'  Oluşturulan bildirim: {service.results["notifications_created"]}')
        self.stdout.write(f'  Oluşturulan kupon: {service.results["coupons_generated"]}')
        
        if service.results['errors']:
            self.stdout.write(self.style.ERROR(f'  Hatalar: {len(service.results["errors"])}'))
            for err in service.results['errors'][:5]:
                self.stdout.write(f'    - {err}')

        if dry_run:
            self.stdout.write('')
            self.stdout.write(self.style.WARNING('⚠️ Bu bir DRY RUN idi. Gerçek email gönderilmedi.'))
