import os
import json
import psycopg2
from dotenv import load_dotenv
from collections import Counter

# Load environment variables
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path)

DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT', '5432')

# Load db_export.json
try:
    with open('db_export.json', 'r', encoding='utf-8') as f:
        export_data = json.load(f)
        
    local_counts = Counter()
    for item in export_data:
        local_counts[item['model']] += 1
except Exception as e:
    print(f"Error reading db_export.json: {e}")
    export_data = []
    local_counts = Counter()

print(f"Loaded {len(export_data)} records from db_export.json")

try:
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )
    cur = conn.cursor()
    
    print("\n--- Veritabanı Karşılaştırması (Local Export vs Supabase Postgres) ---")
    print(f"{'Tablo / Model':<35} | {'Eski DB (Export)':<15} | {'Yeni DB (Postgres)':<15} | {'Fark'}")
    print("-" * 80)
    
    # Let's check common tables
    models_to_check = [
        ('auth.user', 'auth_user'),
        ('products.customuser', 'products_customuser'),
        ('products.product', 'products_product'),
        ('products.category', 'products_category'),
        ('products.area', 'products_area'),
        ('products.district', 'products_district'),
        ('products.productownership', 'products_productownership'),
        ('products.delivery', 'products_delivery'),
        ('products.deliveryroute', 'products_deliveryroute'),
        ('products.wishlistitem', 'products_wishlistitem'),
        ('products.customeraddress', 'products_customeraddress')
    ]
    
    # add any other models found in local_counts
    for model_name, _ in local_counts.items():
        if not any(m[0] == model_name for m in models_to_check):
            table_name = model_name.replace('.', '_')
            models_to_check.append((model_name, table_name))

    for model, table in models_to_check:
        local_count = local_counts.get(model, 0)
        
        try:
            cur.execute(f"SELECT count(*) FROM {table}")
            pg_count = cur.fetchone()[0]
        except Exception as e:
            conn.rollback()
            pg_count = "HATA (Tablo Yok?)"
            
        # Only print if at least one side has > 0
        if local_count > 0 or (isinstance(pg_count, int) and pg_count > 0):
            diff = pg_count - local_count if isinstance(pg_count, int) else "N/A"
            diff_str = f"{diff:+d}" if isinstance(diff, int) and diff != 0 else str(diff) if diff != 0 else "-"
            print(f"{model:<35} | {local_count:<15} | {pg_count:<15} | {diff_str}")

    cur.close()
    conn.close()
    
except Exception as e:
    print(f"Error querying postgres: {e}")

