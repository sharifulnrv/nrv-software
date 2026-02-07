from app import app
from models import BankTransaction

def check_dates():
    with app.app_context():
        # Get first 20 transactions
        txs = BankTransaction.query.limit(20).all()
        print(f"Found {len(txs)} transactions.")
        for tx in txs:
            print(f"ID: {tx.id}, Date: '{tx.date}'")

if __name__ == "__main__":
    check_dates()
