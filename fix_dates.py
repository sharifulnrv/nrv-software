import sqlite3
from datetime import datetime

# Connect to DB
conn = sqlite3.connect('instance/nexus.db')
cursor = conn.cursor()

def parse_date(date_str):
    for fmt in ('%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y'):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            pass
    return None

print("Scanning transactions...")
cursor.execute('SELECT id, date, bank_id FROM bank_transaction')
rows = cursor.fetchall()

updates = 0
bank_ids = set()

for row in rows:
    tx_id, date_str, bank_id = row
    dt = parse_date(date_str)
    
    if dt:
        iso_date = dt.strftime('%Y-%m-%d')
        if iso_date != date_str:
            print(f"Fixing ID {tx_id}: {date_str} -> {iso_date}")
            cursor.execute('UPDATE bank_transaction SET date = ? WHERE id = ?', (iso_date, tx_id))
            updates += 1
            bank_ids.add(bank_id)
    else:
        print(f"WARNING: Could not parse date for ID {tx_id}: {date_str}")

conn.commit()
print(f"Normalized {updates} dates.")

# Now Recompute Balances for affected banks
print("Recomputing balances...")

for bid in bank_ids:
    print(f"Processing Bank {bid}...")
    cursor.execute('SELECT id, date, credit, debit FROM bank_transaction WHERE bank_id = ?', (bid,))
    txs = cursor.fetchall()
    
    # Sort by ISO Date (ASC), then ID (ASC)
    # Since we normalized dates, string sort works for date
    txs.sort(key=lambda x: (x[1], x[0]))
    
    running_bal = 0.0
    for tx in txs:
        tid, _, cred, deb = tx
        running_bal += (cred - deb)
        cursor.execute('UPDATE bank_transaction SET balance = ? WHERE id = ?', (running_bal, tid))

conn.commit()
conn.close()
print("Done!")
