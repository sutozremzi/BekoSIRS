import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path)

DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT', '5432')

try:
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )
    cur = conn.cursor()
    
    # Get total user count
    cur.execute("SELECT count(*) FROM products_customuser")
    total_users = cur.fetchone()[0]
    
    print("\n--- MÜŞTERİ BİLGİLERİ ---")
    print(f"Toplam Kullanıcı Sayısı (products_customuser bloğu): {total_users}")
    
    # Check what columns exist to distinguish user types
    cur.execute("SELECT * FROM products_customuser LIMIT 0")
    colnames = [desc[0] for desc in cur.description]
    
    # Try different grouping columns commonly used in Django / Custom Models
    if 'role' in colnames:
        cur.execute("SELECT role, count(*) FROM products_customuser GROUP BY role")
        print("\nRol Dağılımı:")
        for row in cur.fetchall():
            print(f"- {row[0] if row[0] else 'Belirtilmemiş'}: {row[1]}")
            
    if 'user_type' in colnames:
        cur.execute("SELECT user_type, count(*) FROM products_customuser GROUP BY user_type")
        print("\nKullanıcı Tipi Dağılımı:")
        for row in cur.fetchall():
            print(f"- {row[0] if row[0] else 'Belirtilmemiş'}: {row[1]}")
            
    if 'is_staff' in colnames and 'is_superuser' in colnames:
        cur.execute("""
            SELECT 
                CASE 
                    WHEN is_superuser = true THEN 'Süper Yönetici (Admin)'
                    WHEN is_staff = true THEN 'Personel (Staff)'
                    ELSE 'Normal Kullanıcı (Örn: Müşteri)'
                END as type,
                count(*)
            FROM products_customuser
            GROUP BY 1
        """)
        print("\nSistem Yetkilerine Göre Dağılım (Django Default):")
        for row in cur.fetchall():
            print(f"- {row[0]}: {row[1]}")

    cur.close()
    conn.close()
    
except Exception as e:
    print(f"Error querying database: {e}")
