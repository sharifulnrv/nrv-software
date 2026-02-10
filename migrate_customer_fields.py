import sqlite3
import os

DB_PATH = 'instance/nexus.db'

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check existing columns
        cursor.execute("PRAGMA table_info(customer)")
        columns = [info[1] for info in cursor.fetchall()]
        
        new_fields = {
            'father_name': 'TEXT',
            'mother_name': 'TEXT',
            'dob': 'TEXT',
            'religion': 'TEXT',
            'profession': 'TEXT',
            'nid_no': 'TEXT',
            'present_address': 'TEXT',
            'permanent_address': 'TEXT'
        }
        
        for field, type_ in new_fields.items():
            if field not in columns:
                print(f"Adding '{field}' column to 'customer' table...")
                cursor.execute(f"ALTER TABLE customer ADD COLUMN {field} {type_}")
                print(f"Added {field}.")
            else:
                print(f"Column '{field}' already exists.")
        
        conn.commit()
        print("Migration completed successfully.")
            
    except Exception as e:
        print(f"Migration failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
