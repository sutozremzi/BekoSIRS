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

print(f"Connecting to {DB_HOST} as {DB_USER}...")

try:
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )
    cur = conn.cursor()
    
    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
    tables = [row[0] for row in cur.fetchall()]
    
    # Try empty all tables for resetting (in the right order if possible, though CASCADE handles it)
    print("Clearing database tables...")
    for table in tables:
        if table.startswith('django_') or table.startswith('auth_') or table.startswith('products_') or table.startswith('token_'):
            try:
                cur.execute(f"TRUNCATE TABLE {table} CASCADE")
                print(f"Truncated {table}")
            except Exception as e:
                print(f"Could not truncate {table}: {e}")
                conn.rollback()

    conn.commit()
    print("Database cleared. Ready for loaddata.")
    
    cur.close()
    conn.close()
except Exception as e:
    print(f"Database error: {e}")
