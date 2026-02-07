from app import app
from models import Transaction

def debug_issue():
    print("--- Checking Route Map ---")
    with app.app_context():
        rules = [str(p) for p in app.url_map.iter_rules()]
        found = any('/transaction/edit/<int:id>' in r for r in rules)
        print(f"Route '/transaction/edit/<int:id>' registered? {found}")
        
    print("\n--- Checking Transaction 5 ---")
    with app.app_context():
        tx = Transaction.query.get(5)
        if tx:
            print(f"Transaction 5 exists: ID={tx.id}, Amount={tx.amount}, Customer={tx.customer_id}")
        else:
            print("Transaction 5 NOT FOUND.")

if __name__ == "__main__":
    debug_issue()
