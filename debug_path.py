import os
import json
import sqlite3

def get_app_data_path():
    app_data = os.getenv('APPDATA')
    if not app_data:
        app_data = os.path.expanduser("~")
    return os.path.join(app_data, 'NexusRiverView')

def get_launcher_config():
    config_path = os.path.join(get_app_data_path(), 'launcher_config.json')
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

config = get_launcher_config()
data_path = config.get('data_path')

print(f"Resolved Data Path from Launcher Config: {data_path}")

if data_path and os.path.exists(data_path):
    db_path = os.path.join(data_path, 'nexus.db')
    print(f"Checking Database: {db_path}")
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(director)")
        cols = [c[1] for c in cursor.fetchall()]
        print(f"Columns in 'director' table: {cols}")
        if 'updated_at' in cols:
            print("RESULT: updated_at column EXISTS.")
        else:
            print("RESULT: updated_at column MISSING.")
        conn.close()
    else:
        print("RESULT: Database file NOT FOUND at that path.")
else:
    print("RESULT: Data Path NOT FOUND or does not exist.")
