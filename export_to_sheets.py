import sqlite3
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import time

# Configuration
DB_PATH = "instance/nexus.db"
SHEET_ID = "1Uapf1c4wDZ4hGfa1bqSbRjF45VodFv2-jtzgLL4VDq0"
CREDENTIALS_FILE = "credentials.json"

def get_db_connection():
    return sqlite3.connect(DB_PATH)

def get_sheets_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
    return gspread.authorize(creds)

def export_table_to_sheet(cursor, client, spreadsheet, table_name):
    print(f"Exporting table: {table_name}...")
    
    # Fetch data from SQLite
    cursor.execute(f'SELECT * FROM "{table_name}"')
    rows = cursor.fetchall()
    
    # Fetch headers
    cursor.execute(f'PRAGMA table_info("{table_name}")')
    headers = [col[1] for col in cursor.fetchall()]
    
    # Prepare data (headers + rows)
    # Convert all values to strings for consistency in Google Sheets
    data_to_write = [headers]
    for row in rows:
        data_to_write.append([str(val) if val is not None else "" for val in row])
    
    try:
        # Check if worksheet exists, if not create it
        try:
            worksheet = spreadsheet.worksheet(table_name)
            print(f"  Updating existing worksheet: {table_name}")
            worksheet.clear()
        except gspread.exceptions.WorksheetNotFound:
            print(f"  Creating new worksheet: {table_name}")
            worksheet = spreadsheet.add_worksheet(title=table_name, rows="100", cols="20")
        
        # Write data
        if data_to_write:
            # Resize worksheet to fit data
            worksheet.resize(rows=len(data_to_write), cols=len(headers))
            worksheet.update('A1', data_to_write)
            print(f"  Successfully exported {len(rows)} rows and {len(headers)} columns.")
        
        # Avoid hitting API rate limits
        time.sleep(1)
        
    except Exception as e:
        print(f"  Error exporting {table_name}: {e}")

def main():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [t[0] for t in cursor.fetchall()]
        
        client = get_sheets_client()
        spreadsheet = client.open_by_key(SHEET_ID)
        
        for table in tables:
            if table == 'sqlite_sequence': # Skip internal SQLite table
                continue
            export_table_to_sheet(cursor, client, spreadsheet, table)
            
        conn.close()
        print("\nDatabase export completed successfully!")
        
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
