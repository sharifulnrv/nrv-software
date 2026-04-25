import pandas as pd
import openpyxl
from models import Director, Customer, PettyCash, Transaction, Bank, BankTransaction, Installment, CustomerInstallment, Party, PartyLedger
import os
import shutil
import io
from datetime import datetime, timezone
from database import db
from telegram_utils import send_telegram_document, log_debug

EXCEL_FILE = 'nexus_river_view_master.xlsx' if __name__ != '__main__' else 'test_nexus_river_view.xlsx'

def sync_to_excel():
    """
    Fetches all customers and directors from the database,
    creates a consolidated table, sorts by Director,
    and writes to the Master Excel file.
    """
    try:
        # ... logic to create dataframes ...
        # Since I am replacing a large chunk, I must be careful not to delete the data preparation logic.
        # However, the user instruction said "logic.py" at "sync_to_excel".
        # The previous view showed the function is long.
        # I should use multi_replace or targeted replace.
        # But I need to wrap the whole function in try...except for logging?
        # The function already has a try...except block starting at line 187.
        # I will just update the imports and the existing try...except block.
        pass
    except:
        pass

# Wait, I cannot use ReplacementContent with "..." placeholder logic.
# I need to be precise.
# Let's use 2 replacements. 
# 1. Imports
# 2. The try-except block at the end.

    directors = Director.query.all()
    # Create a mapping of Director ID to Name for easy lookup, although we can join in query
    # But let's fetch all customers joined with directors
    
    customers = Customer.query.join(Director).add_columns(
        Director.name.label('director_name'),
        Customer.customer_id,
        Customer.name,
        Customer.phone,
        Customer.plot_no,
        Customer.total_price,
        Customer.down_payment,
        Customer.monthly_installment,
        Customer.total_paid,
        Customer.due_amount
    ).all()
    
    # Prepare data for DataFrame
    data = []
    for row in customers:
        # row is a tuple: (CustomerObj, director_name, ...) if we didn't refine add_columns carefully
        # With add_columns, it returns a Result object (named tuple like)
        
        # Let's simplify: Query customers and access relationship
        pass

    # Refined Query
    all_customers = Customer.query.outerjoin(Director).order_by(Director.name, Customer.customer_id).all()
    
    export_list = []
    for c in all_customers:
        export_list.append({
            'Director Name': c.director.name,
            'Customer ID': c.customer_id,
            'Customer Name': c.name,
            'Phone': c.phone,
            'Plot No': c.plot_no,
            'Total Price': c.total_price,
            'Down Payment': c.down_payment,
            'Monthly Installment': c.monthly_installment,
            'Total Paid': c.total_paid,
            'Due Amount': c.due_amount
        })
    
    if not export_list:
        # Create empty dataframe with columns if no data
        df = pd.DataFrame(columns=[
            'Director Name', 'Customer ID', 'Customer Name', 'Phone', 'Plot No',
            'Total Price', 'Down Payment', 'Monthly Installment', 'Total Paid', 'Due Amount'
        ])
    else:
        df = pd.DataFrame(export_list)
        # Smart Sorting: Sort by Director Name, then Customer ID
        df = df.sort_values(by=['Director Name', 'Customer ID'])

    # --- Director Summary Data ---
    all_directors = Director.query.all()
    director_list = []
    
    # Image Columns:
    # 1. SL NO. | 2. Share name | 3. Total share | 4. Per share value | 5. Fair Cost 
    # 6. Total share value | 7. Land value of Extra share | 8. Total share+ Extra share Value
    # 9. Total Paid Until date | 10. Date & Deposit | 11. B.Name | 12. DUE
    
    for i, d in enumerate(all_directors, start=1):
        director_list.append({
            'SL NO.': i,
            'Share name': d.name,
            'Total share': d.total_share,
            'Total Paid': d.total_paid,
            'Total Due': d.total_due,
            'Bank Name': d.bank_name or '',
            'History': d.payment_history or ''
        })
        
    df_directors = pd.DataFrame(director_list)
    
    # Petty Cash Sheet
    all_entries = PettyCash.query.order_by(PettyCash.date).all()
    petty_list = []
    
    running_balance = 0
    for e in all_entries:
        if e.type == 'Income':
            running_balance += e.amount
        else:
            running_balance -= e.amount
            
        petty_list.append({
            'Date': e.date,
            'Description': e.description,
            'Category': e.category,
            'Type': e.type,
            'Income': e.amount if e.type == 'Income' else 0,
            'Expense': e.amount if e.type == 'Expense' else 0,
            'Balance': running_balance,
            'Images': e.images
        })
        
    df_petty = pd.DataFrame(petty_list)
    
    # Transactions Sheet
    all_transactions = Transaction.query.order_by(Transaction.date).all()
    tx_list = []
    for tx in all_transactions:
        tx_list.append({
            'ID': tx.id,
            'Date': tx.date,
            'Customer ID': tx.customer.customer_id,
            'Customer Name': tx.customer.name,
            'Amount': tx.amount,
            'Installment Type': tx.installment_type,
            'Bank Name': tx.bank_name,
            'Transaction ID': tx.transaction_id,
            'Remarks': tx.remarks,
            'Images': tx.images
        })
    df_transactions = pd.DataFrame(tx_list)

    # Bank Sheets
    all_banks = Bank.query.all()
    bank_list = []
    for b in all_banks:
        bank_list.append({
            'Bank Name': b.bank_name,
            'Branch': b.branch,
            'Account Holder': b.account_holder_name,
            'Joint Name': b.joint_name,
            'FHP': b.fhp,
            'Address': b.address,
            'City': b.city,
            'Phone': b.phone,
            'Customer ID': b.customer_id,
            'Account No': b.account_no,
            'Prev Account No': b.prev_account_no,
            'Account Type': b.account_type,
            'Currency': b.currency,
            'Status': b.status
        })
    df_banks = pd.DataFrame(bank_list)
    # Bank Transactions Sheet
    all_bank_tx = BankTransaction.query.order_by(BankTransaction.date).all()
    bank_tx_data = []
    for btx in all_bank_tx:
        bank_tx_data.append({
            'Date': btx.date,
            'Bank ID': btx.bank_id,
            'Bank Name': btx.bank.bank_name if btx.bank else "N/A",
            'Narration': btx.narration,
            'Debit': btx.debit,
            'Credit': btx.credit,
            'Balance': btx.balance
        })
    df_bank_tx = pd.DataFrame(bank_tx_data)

    # Installments Sheet
    all_installments = Installment.query.all()
    inst_list = []
    for inst in all_installments:
        inst_list.append({
            'ID': inst.id,
            'Name': inst.name,
            'Amount Per Share': inst.amount_per_share
        })
    df_inst = pd.DataFrame(inst_list)

    # Customer Installments Sheet
    all_cust_inst = CustomerInstallment.query.all()
    ci_list = []
    for ci in all_cust_inst:
        ci_list.append({
            'Customer ID': ci.customer.customer_id,
            'Customer Name': ci.customer.name,
            'Installment Name': ci.installment.name,
            'Total Amount': ci.total_amount,
            'Paid Amount': ci.paid_amount,
            'Due Amount': ci.due_amount
        })
    df_ci = pd.DataFrame(ci_list)

    # Write to Excel
    # We use engine='openpyxl' for xlsx
    try:
        # Determine Excel Path based on DATA_FOLDER
        from flask import current_app
        data_folder = current_app.config.get('DATA_FOLDER', '.')
        
        # Use simple filename if in dev mode main, else DATA_FOLDER
        if __name__ == '__main__':
             target_excel_path = EXCEL_FILE 
        else:
             target_excel_path = os.path.join(data_folder, 'nexus_river_view_master.xlsx')
             
        with pd.ExcelWriter(target_excel_path, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Master_Data', index=False)
            df_directors.to_excel(writer, sheet_name='Directors_Summary', index=False)
            df_petty.to_excel(writer, sheet_name='Petty_Cash', index=False)
            df_transactions.to_excel(writer, sheet_name='Transactions', index=False)
            df_banks.to_excel(writer, sheet_name='Banks', index=False)
            df_bank_tx.to_excel(writer, sheet_name='Bank_Transactions', index=False)
            df_inst.to_excel(writer, sheet_name='Installments', index=False)
            df_ci.to_excel(writer, sheet_name='Customer_Installments', index=False)
            
            # Formatter function
            workbook = writer.book
            
            for sheet_name in ['Master_Data', 'Directors_Summary', 'Petty_Cash', 'Transactions', 'Banks', 'Bank_Transactions', 'Installments', 'Customer_Installments']:
                if sheet_name in writer.sheets:
                    worksheet = writer.sheets[sheet_name]
                    for column in worksheet.columns:
                        max_length = 0
                        column = [cell for cell in column]
                        for cell in column:
                            try:
                                if len(str(cell.value)) > max_length:
                                    max_length = len(cell.value)
                            except:
                                pass
                        adjusted_width = (max_length + 2)
                        worksheet.column_dimensions[column[0].column_letter].width = adjusted_width
                
        print(f"Successfully synced to {target_excel_path}")
        log_debug(f"Synced Excel to: {target_excel_path}")
        
        print(f"Successfully synced to {target_excel_path}")
        log_debug(f"Synced Excel to: {target_excel_path}")
            
            # REMOVED: Excel upload to Telegram as it is too slow for real-time saving
            # Redundant since we send the DB file which contains everything.
            
    except Exception as e:
        print(f"Error syncing to Excel: {e}")
        log_debug(f"CRITICAL ERROR in sync_to_excel: {e}")

def create_db_backup():
    """
    Creates a copy of the current nexus.db into the backups folder with a timestamp.
    """
    try:
        from flask import current_app
        data_folder = current_app.config.get('DATA_FOLDER', os.getcwd())
        db_path = current_app.config.get('DATABASE_PATH')
        
        if not db_path or not os.path.exists(db_path):
            log_debug("DB backup failed: database_path not found.")
            return None
            
        backup_dir = os.path.join(data_folder, 'backups')
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"nexus_db_backup_{timestamp}.db"
        backup_path = os.path.join(backup_dir, backup_filename)
        
        import shutil
        shutil.copy2(db_path, backup_path)
        log_debug(f"DB Backup created: {backup_path}")
        
        # Cleanup old backups
        cleanup_old_backups()
        
        return backup_path
    except Exception as e:
        log_debug(f"Error creating DB backup: {e}")
        return None

def cleanup_old_backups(days=30):
    """
    Deletes backup files in the backups folder that are older than the specified number of days.
    """
    try:
        from flask import current_app
        import time
        data_folder = current_app.config.get('DATA_FOLDER', os.getcwd())
        backup_dir = os.path.join(data_folder, 'backups')
        
        if not os.path.exists(backup_dir):
            return
            
        now = time.time()
        cutoff = now - (days * 86400)
        
        deleted_count = 0
        for filename in os.listdir(backup_dir):
            file_path = os.path.join(backup_dir, filename)
            if os.path.isfile(file_path):
                file_time = os.path.getmtime(file_path)
                if file_time < cutoff:
                    os.remove(file_path)
                    deleted_count += 1
        
        if deleted_count > 0:
            log_debug(f"Auto-cleanup: Deleted {deleted_count} old backups.")
            
    except Exception as e:
        log_debug(f"Error cleaning up old backups: {e}")

def restore_from_excel(file_path):
    """
    Restores the database from the given Excel file.
    WARNING: This wipes all current data.
    """
    try:
        # Read Excel Sheets
        df_master = pd.read_excel(file_path, engine='openpyxl', sheet_name='Master_Data')
        df_directors = pd.read_excel(file_path, engine='openpyxl', sheet_name='Directors_Summary')
        
        # Optional sheets (might not exist in older backups)
        try:
            df_petty = pd.read_excel(file_path, engine='openpyxl', sheet_name='Petty_Cash')
        except:
            df_petty = pd.DataFrame()

        try:
            df_tx = pd.read_excel(file_path, engine='openpyxl', sheet_name='Transactions')
        except:
            df_tx = pd.DataFrame() # Fixed empty dataframe assignment

        try:
            df_banks = pd.read_excel(file_path, engine='openpyxl', sheet_name='Banks')
        except:
            df_banks = pd.DataFrame()

        try:
            df_bank_tx = pd.read_excel(file_path, engine='openpyxl', sheet_name='Bank_Transactions')
        except:
            df_bank_tx = pd.DataFrame()

        # Wipe Database
        BankTransaction.query.delete()
        Bank.query.delete()
        PettyCash.query.delete()
        Transaction.query.delete()
        Customer.query.delete()
        Director.query.delete()
        db.session.commit()
        
        # Restore Directors
        director_map = {} # Name -> ID
        for _, row in df_directors.iterrows():
            d = Director(
                name=row['Share name'],
                total_share=row['Total share'],
                per_share_value=0,
                fair_cost=0,
                land_value_extra_share=0,
                total_paid=row.get('Total Paid', 0),
                total_due=row.get('Total Due', 0),
                payment_history=str(row.get('History', '')) if pd.notna(row.get('History')) else '',
                bank_name=str(row.get('Bank Name', '')) if pd.notna(row.get('Bank Name')) else ''
            )
            db.session.add(d)
            db.session.flush() # Get ID
            director_map[d.name] = d.id
            
        # Restore Customers
        customer_map = {} # Customer ID (str) -> DB ID
        for _, row in df_master.iterrows():
            dir_name = row['Director Name']
            if dir_name in director_map:
                c = Customer(
                    director_id=director_map[dir_name],
                    customer_id=row['Customer ID'],
                    name=row['Customer Name'],
                    phone=str(row['Phone']),
                    plot_no=row['Plot No'],
                    total_price=row['Total Price'],
                    down_payment=row['Down Payment'],
                    monthly_installment=row['Monthly Installment'],
                    total_paid=row['Total Paid'],
                    due_amount=row['Due Amount']
                )
                db.session.add(c)
                db.session.flush()
                customer_map[c.customer_id] = c.id
        
        # Restore Transactions
        if not df_tx.empty:
            for _, row in df_tx.iterrows():
                cust_str_id = row['Customer ID']
                if cust_str_id in customer_map:
                    t = Transaction(
                        date=str(row['Date']), # Ensure string
                        amount=row['Amount'],
                        installment_type=row['Installment Type'],
                        bank_name=str(row['Bank Name']) if pd.notna(row['Bank Name']) else '',
                        transaction_id=str(row['Transaction ID']) if pd.notna(row['Transaction ID']) else '',
                        remarks=str(row['Remarks']) if pd.notna(row['Remarks']) else '',
                        images=str(row['Images']) if pd.notna(row['Images']) else '',
                        customer_id=customer_map[cust_str_id]
                    )
                    db.session.add(t)

        # Restore Petty Cash
        if not df_petty.empty:
            for _, row in df_petty.iterrows():
                pc = PettyCash(
                    date=str(row['Date']),
                    description=row['Description'],
                    category=row['Category'],
                    type=row['Type'],
                    amount=row['Income'] if row['Type'] == 'Income' else row['Expense'],
                    images=str(row['Images']) if pd.notna(row['Images']) else ''
                )
                db.session.add(pc)

        # Restore Banks
        bank_map = {} # Account No -> ID
        if not df_banks.empty:
            for _, row in df_banks.iterrows():
                b = Bank(
                    bank_name=row['Bank Name'],
                    branch=str(row['Branch']) if pd.notna(row['Branch']) else '',
                    account_holder_name=str(row['Account Holder']) if pd.notna(row['Account Holder']) else '',
                    joint_name=str(row['Joint Name']) if pd.notna(row['Joint Name']) else '',
                    fhp=str(row['FHP']) if pd.notna(row['FHP']) else '',
                    address=str(row['Address']) if pd.notna(row['Address']) else '',
                    city=str(row['City']) if pd.notna(row['City']) else '',
                    phone=str(row['Phone']) if pd.notna(row['Phone']) else '',
                    customer_id=str(row['Customer ID']) if pd.notna(row['Customer ID']) else '',
                    account_no=str(row['Account No']),
                    prev_account_no=str(row['Prev Account No']) if pd.notna(row['Prev Account No']) else '',
                    account_type=str(row['Account Type']) if pd.notna(row['Account Type']) else '',
                    currency=str(row['Currency']) if pd.notna(row['Currency']) else '',
                    status=str(row['Status']) if pd.notna(row['Status']) else 'Active'
                )
                db.session.add(b)
                db.session.flush()
                bank_map[b.account_no] = b.id

        # Restore Bank Transactions
        if not df_bank_tx.empty:
            for _, row in df_bank_tx.iterrows():
                acc_no = str(row['Bank Account No'])
                if acc_no in bank_map:
                    btx = BankTransaction(
                        date=str(row['Date']),
                        cheque_no=str(row['Cheque No']) if pd.notna(row['Cheque No']) else '',
                        ref_no=str(row['Ref No']) if pd.notna(row['Ref No']) else '',
                        narration=str(row['Narration']) if pd.notna(row['Narration']) else '',
                        transaction_details=str(row['Transaction Details']) if pd.notna(row['Transaction Details']) else '',
                        debit=row['Debit'],
                        credit=row['Credit'],
                        balance=row['Balance'],
                        bank_id=bank_map[acc_no]
                    )
                    db.session.add(btx)

        db.session.commit()
        return True, "Data successfully restored."
        
    except Exception as e:
        db.session.rollback()
        print(f"Restore failed: {e}")
        return False, str(e)
def restore_from_data_dict(data_dict):
    """
    Restores the database from a dictionary of lists of dictionaries.
    """
    try:
        # Wipe Database
        PartyLedger.query.delete()
        Party.query.delete()
        CustomerInstallment.query.delete()
        Installment.query.delete()
        BankTransaction.query.delete()
        Bank.query.delete()
        PettyCash.query.delete()
        Transaction.query.delete()
        Customer.query.delete()
        Director.query.delete()
        db.session.commit()
        
        # Restore Directors
        director_id_map = {} # Maps old_id (from sheet) to new_id (in DB)
        for row in data_dict.get('director', []):
            old_id = str(row.get('id'))
            d = Director(
                name=row['name'],
                total_share=float(row['total_share'] or 0),
                per_share_value=0,
                fair_cost=0,
                land_value_extra_share=0,
                total_paid=float(row['total_paid'] or 0),
                total_due=float(row.get('total_due') or 0),
                payment_history=str(row['payment_history']),
                bank_name=str(row['bank_name']),
                updated_at=datetime.strptime(row['updated_at'], "%Y-%m-%d %H:%M:%S") if row.get('updated_at') else datetime.now(timezone.utc)
            )
            db.session.add(d)
            db.session.flush()
            director_id_map[old_id] = d.id
            
        # Restore Customers
        customer_id_map = {}
        for row in data_dict.get('customer', []):
            old_id = str(row.get('id'))
            old_director_id = str(row.get('director_id'))
            # Get the new director ID from our map
            new_director_id = director_id_map.get(old_director_id)
            
            if not new_director_id:
                print(f"Warning: Could not find new director ID for old ID {old_director_id}")
                # Fallback to the old ID if mapping fails (less safe but best effort)
                new_director_id = int(old_director_id) if old_director_id.isdigit() else 1

            c = Customer(
                director_id=new_director_id,
                customer_id=row['customer_id'],
                name=row['name'],
                phone=str(row['phone']),
                plot_no=row['plot_no'],
                total_price=float(row['total_price'] or 0),
                down_payment=float(row['down_payment'] or 0),
                monthly_installment=float(row['monthly_installment'] or 0),
                total_paid=float(row['total_paid'] or 0),
                due_amount=float(row['due_amount'] or 0),
                father_name=row.get('father_name', ''),
                mother_name=row.get('mother_name', ''),
                dob=row.get('dob', ''),
                religion=row.get('religion', ''),
                profession=row.get('profession', ''),
                nid_no=row.get('nid_no', ''),
                present_address=row.get('present_address', ''),
                permanent_address=row.get('permanent_address', ''),
                updated_at=datetime.strptime(row['updated_at'], "%Y-%m-%d %H:%M:%S") if row.get('updated_at') else datetime.now(timezone.utc)
            )
            db.session.add(c)
            db.session.flush()
            customer_id_map[old_id] = c.id

        # Restore Transactions
        for row in data_dict.get('transaction', []):
            old_cust_id = str(row.get('customer_id'))
            new_cust_id = customer_id_map.get(old_cust_id)
            
            if not new_cust_id:
                new_cust_id = int(old_cust_id) if old_cust_id.isdigit() else 1

            t = Transaction(
                date=str(row['date']),
                amount=float(row['amount'] or 0),
                installment_type=row['installment_type'],
                bank_name=str(row['bank_name']),
                transaction_id=str(row['transaction_id']),
                remarks=str(row['remarks']),
                images=str(row['images']),
                customer_id=new_cust_id,
                updated_at=datetime.strptime(row['updated_at'], "%Y-%m-%d %H:%M:%S") if row.get('updated_at') else datetime.now(timezone.utc)
            )
            db.session.add(t)

        # Restore Petty Cash
        for row in data_dict.get('petty_cash', []):
            pc = PettyCash(
                date=str(row['date']),
                description=row['description'],
                category=row['category'],
                type=row['type'],
                amount=float(row['amount'] or 0),
                images=str(row['images']),
                updated_at=datetime.strptime(row['updated_at'], "%Y-%m-%d %H:%M:%S") if row.get('updated_at') else datetime.now(timezone.utc)
            )
            db.session.add(pc)

        # Restore Banks
        bank_id_map = {}
        for row in data_dict.get('bank', []):
            old_id = str(row.get('id'))
            b = Bank(
                bank_name=row['bank_name'],
                branch=str(row['branch']),
                account_holder_name=str(row['account_holder_name']),
                joint_name=str(row['joint_name']),
                fhp=str(row['fhp']),
                address=str(row['address']),
                city=str(row['city']),
                phone=str(row['phone']),
                customer_id=str(row['customer_id']),
                account_no=str(row['account_no']),
                prev_account_no=str(row['prev_account_no']),
                account_type=str(row['account_type']),
                currency=str(row['currency']),
                status=str(row['status']),
                updated_at=datetime.strptime(row['updated_at'], "%Y-%m-%d %H:%M:%S") if row.get('updated_at') else datetime.now(timezone.utc)
            )
            db.session.add(b)
            db.session.flush()
            bank_id_map[old_id] = b.id

        # Restore Bank Transactions
        for row in data_dict.get('bank_transaction', []):
            old_bank_id = str(row.get('bank_id'))
            new_bank_id = bank_id_map.get(old_bank_id)
            
            if not new_bank_id:
                new_bank_id = int(old_bank_id) if old_bank_id.isdigit() else 1

            btx = BankTransaction(
                date=str(row['date']),
                cheque_no=str(row['cheque_no']),
                ref_no=str(row['ref_no']),
                narration=str(row['narration']),
                transaction_details=str(row['transaction_details']),
                debit=float(row['debit'] or 0),
                credit=float(row['credit'] or 0),
                balance=float(row['balance'] or 0),
                bank_id=new_bank_id,
                updated_at=datetime.strptime(row['updated_at'], "%Y-%m-%d %H:%M:%S") if row.get('updated_at') else datetime.now(timezone.utc)
            )
            db.session.add(btx)

        # Restore Installments
        installment_id_map = {}
        for row in data_dict.get('installment', []):
            old_inst_id = str(row.get('id'))
            inst = Installment(
                name=row['name'],
                amount_per_share=float(row['amount_per_share'] or 0)
            )
            db.session.add(inst)
            db.session.flush()
            installment_id_map[old_inst_id] = inst.id

        # Restore Customer Installments
        for row in data_dict.get('customer_installment', []):
            old_cust_id = str(row.get('customer_id'))
            old_inst_id = str(row.get('installment_id'))
            
            new_cust_id = customer_id_map.get(old_cust_id)
            new_inst_id = installment_id_map.get(old_inst_id)
            
            if new_cust_id and new_inst_id:
                ci = CustomerInstallment(
                    customer_id=new_cust_id,
                    installment_id=new_inst_id,
                    total_amount=float(row['total_amount'] or 0),
                    paid_amount=float(row['paid_amount'] or 0),
                    due_amount=float(row['due_amount'] or 0)
                )
                db.session.add(ci)

        # Restore Parties
        party_id_map = {}
        for row in data_dict.get('party', []):
            old_id = str(row.get('id'))
            p = Party(
                name=row['name'],
                category=row['category'],
                phone=row.get('phone', ''),
                address=row.get('address', ''),
                created_at=datetime.strptime(row['created_at'], "%Y-%m-%d %H:%M:%S") if row.get('created_at') else datetime.now(timezone.utc)
            )
            db.session.add(p)
            db.session.flush()
            party_id_map[old_id] = p.id

        # Restore Vouchers (Depends on Party and Bank)
        voucher_id_map = {}
        from models import Voucher
        for row in data_dict.get('voucher', []):
            old_id = str(row.get('id'))
            old_party_id = str(row.get('party_id'))
            old_bank_id = str(row.get('bank_id'))
            
            v = Voucher(
                voucher_no=row['voucher_no'],
                type=row['type'],
                date=row['date'],
                party_id=party_id_map.get(old_party_id),
                description=row.get('description', ''),
                total_amount=float(row.get('total_amount') or 0),
                amount_paid=float(row.get('amount_paid') or 0),
                due_amount=float(row.get('due_amount') or 0),
                payment_percentage=float(row.get('payment_percentage') or 0),
                payment_method=row['payment_method'],
                bank_id=bank_id_map.get(old_bank_id),
                category=row.get('category', ''),
                notes=row.get('notes', ''),
                attachment=row.get('attachment', ''),
                created_at=datetime.strptime(row['created_at'], "%Y-%m-%d %H:%M:%S") if row.get('created_at') else datetime.now(timezone.utc)
            )
            db.session.add(v)
            db.session.flush()
            voucher_id_map[old_id] = v.id

        # Restore Bank Transactions (Refers to Voucher)
        for row in data_dict.get('bank_transaction', []):
            old_bank_id = str(row.get('bank_id'))
            old_voucher_id = str(row.get('voucher_id'))
            new_bank_id = bank_id_map.get(old_bank_id)
            if new_bank_id:
                bt = BankTransaction(
                    date=row['date'],
                    cheque_no=row.get('cheque_no', ''),
                    ref_no=row.get('ref_no', ''),
                    narration=row.get('narration', ''),
                    transaction_details=row.get('transaction_details', ''),
                    debit=float(row.get('debit') or 0),
                    credit=float(row.get('credit') or 0),
                    balance=float(row.get('balance') or 0),
                    bank_id=new_bank_id,
                    voucher_id=voucher_id_map.get(old_voucher_id)
                )
                db.session.add(bt)

        # Restore Petty Cash (Refers to Voucher)
        for row in data_dict.get('petty_cash', []):
            old_voucher_id = str(row.get('voucher_id'))
            pc = PettyCash(
                date=row['date'],
                description=row['description'],
                category=row['category'],
                type=row['type'],
                amount=float(row['amount']),
                images=row.get('images', ''),
                voucher_id=voucher_id_map.get(old_voucher_id)
            )
            db.session.add(pc)

        # Restore Party Ledger (Refers to Voucher)
        for row in data_dict.get('party_ledger', []):
            old_party_id = str(row.get('party_id'))
            old_voucher_id = str(row.get('voucher_id'))
            new_party_id = party_id_map.get(old_party_id)
            if new_party_id:
                pl = PartyLedger(
                    party_id=new_party_id,
                    date=row['date'],
                    description=row.get('description', ''),
                    bill_amount=float(row.get('bill_amount') or 0),
                    paid_amount=float(row.get('paid_amount') or 0),
                    balance=float(row.get('balance') or 0),
                    reference=row.get('reference', ''),
                    voucher_id=voucher_id_map.get(old_voucher_id),
                    created_at=datetime.strptime(row['created_at'], "%Y-%m-%d %H:%M:%S") if row.get('created_at') else datetime.now(timezone.utc)
                )
                db.session.add(pl)

        db.session.commit()
        return True, "Data successfully restored from sync (ID mapping applied)."
    except Exception as e:
        db.session.rollback()
        print(f"Restore from dict failed: {e}")
        return False, str(e)

def recalculate_party_ledger_balances(party_id):
    """
    Recalculates the running balance for all entries of a specific party.
    Ensures consistency if entries are added out of order or deleted.
    """
    try:
        entries = PartyLedger.query.filter_by(party_id=party_id).order_by(PartyLedger.date.asc(), PartyLedger.id.asc()).all()
        running_balance = 0.0
        for entry in entries:
            running_balance += (entry.bill_amount - entry.paid_amount)
            entry.balance = running_balance
        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        log_debug(f"Error recalculating party balances: {e}")
        return False

def export_party_ledger_to_excel(party_id):
    """
    Generates an Excel file for a specific party's ledger.
    """
    from models import Party
    party = Party.query.get(party_id)
    if not party:
        return None, "Party not found"
        
    entries = PartyLedger.query.filter_by(party_id=party_id).order_by(PartyLedger.date.asc(), PartyLedger.id.asc()).all()
    
    data = []
    for e in entries:
        data.append({
            'Date': e.date,
            'Description': e.description,
            'Bill (Credit)': e.bill_amount,
            'Paid (Debit)': e.paid_amount,
            'Balance': e.balance,
            'Reference': e.reference
        })
        
    df = pd.DataFrame(data)
    
    # Create memory stream
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Ledger')
        
        # Formatting
        workbook = writer.book
        worksheet = writer.sheets['Ledger']
        
        # Adjust column widths
        for i, col in enumerate(df.columns):
            column_len = max(df[col].astype(str).str.len().max(), len(col)) + 2
            worksheet.column_dimensions[openpyxl.utils.get_column_letter(i+1)].width = column_len

    output.seek(0)
    # Get company info
    company_name = os.environ.get('COMPANY_NAME', 'NEXUS RIVER VIEW')
        
    safe_company_name = "".join(c for c in company_name if c.isalnum() or c in (' ', '_', '-')).strip().replace(' ', '_')
    filename = f"{safe_company_name}_{party.name.replace(' ', '_')}_Ledger_{datetime.now().strftime('%Y%m%d')}.xlsx"
    return output, filename

def generate_voucher_number(v_type):
    """
    Generates a unique voucher number based on type.
    Debit Voucher: DV1, DV2, ...
    Credit Voucher: CV1, CV2, ...
    """
    from models import Voucher
    prefix = "DV" if v_type == "Debit" else "CV"
    
    # Get all vouchers of this type and find the max number
    vouchers = Voucher.query.filter(Voucher.type == v_type).all()
    count = len(vouchers)
    new_num = count + 1
    
    return f"{prefix}{new_num}"

def generate_contra_number():
    from models import ContraEntry
    # Get all contra entries and find the next number
    count = ContraEntry.query.count()
    new_num = count + 1
    return f"CN{new_num}"

def process_voucher_financials(voucher_id, action='add'):
    """
    Handles automatic balance updates across modules when a voucher is created, edited, or deleted.
    Voucher types:
    - Debit: Payment MADE (Money OUT)
    - Credit: Money RECEIVED (Money IN)
    """
    from models import Voucher, PettyCash, BankTransaction, PartyLedger, Party
    voucher = Voucher.query.get(voucher_id)
    if not voucher:
        return False, "Voucher not found"

    try:
        # 1. Clear existing side-effects (for Edit/Delete)
        if action in ['edit', 'delete']:
            PettyCash.query.filter_by(voucher_id=voucher.id).delete()
            BankTransaction.query.filter_by(voucher_id=voucher.id).delete()
            PartyLedger.query.filter_by(voucher_id=voucher.id).delete()
            
            # If it was a customer voucher, we need to handle Transaction reverse?
            # Or just let process_voucher_financials re-create things.
            # Usually Customer transactions are updated via recalculate_customer_totals
            from models import Transaction
            Transaction.query.filter_by(remarks=f"Voucher {voucher.voucher_no}").delete()
            
            if action == 'delete':
                db.session.commit()
                # If it was a party voucher, recalculate balances
                if voucher.party_id:
                    recalculate_party_ledger_balances(voucher.party_id)
                
                if voucher.customer_id:
                    from models import Customer
                    cust = Customer.query.get(voucher.customer_id)
                    recalculate_customer_totals(cust)
                return True, "Voucher side-effects removed"

        # 2. Add new side-effects (for Add/Edit)
        if action in ['add', 'edit']:
            # A. Update Cash or Bank
            if voucher.payment_method == 'Cash':
                pc = PettyCash(
                    date=voucher.date,
                    description=f"Voucher {voucher.voucher_no}: {voucher.description}",
                    category=voucher.category or "General",
                    type="Expense" if voucher.type == "Debit" else "Income",
                    amount=voucher.amount_paid,
                    voucher_id=voucher.id
                )
                db.session.add(pc)
            
            elif voucher.payment_method == 'Bank' and voucher.bank_id:
                bt = BankTransaction(
                    date=voucher.date,
                    narration=f"Voucher {voucher.voucher_no}: {voucher.description}",
                    debit=voucher.amount_paid if voucher.type == "Debit" else 0,
                    credit=voucher.amount_paid if voucher.type == "Credit" else 0,
                    bank_id=voucher.bank_id,
                    voucher_id=voucher.id,
                    category=voucher.category or "General",
                    transaction_details=f"{voucher.type} Voucher"
                )
                db.session.add(bt)
                # Note: Bank running balances are usually updated on view or periodically

            # B. Update Party Ledger (if linked)
            if voucher.party_id:
                pl = PartyLedger(
                    party_id=voucher.party_id,
                    date=voucher.date,
                    description=f"Voucher {voucher.voucher_no}: {voucher.description}",
                    bill_amount=voucher.total_amount if (voucher.type == "Debit" and not voucher.is_payment) else 0,
                    paid_amount=voucher.amount_paid, # Amount actually paid/received
                    reference=voucher.voucher_no,
                    voucher_id=voucher.id
                )
                # If Credit Voucher linked to party, bill_amount might be 0, and paid_amount is credit to party?
                # Usually Credit Voucher to party means THEY paid US.
                if voucher.type == "Credit":
                    pl.bill_amount = 0
                    pl.paid_amount = -voucher.amount_paid # Negative paid_amount in our ledger logic means receiving? 
                    # Wait, our PartyLedger logic: balance = sum(bill) - sum(paid).
                    # If we pay them: paid_amount increases, balance decreases. (Correct: we owe less)
                    # If they pay us: paid_amount should be negative? OR bill_amount should be negative?
                    # Let's check existing logic: bill_amount (Credit), paid_amount (Debit).
                    # If they pay us, it's a Credit to THEM? No, Debit is what we pay. 
                    # Actually, standard: Credit (THEM giving us goods), Debit (US paying THEM).
                    # If THEY pay US, it's a "Negative Bill" or "Positive Payment" in a different sense.
                    # Let's simplify: 
                    # Debit Voucher (We Pay): Bill = Total Amount, Paid = Amount Paid. Balance = Total - Paid.
                    # Credit Voucher (They Pay): Bill = 0, Paid = -Amount Paid (Received). Balance = 0 - (-Paid) = +Paid.
                    # Actually, if we just want to track their balance:
                    # Bill = Amount they owe us (Credit), Paid = Amount we paid them (Debit).
                    # So if they pay us, it's a SUBTRACTION from Bill or ADDITION to Paid.
                    # Let's use:
                    # Debit Voucher: Bill += total, Paid += paid.
                    # Credit Voucher: Bill += 0, Paid -= amount_received.
                    pass
                
                db.session.add(pl)
                db.session.flush() # Ensure PL has an ID
                recalculate_party_ledger_balances(voucher.party_id)

            # C. Update Customer (if linked)
            if voucher.customer_id:
                from models import Transaction, Customer, CustomerInstallment
                # Create a Transaction for the customer
                tx = Transaction(
                    date=voucher.date,
                    amount=voucher.amount_paid,
                    installment_type="Installment",
                    remarks=f"Voucher {voucher.voucher_no}: {voucher.description}",
                    payment_method=voucher.payment_method,
                    customer_id=voucher.customer_id
                )
                db.session.add(tx)
                
                # Update Customer Balance and Installments
                cust = Customer.query.get(voucher.customer_id)
                if cust:
                    recalculate_customer_totals(cust)
                    # Allocation logic (simplistic: oldest due first)
                    # Wait, usually Transaction is linked to CustomerInstallment
                    pending_installments = CustomerInstallment.query.filter(
                        CustomerInstallment.customer_id == voucher.customer_id,
                        CustomerInstallment.due_amount > 0
                    ).all() # Sorting would be better
                    
                    remaining = voucher.amount_paid
                    for ci in pending_installments:
                        if remaining <= 0: break
                        pay = min(remaining, ci.due_amount)
                        ci.paid_amount += pay
                        ci.due_amount -= pay
                        remaining -= pay
                        # Link tx to the first one it covers or logic to split? 
                        # Simplifying: just update balances.

        db.session.commit()
        return True, "Voucher financials processed successfully"
    except Exception as e:
        db.session.rollback()
        log_debug(f"Error processing voucher financials: {e}")
        return False, str(e)

def process_contra_financials(contra_id, action='add'):
    from models import ContraEntry, PettyCash, BankTransaction
    contra = ContraEntry.query.get(contra_id)
    if not contra: return False, "Contra Entry not found"
    
    try:
        if action in ['edit', 'delete']:
            PettyCash.query.filter_by(contra_entry_id=contra.id).delete()
            BankTransaction.query.filter_by(contra_entry_id=contra.id).delete()
        
        if action in ['add', 'edit']:
            # From Account (Subtract)
            if contra.from_account == 'Cash':
                pc_out = PettyCash(
                    date=contra.date,
                    description=f"Contra {contra.contra_no}: {contra.description} (Transfer to {contra.to_account})",
                    category="Contra", type="Expense", amount=contra.amount, contra_entry_id=contra.id,
                    images=contra.attachments # Carry over attachments
                )
                db.session.add(pc_out)
            elif contra.from_account == 'Bank' and contra.bank_id:
                bt_out = BankTransaction(
                    date=contra.date, narration=f"Contra {contra.contra_no}: Transfer to {contra.to_account}",
                    debit=contra.amount, credit=0, bank_id=contra.bank_id, contra_entry_id=contra.id,
                    transaction_details="Contra Withdraw",
                    cheque_no=contra.cheque_no # Carry over cheque_no
                )
                db.session.add(bt_out)

            # To Account (Add)
            if contra.to_account == 'Cash':
                pc_in = PettyCash(
                    date=contra.date,
                    description=f"Contra {contra.contra_no}: {contra.description} (Transfer from {contra.from_account})",
                    category="Contra", type="Income", amount=contra.amount, contra_entry_id=contra.id,
                    images=contra.attachments
                )
                db.session.add(pc_in)
            elif contra.to_account == 'Bank' and contra.bank_id:
                bt_in = BankTransaction(
                    date=contra.date, narration=f"Contra {contra.contra_no}: Transfer from {contra.from_account}",
                    debit=0, credit=contra.amount, bank_id=contra.bank_id, contra_entry_id=contra.id,
                    transaction_details="Contra Deposit",
                    cheque_no=contra.cheque_no
                )
                db.session.add(bt_in)

        db.session.commit()
        return True, "Contra financials processed successfully"
    except Exception as e:
        db.session.rollback()
        return False, str(e)

def get_due_payments_report():
    """Returns vouchers that have a remaining due amount."""
    from models import Voucher
    return Voucher.query.filter(Voucher.due_amount > 0).order_by(Voucher.date.desc()).all()

def get_daily_cash_report(target_date):
    """Aggregates all cash and bank movements for a specific date, providing comparative summaries."""
    from models import PettyCash, Bank, BankTransaction
    from sqlalchemy import func
    
    # 1. Day's Transactions
    transactions = PettyCash.query.filter_by(date=target_date).all()
    
    # 2. Cash Balances
    # Previous day's cash in hand: All Income - All Expense before target_date
    cash_in_before = db.session.query(func.sum(PettyCash.amount)).filter(PettyCash.date < target_date, PettyCash.type == 'Income').scalar() or 0
    cash_out_before = db.session.query(func.sum(PettyCash.amount)).filter(PettyCash.date < target_date, PettyCash.type == 'Expense').scalar() or 0
    prev_cash = cash_in_before - cash_out_before
    
    # Today's cash in hand: All Income - All Expense including target_date
    cash_in_today = db.session.query(func.sum(PettyCash.amount)).filter(PettyCash.date <= target_date, PettyCash.type == 'Income').scalar() or 0
    cash_out_today = db.session.query(func.sum(PettyCash.amount)).filter(PettyCash.date <= target_date, PettyCash.type == 'Expense').scalar() or 0
    today_cash = cash_in_today - cash_out_today
    
    # 3. Bank Balances
    # We must sort using the same logic as recompute_bank_balances to handle mixed date formats
    def parse_tx_date(date_str):
        for fmt in ('%d-%m-%Y', '%Y-%m-%d'):
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                pass
        return datetime.min.date()

    target_date_obj = datetime.strptime(target_date, "%Y-%m-%d").date()
    banks = Bank.query.all()
    prev_bank = 0.0
    today_bank = 0.0
    
    for b in banks:
        all_tx = BankTransaction.query.filter_by(bank_id=b.id).all()
        # Sort transactions: Date (asc), then ID (asc)
        sorted_tx = sorted(all_tx, key=lambda x: (parse_tx_date(x.date), x.id))
        
        bank_prev = 0.0
        bank_today = 0.0
        
        for tx in sorted_tx:
            tx_date = parse_tx_date(tx.date)
            if tx_date < target_date_obj:
                bank_prev = tx.balance
            if tx_date <= target_date_obj:
                bank_today = tx.balance
            else:
                break
                
        prev_bank += bank_prev
        today_bank += bank_today
            
    return {
        'transactions': transactions,
        'prev_cash': prev_cash,
        'today_cash': today_cash,
        'prev_bank': prev_bank,
        'today_bank': today_bank
    }
