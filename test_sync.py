import os
from app import create_app
from sync_manager import sync_manager
from database import db
from models import Director

def test_sync():
    app = create_app()
    with app.app_context():
        print("Checking sync status...")
        status, details = sync_manager.check_for_mismatches()
        print(f"Status: {status}")
        print(f"Details: {details}")
        
        if status == "mismatch":
            print("Mismatch detected. This is expected if data was modified or sync didn't run yet.")
        elif status == "match":
            print("Sync is already healthy.")
        elif status == "empty_sheets":
            print("Sheets are empty. Running initial sync...")
            success, msg = sync_manager.sync_to_sheets()
            print(f"Sync result: {success}, {msg}")

if __name__ == "__main__":
    test_sync()
