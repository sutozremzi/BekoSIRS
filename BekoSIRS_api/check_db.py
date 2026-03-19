import sqlite3
import json
import sys

def main():
    try:
        conn = sqlite3.connect('db.sqlite3')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, status, request_type FROM products_servicerequest")
        reqs = [dict(row) for row in cursor.fetchall()]
        
        cursor.execute("SELECT id, service_request_id, queue_number, priority FROM products_servicequeue")
        queues = [dict(row) for row in cursor.fetchall()]
        
        print("Service Requests:")
        for r in reqs[:5]: print(r)
        
        print("\nService Queues:")
        for q in queues[:5]: print(q)
        
        conn.close()
    except Exception as e:
        print(f'Error: {e}')

if __name__ == '__main__':
    main()
