from app import create_app, db
from models import Director, Customer, Transaction, PettyCash
import pandas as pd
import os
import logic

# FORCE Test Excel File
logic.EXCEL_FILE = 'test_nexus_river_view.xlsx'
from logic import sync_to_excel

def verify():
    # db_path = os.path.join('instance', 'nexus.db')
    # Use test DB only
            
    test_db_path = os.path.join('instance', 'test_nexus.db')
    if os.path.exists(test_db_path):
        try:
            os.remove(test_db_path)
            print("Deleted old test_nexus.db")
        except:
            pass

    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test_nexus.db'
    with app.app_context():
        print("1. Creating Test Database...")
        db.create_all()
        
        print("2. Clearing old data for test...")
        Customer.query.delete()
        Director.query.delete()
        Transaction.query.delete()
        PettyCash.query.delete()
        db.session.commit()
        
        print("3. Adding Test Director with Financials...")
        d1 = Director(
            name="Test Director", 
            phone="1234567890",
            bank_name="Test Bank",
            total_share=10,
            per_share_value=5000,
            fair_cost=1000,
            land_value_extra_share=2000,
            total_paid=20000,
            payment_history="Self: 5000\nBank: 15000"
        )
        db.session.add(d1)
        db.session.commit()
        
        print(f"   Director ID: {d1.id}")
        
        print("4. Adding Test Customer...")
        c1 = Customer(
            director_id=d1.id,
            customer_id="CUST-001",
            name="Test Customer",
            phone="0987654321",
            plot_no="A-101",
            total_price=50000,
            down_payment=10000,
            monthly_installment=5000,
            total_paid=10000,
            due_amount=40000
        )
        db.session.add(c1)
        db.session.commit()
        
        # Add Transaction
        print("4.5 Adding Transaction...")
        tx = Transaction(
            date="2026-02-03",
            amount=5000,
            installment_type="Down Payment",
            bank_name="Test Bank Transaction",
            customer=c1
        )
        c1.total_paid += 5000
        c1.due_amount = c1.total_price - c1.total_paid
        db.session.add(tx)
        db.session.commit()

        db.session.add(tx)
        db.session.commit()
        
        # Add Petty Cash
        print("4.6 Adding Petty Cash...")
        pc1 = PettyCash(date="2026-02-03", description="Office Income", category="Income", type="Income", amount=1000, images="test_img.png")
        pc2 = PettyCash(date="2026-02-03", description="Tea", category="Food", type="Expense", amount=200, images="test.pdf")
        db.session.add(pc1)
        db.session.add(pc2)
        db.session.commit()

        print("5. Syncing to Excel...")
        sync_to_excel()
        
        print("6. Verifying Excel File...")
        test_excel = 'test_nexus_river_view.xlsx'
        if os.path.exists(test_excel):
            df = pd.read_excel(test_excel, engine='openpyxl', sheet_name='Master_Data')
            df_dir = pd.read_excel(test_excel, engine='openpyxl', sheet_name='Directors_Summary')
            
            print("   Master Rows found:", len(df))
            print("   Director Rows found:", len(df_dir))
            
            if len(df) == 1 and df.iloc[0]['Customer Name'] == 'Test Customer':
                print("   SUCCESS: Customer Data matched!")
                if df.iloc[0]['Total Paid'] == 15000:
                     print("   SUCCESS: Transaction updated Total Paid correctly!")
                else:
                     print(f"   FAILURE: Total Paid mismatch. Expected 15000, got {df.iloc[0]['Total Paid']}")
            else:
                print("   FAILURE: Customer Data mismatch.")
                
            # Verify new columns
            print("   Verifying Image-based Column Mapping...")
            expected_columns = [
                'SL NO.', 'Share name', 'Total share', 'Per share value', 'Fair Cost', 
                'Total share value', 'Land value of Extra share', 'Total share+ Extra share Value', 
                'Total Paid Until date', 'Date & Deposit', 'B.Name', 'DUE'
            ]
            
            columns_matched = True
            for col in expected_columns:
                if col not in df_dir.columns:
                    print(f"   FAILURE: Missing Column '{col}'")
                    columns_matched = False
            
            if columns_matched:
                 if len(df_dir) == 1 and df_dir.iloc[0]['Share name'] == 'Test Director':
                     print("   SUCCESS: All Director Columns & Data Type Found!")
                 else:
                     print("   FAILURE: Director Data value mismatch.")
            else:
                print("   FAILURE: Column schema mismatch.")
                
            # Verify Petty Cash
            df_petty = pd.read_excel(test_excel, engine='openpyxl', sheet_name='Petty_Cash')
            print("   Petty Cash Rows found:", len(df_petty))
            if len(df_petty) == 2:
                print("   SUCCESS: Petty Cash Rows matched!")
            else:
                print("   FAILURE: Petty Cash Rows mismatch.")

            # Verify Transactions
            df_tx = pd.read_excel(test_excel, engine='openpyxl', sheet_name='Transactions')
            print("   Transaction Rows found:", len(df_tx))
            if len(df_tx) == 1: 
                print("   SUCCESS: Transaction Rows matched!")
            else:
                 print("   FAILURE: Transaction Rows mismatch.")
                
        else:
            print(f"   FAILURE: File {test_excel} not created.")

if __name__ == "__main__":
    verify()
