import os
import sys
import logging

# Set the data path environment variable so app uses the correct DB
def get_active_data_path():
    """Matches the logic in fix_db.py and run_gui.py."""
    import os, json
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
    return os.path.abspath('instance') # Fallback

active_path = get_active_data_path()
os.environ['NEXUS_DATA_PATH'] = active_path
print(f"FORCING SYNC FROM: {active_path}")

from app import create_app
from database import db
from sync_manager import sync_manager

def force_upload():
    print("Initializing Flask App with database at instance/nexus.db...")
    app = create_app()
    
    with app.app_context():
        print("Checking tables...")
        from models import Director, Customer, Transaction, PettyCash, Bank, BankTransaction
        
        counts = {
            'Director': Director.query.count(),
            'Customer': Customer.query.count(),
            'Transaction': Transaction.query.count(),
            'PettyCash': PettyCash.query.count(),
            'Bank': Bank.query.count(),
            'BankTransaction': BankTransaction.query.count()
        }
        print(f"Local Data Counts: {counts}")
        
        print("\nStarting forced upload to Google Sheets...")
        try:
            sync_manager.sync_to_sheets()
            print("\nSUCCESS: Data from instance/nexus.db has been pushed to Google Sheets.")
        except Exception as e:
            print(f"\nERROR during upload: {e}")

if __name__ == "__main__":
    force_upload()
