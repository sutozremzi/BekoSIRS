import json
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bekosirs_backend.settings')
django.setup()

from django.db import transaction
from django.core.management import call_command
from django.db import IntegrityError
from django.db.models.signals import pre_save, post_save

# Disable signals if necessary
# from products.models import ProductAssignment, Delivery

def load_data_safely():
    with open('db_export.json', 'r', encoding='utf-8') as f:
        export_data = json.load(f)

    # Dictionary to categorize models
    data_by_model = {}
    for item in export_data:
        model = item['model']
        if model not in data_by_model:
            data_by_model[model] = []
        data_by_model[model].append(item)

    # Order of models to load to respect foreign key constraints
    ordered_models = [
        'auth.group',
        'products.customuser',
        'products.category',
        'products.product',
        'products.district',
        'products.area',
        'products.customeraddress',
        'products.depotlocation',
        'products.productownership',
        'products.wishlist',
        'products.wishlistitem',
        'products.productassignment',
        'products.deliveryroute',
        'products.delivery',
        'products.deliveryroutestop',
        'products.review',
        'products.installmentplan',
        'products.installment',
        'products.servicerequest',
        'products.servicequeue',
        'products.recommendation',
        'products.notification',
        'products.usernotificationpreference',
        'products.viewhistory',
        'products.searchhistory',
        'token_blacklist.outstandingtoken',
        'token_blacklist.blacklistedtoken',
    ]

    for model_name in set(data_by_model.keys()) - set(ordered_models):
        ordered_models.append(model_name)

    print(f"Total models to load: {len(data_by_model)}")

    # Load data model by model, record by record to isolate errors
    from django.apps import apps
    from django.core.serializers import deserialize

    for model_name in ordered_models:
        if model_name not in data_by_model:
            continue
            
        print(f"\nLoading {model_name}...")
        items = data_by_model[model_name]
        
        # Serialize back to JSON for Django deserializer
        model_json = json.dumps(items)
        
        objects = list(deserialize("json", model_json, ignorenonexistent=True))
        success_count = 0
        error_count = 0
        
        for obj in objects:
            # Remap user IDs
            if hasattr(obj.object, 'created_by_id') and obj.object.created_by_id in [10002, 10003]:
                obj.object.created_by_id = 1 if obj.object.created_by_id == 10002 else 2
            if hasattr(obj.object, 'user_id') and obj.object.user_id in [10002, 10003]:
                obj.object.user_id = 1 if obj.object.user_id == 10002 else 2
            if hasattr(obj.object, 'customer_id') and obj.object.customer_id in [10002, 10003]:
                obj.object.customer_id = 1 if obj.object.customer_id == 10002 else 2
            if hasattr(obj.object, 'assigned_by_id') and obj.object.assigned_by_id in [10002, 10003]:
                obj.object.assigned_by_id = 1 if obj.object.assigned_by_id == 10002 else 2
            if hasattr(obj.object, 'driver_id') and obj.object.driver_id in [10002, 10003]:
                obj.object.driver_id = 1 if obj.object.driver_id == 10002 else 2
            if hasattr(obj.object, 'wishlist_id') and obj.object.wishlist_id in [1, 2]: # Wishlist PK changed maybe? Better to just let it fail if wishlist is missing
                pass

            try:
                with transaction.atomic():
                    obj.save()
                    success_count += 1
            except IntegrityError as e:
                error_count += 1
                if error_count < 3: # Print first few errors
                    print(f"  Error loading {model_name} pk={obj.object.pk}: {e}")
            except Exception as e:
                error_count += 1
                if error_count < 3:
                    print(f"  Unknown Error {model_name} pk={obj.object.pk}: {e}")
                    
        print(f"  ✓ Loaded {success_count}/{len(items)} for {model_name} ({error_count} failed)")

if __name__ == '__main__':
    load_data_safely()
