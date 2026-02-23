import sqlite3
import os

DB_PATH = "instance/nexus.db"

def add_timestamp_column():
    if not os.path.exists(DB_PATH):
        print("Database not found. Skipping migration.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [t[0] for t in cursor.fetchall() if t != 'sqlite_sequence']
    
    for table in tables:
        try:
            print(f"Checking updated_at in {table}...")
            cursor.execute(f"PRAGMA table_info(\"{table}\")")
            columns = [c[1] for c in cursor.fetchall()]
            
            if 'updated_at' not in columns:
                print(f"  Adding updated_at to {table}...")
                cursor.execute(f"ALTER TABLE \"{table}\" ADD COLUMN updated_at DATETIME")
                cursor.execute(f"UPDATE \"{table}\" SET updated_at = CURRENT_TIMESTAMP")
                print(f"  Success.")
            else:
                print(f"  Column already exists in {table}.")
        except Exception as e:
            print(f"  Error: {e}")
                
    conn.commit()
    conn.close()
    print("Migration completed.")

if __name__ == "__main__":
    add_timestamp_column()
