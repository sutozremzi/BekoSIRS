import sqlite3
from datetime import datetime
import sys

def main():
    try:
        conn = sqlite3.connect('db.sqlite3')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id FROM products_servicerequest 
            WHERE status NOT IN ('completed', 'cancelled')
            AND id NOT IN (SELECT service_request_id FROM products_servicequeue)
        ''')
        missing_reqs = cursor.fetchall()
        
        if missing_reqs:
            cursor.execute('SELECT MAX(queue_number) FROM products_servicequeue')
            result = cursor.fetchone()[0]
            base_queue = result if result else 0
            
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            for i, (req_id,) in enumerate(missing_reqs, 1):
                q_num = base_queue + i
                cursor.execute('''
                    INSERT INTO products_servicequeue (service_request_id, queue_number, priority, estimated_wait_time, entered_queue_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (req_id, q_num, 5, q_num * 30, now))
                print(f'Inserted queue {q_num} for request {req_id}')
            
            conn.commit()
            print("Successfully updated database")
        else:
            print('No missing queue entries found.')
        conn.close()
    except Exception as e:
        print(f'Error: {e}')
        sys.exit(1)

if __name__ == '__main__':
    main()
