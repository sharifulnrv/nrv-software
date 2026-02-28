import os
import sys
import time
from app import create_app
from sync_manager import sync_manager, get_credentials_path
from models import Customer

# Mock environment if needed
if not os.environ.get('NEXUS_DATA_PATH'):
    os.environ['NEXUS_DATA_PATH'] = os.path.abspath(".")

app = create_app()

with app.app_context():
    print("Testing Google Sheets Sync...")
    print(f"Credentials File: {os.path.abspath(get_credentials_path())}")
    
    start_time = time.time()
    success, msg = sync_manager.sync_to_sheets()
    end_time = time.time()
    
    print(f"Sync Success: {success}")
    print(f"Sync Message: {msg}")
    print(f"Time taken: {end_time - start_time:.2f} seconds")

    if success:
        # Check if customer in DB is actually in the data being sent
        data = sync_manager.get_all_tables_data()
        customers = data.get('customer', [])
        print(f"Number of customers in sync data: {len(customers)}")
        if customers:
            print(f"Sample customer: {customers[0]['name']} (ID: {customers[0]['customer_id']})")
