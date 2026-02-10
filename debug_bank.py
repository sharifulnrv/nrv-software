import sqlite3
from datetime import datetime

def parse_date(date_str):
    for fmt in ('%Y-%m-%d', '%d-%m-%Y'):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            pass
    return datetime.min

conn = sqlite3.connect('instance/nexus.db')
cursor = conn.cursor()

# Get all transactions
cursor.execute('SELECT id, date, credit, debit, balance, bank_id FROM bank_transaction')
rows = cursor.fetchall()
conn.close()

print(f"Total entries: {len(rows)}")

# Group by bank
banks = {}
for r in rows:
    bid = r[5]
    if bid not in banks: banks[bid] = []
    banks[bid].append(r)

for bid, txs in banks.items():
    print(f"\n--- Bank {bid} ---")
    # Sort
    # row index: 0=id, 1=date
    txs.sort(key=lambda x: (parse_date(x[1]), x[0]))
    
    running = 0.0
    for tx in txs:
        # 2=credit, 3=debit
        credit = tx[2]
        debit = tx[3]
        running += (credit - debit)
        
        # print first few and last few
        print(f"ID: {tx[0]} Date: {tx[1]} C:{credit} D:{debit} Bal:{tx[4]} CalcRunning:{running}")

