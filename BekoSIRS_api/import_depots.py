import json
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bekosirs_backend.settings')
django.setup()

from django.core.serializers import deserialize
from django.db import transaction

def load_depots():
    with open('db_export.json', 'r', encoding='utf-8') as f:
        export_data = json.load(f)

    depot_data = [item for item in export_data if item['model'] == 'products.depotlocation']
    print(f"Found {len(depot_data)} depots in export.")
    
    if not depot_data:
        return
        
    model_json = json.dumps(depot_data)
    objects = list(deserialize("json", model_json, ignorenonexistent=True))
    
    success_count = 0
    for obj in objects:
        try:
            with transaction.atomic():
                obj.save()
                success_count += 1
        except Exception as e:
            print(f"Error saving depot '{obj.object.name}': {e}")
            
    print(f"Successfully loaded {success_count}/{len(depot_data)} depots.")

if __name__ == '__main__':
    load_depots()
