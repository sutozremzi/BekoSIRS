import os
import psycopg2
from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path)

conn = psycopg2.connect(
    dbname=os.getenv('DB_NAME'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'),
    host=os.getenv('DB_HOST'),
    port=os.getenv('DB_PORT', '5432')
)
cur = conn.cursor()

cur.execute("SELECT id, username FROM products_customuser WHERE username IN ('admin', 'test')")
for row in cur.fetchall():
    print(f"User {row[1]}: ID {row[0]}")

cur.close()
conn.close()
