import os
import django
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bekosirs_backend.settings')
django.setup()

from products.models import ProductAssignment, ProductOwnership

def fix_missing_ownerships():
    print("Checking for DELIVERED assignments without ProductOwnership...")
    
    # Find assignments that are DELIVERED
    delivered_assignments = ProductAssignment.objects.filter(status='DELIVERED')
    
    fixed_count = 0
    for assignment in delivered_assignments:
        user = assignment.customer
        product = assignment.product
        
        # Check if ownership exists
        ownership_exists = ProductOwnership.objects.filter(
            customer=user, 
            product=product
        ).exists()
        
        if not ownership_exists:
            print(f"Missing ownership for User: {user.username}, Product: {product.name}")
            
            # Create ownership
            ProductOwnership.objects.create(
                customer=user,
                product=product,
                purchase_date=assignment.assigned_at.date(), # Use assignment date as purchase date
                serial_number=f"AUTO-FIX-{assignment.id}"
            )
            print("  -> Created details ProductOwnership record.")
            fixed_count += 1
        else:
            # print(f"Ownership exists for User: {user.username}, Product: {product.name}")
            pass

    print(f"Scan complete. Fixed {fixed_count} missing ownerships.")

if __name__ == "__main__":
    fix_missing_ownerships()
