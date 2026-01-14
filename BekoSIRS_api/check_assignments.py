import os
import django
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bekosirs_backend.settings')
django.setup()

from products.models import ProductAssignment, CustomUser

def check_assignments():
    first_name = "Yılmaz"
    last_name = "Ergün"
    user = CustomUser.objects.filter(first_name__iexact=first_name, last_name__iexact=last_name).first()
    
    if not user:
        print(f"User {first_name} {last_name} not found!")
        return

    print(f"Checking assignments for user: {user.username} (ID: {user.id})")
    
    assignments = ProductAssignment.objects.filter(customer=user)
    print(f"Total Assignments found: {assignments.count()}")
    
    for a in assignments:
        print(f"--- Assignment ID: {a.id} ---")
        print(f"Product: {a.product.name}")
        print(f"Status: {a.status}")
        print(f"Created At: {a.assigned_at}")
        
        # Check delivery
        try:
            d = a.delivery
            print(f"Linked Delivery ID: {d.id}, Status: {d.status}")
        except:
            print("No linked delivery.")

if __name__ == "__main__":
    check_assignments()
