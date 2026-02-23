import sqlite3
import os
import json

def get_app_data_path():
    app_data = os.getenv('APPDATA')
    if not app_data:
        app_data = os.path.expanduser("~") # Fallback to home
    return os.path.join(app_data, 'NexusRiverView')

def get_launcher_config():
    """Read path from launcher config, just like run_gui.py does."""
    app_data = os.getenv('APPDATA')
    if not app_data:
        app_data = os.path.expanduser("~")
    config_path = os.path.join(app_data, 'NexusRiverView', 'launcher_config.json')
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                return config.get('data_path')
        except:
            pass
    return None

def get_db_path():
    # 1. Try launcher config
    path = get_launcher_config()
    if path:
        db_path = os.path.join(path, "nexus.db")
        if os.path.exists(db_path):
            return db_path
            
    # 2. Try default location
    if os.path.exists("C:/NRV/nexus.db"):
        return "C:/NRV/nexus.db"
        
    # 3. Try instance folder
    if os.path.exists("instance/nexus.db"):
        return "instance/nexus.db"
        
    return None

def migrate_auto():
    db_path = get_db_path()
    if not db_path:
        print("Could not locate nexus.db. Please ensure the app has been run once.")
        return

    print(f"Migrating database at: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [t[0] for t in cursor.fetchall() if t[0] != 'sqlite_sequence']
    
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
            print(f"  Error migrating {table}: {e}")
                
    conn.commit()
    conn.close()
    print("Migration finished.")

if __name__ == "__main__":
    migrate_auto()
