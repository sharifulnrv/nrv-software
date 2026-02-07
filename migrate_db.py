import sqlite3
import os

DB_PATH = 'instance/nexus.db'

def migrate():
    if not os.path.exists(DB_PATH):
        print("Database not found, nothing to migrate (will be created fresh).")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if column exists
        cursor.execute("PRAGMA table_info(petty_cash)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if 'images' not in columns:
            print("Adding 'images' column to 'petty_cash' table...")
            cursor.execute("ALTER TABLE petty_cash ADD COLUMN images TEXT")
            conn.commit()
            print("Migration successful.")
        else:
            print("Column 'images' already exists.")
            
    except Exception as e:
        print(f"Migration failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
