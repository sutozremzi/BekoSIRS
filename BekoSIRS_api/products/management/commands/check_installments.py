# products/management/commands/check_installments.py
"""
Management command to check and process installment payments.
Run daily via cron: python manage.py check_installments

Görevler:
1. Vadesi geçmiş pending taksitleri 'overdue' yap
2. Gecikmiş taksitler için bildirim oluştur
3. Vadeye 3 gün kala hatırlatma bildirimi gönder
4. Tüm taksitler ödendiyse planı 'completed' yap
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from products.models import InstallmentPlan, Installment, Notification


class Command(BaseCommand):
    help = 'Taksit ödemelerini kontrol et, gecikmeleri işaretle ve bildirim gönder'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Değişiklik yapmadan sadece kontrol et',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        today = timezone.now().date()
        
        self.stdout.write(self.style.NOTICE(f"Taksit kontrolü başlatıldı: {today}"))

        # 1. Vadesi geçmiş pending taksitleri overdue yap
        overdue_count = self.mark_overdue_installments(today, dry_run)

        # 2. Gecikmiş taksitler için bildirim gönder
        overdue_notification_count = self.send_overdue_notifications(dry_run)

        # 3. 3 gün kala hatırlatma gönder
        reminder_count = self.send_due_reminders(today, dry_run)

        # 4. Tamamlanan planları işaretle
        completed_count = self.mark_completed_plans(dry_run)

        # Özet
        self.stdout.write(self.style.SUCCESS(f"""
Taksit Kontrolü Tamamlandı:
- Gecikmiş olarak işaretlenen: {overdue_count}
- Gecikme bildirimi gönderilen: {overdue_notification_count}
- Hatırlatma bildirimi gönderilen: {reminder_count}
- Tamamlanan plan sayısı: {completed_count}
{"(DRY RUN - değişiklik yapılmadı)" if dry_run else ""}
        """))

    def mark_overdue_installments(self, today, dry_run):
        """Vadesi geçmiş ve hala pending olan taksitleri overdue yap."""
        overdue_installments = Installment.objects.filter(
            status='pending',
            due_date__lt=today
        )
        
        count = overdue_installments.count()
        
        if count > 0 and not dry_run:
            overdue_installments.update(status='overdue')
            self.stdout.write(f"  → {count} taksit 'overdue' olarak işaretlendi")
        else:
            self.stdout.write(f"  → {count} taksit overdue (güncellenecek)")

        return count

    def send_overdue_notifications(self, dry_run):
        """Gecikmiş taksitler için müşteriye bildirim gönder."""
        # Son 24 saatte bildirim gönderilmemiş gecikmiş taksitler
        yesterday = timezone.now() - timedelta(days=1)
        
        overdue_installments = Installment.objects.filter(
            status='overdue'
        ).select_related('plan', 'plan__customer', 'plan__product')

        count = 0
        for installment in overdue_installments:
            # Check if notification was already sent recently
            existing = Notification.objects.filter(
                user=installment.plan.customer,
                title__contains='Taksit Ödemesi Gecikti',
                created_at__gte=yesterday,
                related_product=installment.plan.product
            ).exists()

            if not existing:
                if not dry_run:
                    Notification.objects.create(
                        user=installment.plan.customer,
                        notification_type='general',
                        title='⚠️ Taksit Ödemesi Gecikti',
                        message=f'{installment.plan.product.name} ürününün {installment.installment_number}. taksit ödemesi {installment.days_overdue} gündür gecikmiş durumda. Lütfen ödemenizi yapınız.',
                        related_product=installment.plan.product
                    )
                count += 1
                self.stdout.write(f"  → Gecikme bildirimi: {installment.plan.customer.username} - Taksit #{installment.installment_number}")

        return count

    def send_due_reminders(self, today, dry_run):
        """Vadeye 3 gün kala hatırlatma bildirimi gönder."""
        reminder_date = today + timedelta(days=3)
        yesterday = timezone.now() - timedelta(days=1)

        upcoming_installments = Installment.objects.filter(
            status='pending',
            due_date=reminder_date
        ).select_related('plan', 'plan__customer', 'plan__product')

        count = 0
        for installment in upcoming_installments:
            # Check if reminder was already sent
            existing = Notification.objects.filter(
                user=installment.plan.customer,
                title__contains='Taksit Hatırlatması',
                created_at__gte=yesterday,
                related_product=installment.plan.product
            ).exists()

            if not existing:
                if not dry_run:
                    Notification.objects.create(
                        user=installment.plan.customer,
                        notification_type='general',
                        title='📅 Taksit Hatırlatması',
                        message=f'{installment.plan.product.name} ürününün {installment.installment_number}. taksit ödemesi 3 gün sonra ({installment.due_date.strftime("%d.%m.%Y")}) yapılmalıdır. Tutar: {installment.amount}₺',
                        related_product=installment.plan.product
                    )
                count += 1
                self.stdout.write(f"  → Hatırlatma: {installment.plan.customer.username} - Taksit #{installment.installment_number}")

        return count

    def mark_completed_plans(self, dry_run):
        """Tüm taksitleri ödenmiş planları completed olarak işaretle."""
        active_plans = InstallmentPlan.objects.filter(status='active')
        
        count = 0
        for plan in active_plans:
            # Check if all installments are paid
            unpaid = plan.installments.exclude(status='paid').exists()
            
            if not unpaid:
                if not dry_run:
                    plan.status = 'completed'
                    plan.save()
                    
                    # Send completion notification
                    Notification.objects.create(
                        user=plan.customer,
                        notification_type='general',
                        title='🎉 Taksit Planı Tamamlandı!',
                        message=f'{plan.product.name} ürününe ait tüm taksitleriniz başarıyla ödenmiştir. Tebrikler!',
                        related_product=plan.product
                    )
                count += 1
                self.stdout.write(f"  → Plan tamamlandı: {plan.customer.username} - {plan.product.name}")

        return count
