"""
Assign KKTC district-based addresses and coordinates to customers who lack them.
Run: python manage.py shell < assign_coords.py
"""
import os, sys, random

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "bekosirs_backend.settings")

import django
django.setup()

from products.models import CustomUser, CustomerAddress, District, Area

# KKTC real residential coordinates (slightly randomized around real neighborhoods)
KKTC_LOCATIONS = [
    # Lefkosa (Nicosia)
    {"district": "Lefkosa", "coords": [
        (35.1856, 33.3823), (35.1900, 33.3650), (35.1750, 33.3900),
        (35.1820, 33.3760), (35.1930, 33.3540),
    ]},
    # Girne (Kyrenia)
    {"district": "Girne", "coords": [
        (35.3364, 33.3178), (35.3400, 33.3100), (35.3300, 33.3250),
        (35.3280, 33.3350), (35.3450, 33.3050),
    ]},
    # Gazimagusa (Famagusta)
    {"district": "Gazimagusa", "coords": [
        (35.1257, 33.9400), (35.1300, 33.9350), (35.1200, 33.9450),
        (35.1350, 33.9300), (35.1180, 33.9500),
    ]},
    # Guzelyurt (Morphou)
    {"district": "Guzelyurt", "coords": [
        (35.1986, 32.9930), (35.2050, 32.9850), (35.1920, 32.9990),
        (35.2100, 32.9780), (35.1880, 33.0050),
    ]},
    # Iskele
    {"district": "Iskele", "coords": [
        (35.2860, 33.8770), (35.2900, 33.8700), (35.2820, 33.8850),
        (35.2950, 33.8650), (35.2780, 33.8900),
    ]},
]

def find_district(name_hint):
    """Try to find a district by partial name match."""
    for d in District.objects.all():
        # Normalize for comparison
        d_lower = d.name.lower().replace("i", "i").replace("a", "a")
        hint_lower = name_hint.lower()
        if hint_lower in d_lower or d_lower.startswith(hint_lower[:4]):
            return d
    return None

def main():
    customers = CustomUser.objects.filter(role='customer')
    updated = 0
    created = 0

    # Get all districts for fallback
    all_districts = list(District.objects.all())

    for i, customer in enumerate(customers):
        try:
            addr = customer.customer_address
            has_coords = addr.latitude and addr.longitude
        except CustomerAddress.DoesNotExist:
            addr = None
            has_coords = False

        if has_coords:
            continue  # Already has coordinates

        # Pick a KKTC location (cycle through regions)
        region = KKTC_LOCATIONS[i % len(KKTC_LOCATIONS)]
        coord = random.choice(region["coords"])

        # Add small random offset for realism (50-500m)
        lat = coord[0] + random.uniform(-0.003, 0.003)
        lng = coord[1] + random.uniform(-0.003, 0.003)

        # Find matching district
        district = find_district(region["district"])

        if addr is None:
            # Create new CustomerAddress
            addr = CustomerAddress.objects.create(
                user=customer,
                latitude=round(lat, 7),
                longitude=round(lng, 7),
                district=district,
                open_address=f"Sokak No: {random.randint(1,50)}, Apt: {random.randint(1,10)}",
            )
            created += 1
            print(f"  CREATED: {customer.username} -> {region['district']} ({lat:.4f}, {lng:.4f})")
        else:
            # Update existing address with coordinates
            addr.latitude = round(lat, 7)
            addr.longitude = round(lng, 7)
            if not addr.district:
                addr.district = district
            addr.save()
            updated += 1
            print(f"  UPDATED: {customer.username} -> {region['district']} ({lat:.4f}, {lng:.4f})")

    print(f"\nDone! Created: {created}, Updated: {updated}")

    # Also update District center coordinates if they are missing
    district_centers = {
        "Lefkosa": (35.1856, 33.3823),
        "Girne": (35.3364, 33.3178),
        "Gazimagusa": (35.1257, 33.9400),
        "Guzelyurt": (35.1986, 32.9930),
        "Iskele": (35.2860, 33.8770),
    }
    for d in District.objects.all():
        if not d.center_lat or not d.center_lng:
            for hint, (clat, clng) in district_centers.items():
                if hint.lower()[:4] in d.name.lower()[:6]:
                    d.center_lat = clat
                    d.center_lng = clng
                    d.save()
                    print(f"  District center set: {d.name} -> ({clat}, {clng})")
                    break

main()
