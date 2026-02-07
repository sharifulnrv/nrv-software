import sqlite3
import os

DB_PATH = 'instance/nexus.db'

def migrate():
    if not os.path.exists(DB_PATH):
        print("Database not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute("PRAGMA table_info(bank_transaction)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if 'transaction_details' not in columns:
            print("Adding 'transaction_details' column...")
            cursor.execute("ALTER TABLE bank_transaction ADD COLUMN transaction_details TEXT")
            conn.commit()
            print("Migration successful.")
        else:
            print("Column 'transaction_details' already exists.")
            
    except Exception as e:
        print(f"Migration failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
