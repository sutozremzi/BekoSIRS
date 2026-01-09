import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from products.models import *
from django.contrib.auth import get_user_model
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

User = get_user_model()
user = User.objects.get(username='testmobile')
products = list(Product.objects.all()[:5])

print(f'User: {user.username}')
print(f'Products: {len(products)}')

# 1. ProductOwnership
for i, p in enumerate(products[:3]):
    ownership, created = ProductOwnership.objects.get_or_create(
        customer=user, 
        product=p, 
        defaults={'purchase_date': date.today() - timedelta(days=30*(i+1))}
    )
    print(f'Ownership: {p.name[:25]} - {"NEW" if created else "exists"}')

# 2. Wishlist
wishlist, _ = Wishlist.objects.get_or_create(customer=user)
for p in products[3:5]:
    item, created = WishlistItem.objects.get_or_create(wishlist=wishlist, product=p)
    print(f'Wishlist: {p.name[:25]} - {"NEW" if created else "exists"}')

# 3. InstallmentPlan
plan, created = InstallmentPlan.objects.get_or_create(
    customer=user, 
    product=products[0],
    defaults={
        'total_amount': 15000,
        'down_payment': 3000,
        'installment_count': 6,
        'start_date': date.today() - timedelta(days=60),
        'status': 'active'
    }
)
print(f'InstallmentPlan: {plan.id} - {"NEW" if created else "exists"}')

# 4. Installments
if plan.installments.count() == 0:
    amount = (plan.total_amount - plan.down_payment) / plan.installment_count
    for i in range(1, 7):
        due = plan.start_date + relativedelta(months=i)
        status = 'paid' if i <= 2 else ('overdue' if due < date.today() else 'pending')
        Installment.objects.create(
            plan=plan,
            installment_number=i,
            amount=amount,
            due_date=due,
            status=status,
            payment_date=due if status == 'paid' else None
        )
        print(f'  Installment {i}: {due} - {status}')

print('DONE!')
