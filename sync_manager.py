import os
import sys
import sqlite3
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import time
from database import db
from models import Director, Customer, Transaction, PettyCash, Bank, BankTransaction

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def get_credentials_path():
    """Prioritizes credentials.json in the external data folder."""
    # 1. Try environment variable set by launcher
    data_dir = os.environ.get('NEXUS_DATA_PATH')
    if data_dir:
        ext_path = os.path.join(data_dir, "credentials.json")
        if os.path.exists(ext_path):
            return ext_path
    
    # 2. Try default external path
    default_ext = "C:/NRV/credentials.json"
    if os.path.exists(default_ext):
        return default_ext

    # 3. Fallback to bundled resource or local root
    return resource_path("credentials.json")

# Configuration
SHEET_ID = "1Uapf1c4wDZ4hGfa1bqSbRjF45VodFv2-jtzgLL4VDq0"
CREDENTIALS_FILE = get_credentials_path()

class SyncManager:
    def __init__(self, app=None):
        self.app = app
        self._client = None
        self._spreadsheet = None

    @property
    def client(self):
        if self._client is None:
            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            try:
                creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
                self._client = gspread.authorize(creds)
            except Exception as e:
                print(f"Failed to authorize Google Sheets: {e}")
        return self._client

    @property
    def spreadsheet(self):
        if self._spreadsheet is None and self.client:
            try:
                self._spreadsheet = self.client.open_by_key(SHEET_ID)
            except Exception as e:
                print(f"Failed to open spreadsheet: {e}")
        return self._spreadsheet

    def get_all_tables_data(self):
        """Fetches all data from the database."""
        data = {}
        models = {
            'director': Director,
            'customer': Customer,
            'transaction': Transaction,
            'petty_cash': PettyCash,
            'bank': Bank,
            'bank_transaction': BankTransaction
        }
        for name, model in models.items():
            if name == 'customer':
                records = model.query.order_by(model.customer_id).all()
            else:
                records = model.query.all()
            data[name] = [self._model_to_dict(name, r) for r in records]
        return data

    def _model_to_dict(self, table_name, record):
        """Converts a model instance to a dictionary, handling specific types."""
        d = {}
        for column in record.__table__.columns:
            val = getattr(record, column.name)
            if isinstance(val, datetime):
                # Use a standard ISO format for comparison/storage
                d[column.name] = val.strftime("%Y-%m-%d %H:%M:%S")
            elif val is None:
                d[column.name] = ""
            else:
                d[column.name] = str(val)
        return d

    def sync_to_sheets(self):
        """Exports local database to Google Sheets (One-way: DB -> Sheets)."""
        if not self.spreadsheet:
            return False, "Spreadsheet not found"

        data = self.get_all_tables_data()
        for table_name, rows in data.items():
            try:
                try:
                    worksheet = self.spreadsheet.worksheet(table_name)
                    worksheet.clear()
                except gspread.exceptions.WorksheetNotFound:
                    worksheet = self.spreadsheet.add_worksheet(title=table_name, rows="100", cols="20")
                
                if rows:
                    headers = list(rows[0].keys())
                    values = [headers] + [[row[h] for h in headers] for row in rows]
                    worksheet.resize(rows=len(values), cols=len(headers))
                    worksheet.update('A1', values)
                time.sleep(1) # Rate limiting
            except Exception as e:
                print(f"Error syncing {table_name} to sheets: {e}")
        return True, "Sync to sheets completed"

    def fetch_from_sheets(self):
        """Fetches all data from Google Sheets."""
        if not self.spreadsheet:
            return None
        
        sheet_data = {}
        for worksheet in self.spreadsheet.worksheets():
            table_name = worksheet.title
            rows = worksheet.get_all_records()
            sheet_data[table_name] = rows
        return sheet_data

    def check_for_mismatches(self):
        """Compares local DB with Sheets and returns status."""
        db_data = self.get_all_tables_data()
        sheet_data = self.fetch_from_sheets()
        
        if not sheet_data:
            return "empty_sheets", []

        mismatches = []
        for table_name, db_rows in db_data.items():
            s_rows = sheet_data.get(table_name, [])
            if len(db_rows) != len(s_rows):
                mismatches.append(f"Row count mismatch in {table_name}: DB={len(db_rows)}, Sheets={len(s_rows)}")
                continue
            
            # Simple content check (can be expanded to check timestamps)
            # For now, if counts match, we might check last modified if available
            # However, the user wants "latest edit" logic.
        
        return ("mismatch" if mismatches else "match"), mismatches

    def restore_db_from_sheets(self):
        """Wipes local DB and rebuilds from Sheets."""
        sheet_data = self.fetch_from_sheets()
        if not sheet_data:
            return False, "No data found in Sheets"

        from logic import restore_from_data_dict
        success, msg = restore_from_data_dict(sheet_data)
        return success, msg

sync_manager = SyncManager()
