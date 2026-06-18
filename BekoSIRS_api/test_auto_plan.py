"""
End-to-end test for the auto-planning system.
1. Assign products to customers across different districts
2. Run generate_auto_plan()
3. Print the full plan preview
"""
import os, sys, random, json, io

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "bekosirs_backend.settings")

import django
django.setup()

from products.models import CustomUser, Product, ProductAssignment, Delivery
from products.services.auto_planner import generate_auto_plan

# ── Step 1: Check current state ──
customers = list(CustomUser.objects.filter(role='customer'))
products = list(Product.objects.all()[:20])

print(f"=== MEVCUT DURUM ===")
print(f"Toplam musteri: {len(customers)}")
print(f"Toplam urun: {len(products)}")

existing_planned = ProductAssignment.objects.filter(status='PLANNED').exclude(delivery__isnull=False).count()
print(f"Mevcut PLANNED atama (delivery yok): {existing_planned}")

# ── Step 2: Create test assignments ──
if existing_planned == 0:
    print(f"\n=== URUN ATAMALARI OLUSTURULUYOR ===")
    
    # Make sure we have enough products
    if len(products) < 5:
        print("HATA: Yeterli urun yok!")
        sys.exit(1)
    
    assignments_to_create = []
    
    # Spread assignments across customers to test grouping
    # Some customers get multiple products (same-address grouping test)
    test_plan = [
        # (customer_index, product_indices, quantity)  
        (0, [0], 1),       # Customer 0: 1 product
        (0, [1], 1),       # Customer 0: another product (same address - should group)
        (1, [2], 1),       # Customer 1: 1 product
        (2, [3], 2),       # Customer 2: 2 units of same product
        (3, [0], 1),       # Customer 3: 1 product
        (3, [4], 1),       # Customer 3: another product (same address grouping)
        (3, [2], 1),       # Customer 3: third product (heavy address)
        (4, [1], 1),       # Customer 4
        (5, [3], 1),       # Customer 5
        (6, [0], 1),       # Customer 6
        (7, [2], 1),       # Customer 7
        (8, [4], 1),       # Customer 8
        (9, [1], 1),       # Customer 9
        (10, [3], 1),      # Customer 10
        (11, [0], 1),      # Customer 11
        (12, [2], 1),      # Customer 12
        (13, [4], 1),      # Customer 13
        (14, [1], 1),      # Customer 14
    ]
    
    created = 0
    for ci, pi_list, qty in test_plan:
        if ci >= len(customers):
            continue
        for pi in pi_list:
            if pi >= len(products):
                continue
            cust = customers[ci]
            prod = products[pi]
            
            # Check if this exact assignment already exists
            if ProductAssignment.objects.filter(customer=cust, product=prod, status='PLANNED').exists():
                continue
                
            assignment = ProductAssignment.objects.create(
                customer=cust,
                product=prod,
                quantity=qty,
                status='PLANNED',
                notes='[TEST] Auto-plan test assignment'
            )
            created += 1
            
            # Get customer location info
            district = "?"
            try:
                district = cust.customer_address.district.name if cust.customer_address.district else "?"
            except:
                pass
            print(f"  Atandi: {cust.first_name} {cust.last_name} ({district}) <- {prod.name} x{qty}")
    
    print(f"\nToplam {created} yeni atama olusturuldu.")
else:
    print(f"\nZaten {existing_planned} adet PLANNED atama var, yenisi olusturulmadi.")

# ── Step 3: Run auto-plan ──
print(f"\n{'='*60}")
print(f"=== OTOMATIK PLAN OLUSTURULUYOR ===")
print(f"{'='*60}")

plan = generate_auto_plan()

if not plan.get('days'):
    print("\nHICABIR PLAN OLUSTURULAMADI!")
    if plan.get('warnings'):
        print(f"Uyarilar: {plan['warnings']}")
    sys.exit(1)

# ── Step 4: Print results ──
summary = plan.get('summary', {})
print(f"\n--- OZET ---")
print(f"Toplam gun: {summary.get('total_days', 0)}")
print(f"Toplam teslimat: {summary.get('total_deliveries', 0)}")
print(f"Toplam mesafe: {summary.get('total_distance_km', 0)} km")

warnings = plan.get('warnings', {})
if warnings.get('no_coordinates'):
    print(f"[!] Koordinatsiz atama ID'leri: {warnings['no_coordinates']}")
if warnings.get('over_time_days'):
    print(f"[!] 6 saati asan gunler: {warnings['over_time_days']}")

print(f"\n--- GUN GUN PLAN ---")
for i, day in enumerate(plan['days']):
    duration_h = (day.get('total_duration_min', 0)) / 60
    over = " [!!! 6 SAATI ASIYOR]" if duration_h > 6 else ""
    print(f"\n  GUN {i+1}: {day['weekday']}, {day['date']}")
    print(f"    Bolgeler: {', '.join(day.get('district_names', []))}")
    print(f"    Teslimat: {day['delivery_count']} adet")
    print(f"    Mesafe: {day.get('total_distance_km', 0)} km")
    print(f"    Sure: {day.get('total_duration_min', 0)} dk ({duration_h:.1f} saat){over}")
    
    print(f"    Duraklar:")
    for stop in day.get('stops', []):
        coord_tag = " ~yaklasik" if stop.get('coord_source') == 'district_fallback' else ""
        products_str = ", ".join(
            f"{p['product_name']}x{p['quantity']}" for p in stop.get('products', [])
        )
        print(f"      #{stop.get('stop_order', '?')}: {stop['customer_name']} ({stop['district_name']}{coord_tag})")
        print(f"          Urunler: {products_str}")
        print(f"          Mesafe: {stop.get('dist_from_prev', 0)} km")

print(f"\n{'='*60}")
print(f"TEST TAMAMLANDI - Plan onaya hazir!")
print(f"{'='*60}")
