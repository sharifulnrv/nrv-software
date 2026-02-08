from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from werkzeug.utils import secure_filename
import os
from models import Director, Customer, Transaction, PettyCash, Bank, BankTransaction
from database import db
from logic import sync_to_excel, restore_from_excel
import pandas as pd
import io
from datetime import datetime
from flask import send_file
import random
import string
import json
from telegram_utils import send_telegram_message

main = Blueprint('main', __name__)

@main.route('/')
def index():
    directors = Director.query.all()
    
    # Calculate Grand Totals
    total_payable = 0
    total_paid = 0
    total_due = 0
    
    for d in directors:
        share_val = (d.total_share * d.per_share_value) + d.land_value_extra_share
        total_payable += share_val
        total_paid += d.total_paid
        total_due += (share_val - d.total_paid)
        
    # Calculate Customer Totals
    customers = Customer.query.all()
    cust_total_payable = sum(c.total_price for c in customers)
    cust_total_paid = sum(c.total_paid for c in customers)
    cust_total_due = sum(c.due_amount for c in customers)

    return render_template('index.html', directors=directors, 
                         grand_total_payable=total_payable, 
                         grand_total_paid=total_paid, 
                         grand_total_due=total_due,
                         cust_total_payable=cust_total_payable,
                         cust_total_paid=cust_total_paid,
                         cust_total_due=cust_total_due)

def verify_password():
    password = request.form.get('admin_password')
    admin_pass = current_app.config.get('ADMIN_PASSWORD')
    if password == admin_pass:
        return True
    return False

# --- OTP Store (In-Memory for simplicity) ---
otp_store = {}

@main.route('/change_password_request', methods=['GET', 'POST'])
def change_password_request():
    if request.method == 'POST':
        # Generate OTP
        otp = ''.join(random.choices(string.digits, k=6))
        
        if send_telegram_message(f"Your OTP for Password Change is: {otp}"):
            otp_store['current_otp'] = otp
            flash('OTP sent to Telegram!', 'info')
            return redirect(url_for('main.verify_otp_page'))
        else:
            flash('Failed to send OTP. Check internet or bot config.', 'danger')
            
    return render_template('change_password_request.html')

@main.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp_page():
    if request.method == 'POST':
        user_otp = request.form.get('otp')
        new_password = request.form.get('new_password')
        
        if 'current_otp' in otp_store and otp_store['current_otp'] == user_otp:
            # Update Password
            config_path = os.path.join(current_app.root_path, 'admin_config.json')
            with open(config_path, 'w') as f:
                json.dump({"ADMIN_PASSWORD": new_password}, f)
            
            # Update Runtime Config
            current_app.config['ADMIN_PASSWORD'] = new_password
            
            # Clear OTP
            del otp_store['current_otp']
            
            flash('Password Changed Successfully!', 'success')
            return redirect(url_for('main.index'))
        else:
            flash('Invalid OTP!', 'danger')
            
    return render_template('verify_otp.html')


# --- Director Routes ---
@main.route('/director/add', methods=['GET', 'POST'])
def add_director():
    if request.method == 'POST':
        if not verify_password():
            flash('Invalid Admin Password!', 'danger')
            return redirect(url_for('main.add_director'))

        name = request.form.get('name')
        phone = request.form.get('phone')
        
        if name:
            new_director = Director(
                name=name, 
                phone=phone,
                bank_name=request.form.get('bank_name'),
                total_share=float(request.form.get('total_share') or 0),
                per_share_value=float(request.form.get('per_share_value') or 0),
                fair_cost=float(request.form.get('fair_cost') or 0),
                land_value_extra_share=float(request.form.get('land_value_extra_share') or 0),
                total_paid=float(request.form.get('total_paid') or 0),
                payment_history=request.form.get('payment_history')
            )
            db.session.add(new_director)
            db.session.commit()
            sync_to_excel()
            flash('Director added successfully!', 'success')
            return redirect(url_for('main.index'))
    return render_template('director_form.html')

@main.route('/director/edit/<int:id>', methods=['GET', 'POST'])
def edit_director(id):
    director = Director.query.get_or_404(id)
    if request.method == 'POST':
        if not verify_password():
            flash('Invalid Admin Password!', 'danger')
            return redirect(url_for('main.edit_director', id=id))

        director.name = request.form.get('name')
        director.phone = request.form.get('phone')
        director.bank_name = request.form.get('bank_name')
        director.total_share = float(request.form.get('total_share') or 0)
        director.per_share_value = float(request.form.get('per_share_value') or 0)
        director.fair_cost = float(request.form.get('fair_cost') or 0)
        director.land_value_extra_share = float(request.form.get('land_value_extra_share') or 0)
        director.total_paid = float(request.form.get('total_paid') or 0)
        director.payment_history = request.form.get('payment_history')
        
        db.session.commit()
        sync_to_excel()
        flash('Director updated successfully!', 'success')
        return redirect(url_for('main.index'))
    return render_template('director_form.html', director=director)

@main.route('/director/delete/<int:id>', methods=['POST'])
def delete_director(id):
    if not verify_password():
        flash('Invalid Admin Password!', 'danger')
        return redirect(url_for('main.index'))

    director = Director.query.get_or_404(id)
    # Optional: logic to handle orphaned customers (delete or unlink). 
    # For now, let's assume we delete them or db cascade (we didn't set cascade).
    # Ideally we should warn user. But per request, simple Remove.
    # Let's delete customers first manually if constraints exist
    for customer in director.customers:
        db.session.delete(customer)
        
    db.session.delete(director)
    db.session.commit()
    sync_to_excel()
    flash('Director and their customers removed!', 'info')
    return redirect(url_for('main.index'))


# --- Customer Routes ---
@main.route('/customer/add', methods=['GET', 'POST'])
def add_customer():
    directors = Director.query.all()
    if request.method == 'POST':
        if not verify_password():
            flash('Invalid Admin Password!', 'danger')
            return redirect(url_for('main.add_customer'))

        # Extraction
        director_id = request.form.get('director_id')
        customer_id = request.form.get('customer_id')
        name = request.form.get('name')
        phone = request.form.get('phone')
        plot_no = request.form.get('plot_no')
        total_price = float(request.form.get('total_price') or 0)
        down_payment = float(request.form.get('down_payment') or 0)
        monthly_installment = float(request.form.get('monthly_installment') or 0)
        total_paid = float(request.form.get('total_paid') or 0)
        
        # Calculation
        due_amount = total_price - total_paid
        
        new_customer = Customer(
            director_id=director_id,
            customer_id=customer_id,
            name=name,
            phone=phone,
            plot_no=plot_no,
            total_price=total_price,
            down_payment=down_payment,
            monthly_installment=monthly_installment,
            total_paid=total_paid,
            due_amount=due_amount
        )
        db.session.add(new_customer)
        db.session.commit()
        sync_to_excel()
        flash('Customer added successfully!', 'success')
        return redirect(url_for('main.index'))
        
    return render_template('customer_form.html', directors=directors)

@main.route('/customer/edit/<int:id>', methods=['GET', 'POST'])
def edit_customer(id):
    customer = Customer.query.get_or_404(id)
    directors = Director.query.all()
    
    if request.method == 'POST':
        if not verify_password():
            flash('Invalid Admin Password!', 'danger')
            return redirect(url_for('main.edit_customer', id=id))

        customer.director_id = request.form.get('director_id')
        customer.customer_id = request.form.get('customer_id')
        customer.name = request.form.get('name')
        customer.phone = request.form.get('phone')
        customer.plot_no = request.form.get('plot_no')
        customer.total_price = float(request.form.get('total_price') or 0)
        customer.down_payment = float(request.form.get('down_payment') or 0)
        customer.monthly_installment = float(request.form.get('monthly_installment') or 0)
        customer.total_paid = float(request.form.get('total_paid') or 0)
        
        # Calc Due
        customer.due_amount = customer.total_price - customer.total_paid
        
        db.session.commit()
        sync_to_excel()
        flash('Customer updated successfully!', 'success')
        return redirect(url_for('main.index'))
        
    return render_template('customer_form.html', customer=customer, directors=directors)

@main.route('/delete_customer/<int:id>', methods=['POST'])
def delete_customer(id):
    if not verify_password():
        flash('Invalid Admin Password!', 'danger')
        return redirect(url_for('main.index'))

    customer = Customer.query.get_or_404(id)
    db.session.delete(customer)
    db.session.commit()
    # Sync to Excel
    sync_to_excel()
    flash('Customer deleted!', 'success')
    return redirect(url_for('main.index'))

# --- Transaction Routes ---
@main.route('/manage_transactions/<int:customer_id>', methods=['GET', 'POST'])
def manage_transactions(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    
    if request.method == 'POST':
        date = request.form.get('date')
        amount = float(request.form.get('amount') or 0)
        installment_type = request.form.get('installment_type')
        bank_name = request.form.get('bank_name')
        transaction_id = request.form.get('transaction_id')
        remarks = request.form.get('remarks')
        
        # Handle Images
        images = []
        if 'evidence' in request.files:
            files = request.files.getlist('evidence')
            for file in files:
                if file and file.filename != '':
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
                    images.append(filename)
        
        new_tx = Transaction(
            date=date,
            amount=amount,
            installment_type=installment_type,
            bank_name=bank_name,
            transaction_id=transaction_id,
            remarks=remarks,
            images=','.join(images),
            customer=customer
        )
        
        # Update Customer Totals
        customer.total_paid += amount
        customer.due_amount = customer.total_price - customer.total_paid
        
        db.session.add(new_tx)
        db.session.commit()
        sync_to_excel()
        flash('Transaction Added!', 'success')
        return redirect(url_for('main.manage_transactions', customer_id=customer_id))
        
    transactions = Transaction.query.filter_by(customer_id=customer_id).all()
    return render_template('customer_transactions.html', customer=customer, transactions=transactions)

@main.route('/delete_transaction/<int:id>')
def delete_transaction(id):
    tx = Transaction.query.get_or_404(id)
    customer_id = tx.customer_id
    customer = Customer.query.get(customer_id)
    
    # Revert Customer Totals
    customer.total_paid -= tx.amount
    customer.due_amount = customer.total_price - customer.total_paid
    
    db.session.delete(tx)
    db.session.commit()
    sync_to_excel()
    flash('Transaction Deleted!', 'warning')
    return redirect(url_for('main.manage_transactions', customer_id=customer_id))

@main.route('/transaction/edit/<int:id>', methods=['POST'])
def edit_transaction_details(id):
    if not verify_password():
        flash('Invalid Admin Password!', 'danger')
        # We need customer_id to redirect
        tx = Transaction.query.get(id)
        if tx:
            # Revert to manage page if possible
            return redirect(url_for('main.manage_transactions', customer_id=tx.customer_id))
        return redirect(url_for('main.index'))

    tx = Transaction.query.get_or_404(id)
    customer = Customer.query.get(tx.customer_id)
    
    # 1. Revert Old Amount from Customer Totals
    customer.total_paid -= tx.amount
    
    # 2. Update Transaction Data
    tx.date = request.form.get('date')
    tx.amount = float(request.form.get('amount') or 0)
    tx.installment_type = request.form.get('installment_type')
    tx.bank_name = request.form.get('bank_name')
    tx.transaction_id = request.form.get('transaction_id')
    tx.remarks = request.form.get('remarks')
    
    # 3. Handle New Images (Append)
    if 'evidence' in request.files:
        files = request.files.getlist('evidence')
        new_images = []
        for file in files:
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
                new_images.append(filename)
        
        if new_images:
            current_images = tx.images.split(',') if tx.images else []
            updated_images = current_images + new_images
            tx.images = ','.join(updated_images)
            
    # 4. Apply New Amount to Customer Totals
    customer.total_paid += tx.amount
    customer.due_amount = customer.total_price - customer.total_paid
    
    db.session.commit()
    sync_to_excel()
    flash('Transaction Updated!', 'success')
    return redirect(url_for('main.manage_transactions', customer_id=customer.id))


# --- Petty Cash Routes ---
@main.route('/petty_cash', methods=['GET', 'POST'])
def manage_petty_cash():
    if request.method == 'POST':
        if not verify_password():
            flash('Invalid Admin Password!', 'danger')
            return redirect(url_for('main.manage_petty_cash'))

        date = request.form.get('date')
        description = request.form.get('description')
        category = request.form.get('category')
        type = request.form.get('type')
        amount = float(request.form.get('amount') or 0)
        
        # Handle Evidence Files
        images = []
        if 'evidence' in request.files:
            files = request.files.getlist('evidence')
            for file in files:
                if file and file.filename != '':
                    filename = secure_filename(file.filename)
                    # Optional: Add timestamp/UUID to filename to prevent collisions?
                    # For now keeping it simple as per previous pattern
                    file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
                    images.append(filename)
        
        new_entry = PettyCash(
            date=date,
            description=description,
            category=category,
            type=type,
            amount=amount,
            images=','.join(images)
        )
        db.session.add(new_entry)
        db.session.commit()
        sync_to_excel()
        flash('Petty Cash Entry Added!', 'success')
        return redirect(url_for('main.manage_petty_cash'))
        
    # Filter Logic
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    filter_category = request.args.get('category')
    
    query = PettyCash.query
    
    if start_date:
        query = query.filter(PettyCash.date >= start_date)
    if end_date:
        query = query.filter(PettyCash.date <= end_date)
    if filter_category and filter_category != 'All':
        query = query.filter(PettyCash.category == filter_category)
        
    entries = query.order_by(PettyCash.date.desc()).all()
    
    total_income = sum(e.amount for e in entries if e.type == 'Income')
    total_expense = sum(e.amount for e in entries if e.type == 'Expense')
    current_balance = total_income - total_expense
    
    return render_template('petty_cash.html', entries=entries, 
                         total_income=total_income, 
                         total_expense=total_expense, 
                         current_balance=current_balance)

@main.route('/petty_cash/export')
def export_petty_cash_report():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    filter_category = request.args.get('category')
    
    query = PettyCash.query
    
    if start_date:
        query = query.filter(PettyCash.date >= start_date)
    if end_date:
        query = query.filter(PettyCash.date <= end_date)
    if filter_category and filter_category != 'All':
        query = query.filter(PettyCash.category == filter_category)
        
    entries = query.order_by(PettyCash.date.desc()).all()
    
    data = []
    for e in entries:
        data.append({
            'Date': e.date,
            'Description': e.description,
            'Category': e.category,
            'Type': e.type,
            'Income': e.amount if e.type == 'Income' else 0,
            'Expense': e.amount if e.type == 'Expense' else 0,
            'Images': e.images
        })
        
    df = pd.DataFrame(data)
    
    # Calculate totals for the report
    total_income = df['Income'].sum() if not df.empty else 0
    total_expense = df['Expense'].sum() if not df.empty else 0
    
    # Append Total Row
    if not df.empty:
        df.loc['Total'] = pd.Series(dtype='float64')
        df.at['Total', 'Description'] = 'TOTAL'
        df.at['Total', 'Income'] = total_income
        df.at['Total', 'Expense'] = total_expense
        df.at['Total', 'Category'] = f'Balance: {total_income - total_expense}'
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Petty_Cash_Report', index=False)
        # Polish width
        worksheet = writer.sheets['Petty_Cash_Report']
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

    output.seek(0)
    return send_file(output, download_name="Petty_Cash_Report.xlsx", as_attachment=True)

@main.route('/delete_petty_cash/<int:id>', methods=['POST'])
def delete_petty_cash(id):
    if not verify_password():
        flash('Invalid Admin Password!', 'danger')
        return redirect(url_for('main.manage_petty_cash'))

    entry = PettyCash.query.get_or_404(id)
    db.session.delete(entry)
    db.session.commit()
    sync_to_excel()
    flash('Entry Deleted!', 'info')
    return redirect(url_for('main.manage_petty_cash'))

@main.route('/petty_cash/invoice/<int:id>')
def invoice_view(id):
    entry = PettyCash.query.get_or_404(id)
    return render_template('invoice.html', entry=entry, now=datetime.now())

@main.route('/petty_cash/edit/<int:id>', methods=['POST'])
def edit_petty_cash(id):
    if not verify_password():
        flash('Invalid Admin Password!', 'danger')
        return redirect(url_for('main.manage_petty_cash'))

    entry = PettyCash.query.get_or_404(id)
    
    entry.date = request.form.get('date')
    entry.description = request.form.get('description')
    entry.category = request.form.get('category')
    entry.type = request.form.get('type')
    entry.amount = float(request.form.get('amount') or 0)
    
    # Handle New Evidence Files (Append to existing?)
    # For simplicity, if new files are uploaded, we append them.
    if 'evidence' in request.files:
        files = request.files.getlist('evidence')
        new_images = []
        for file in files:
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
                new_images.append(filename)
        
        if new_images:
            current_images = entry.images.split(',') if entry.images else []
            updated_images = current_images + new_images
            entry.images = ','.join(updated_images)
            
    db.session.commit()
    sync_to_excel()
    flash('Entry Updated Successfully!', 'success')
    return redirect(url_for('main.manage_petty_cash'))

@main.route('/report/download')
def download_report():
    # Generate a summary report
    # Group by Director, Sum Collection (Total Paid), Outstanding (Due Amount)
    
    directors = Director.query.all()
    report_data = []
    
    grand_total_collection = 0
    grand_total_due = 0
    
    for d in directors:
        d_collection = sum(c.total_paid for c in d.customers)
        d_due = sum(c.due_amount for c in d.customers)
        
        grand_total_collection += d_collection
        grand_total_due += d_due
        
        report_data.append({
            'Director': d.name,
            'Total Collection': d_collection,
            'Total Outstanding Dues': d_due
        })
        
    # Append Grand Total
    report_data.append({
        'Director': 'GRAND TOTAL',
        'Total Collection': grand_total_collection,
        'Total Outstanding Dues': grand_total_due
    })
    
    df = pd.DataFrame(report_data)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Summary_Report', index=False)
        
        # Polish width
        worksheet = writer.sheets['Summary_Report']
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

    output.seek(0)
    
    return send_file(output, download_name="Summary_Report.xlsx", as_attachment=True)

# --- Excel Helper ---
def format_excel_width(writer, sheet_name):
    """Helper to auto-adjust column width for Excel sheets."""
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

# --- New Customer Reports ---

@main.route('/report/customers/all')
def download_all_customers_report():
    customers = Customer.query.join(Director).all()
    
    data = []
    for c in customers:
        data.append({
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
        
    df = pd.DataFrame(data)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='All_Customers', index=False)
        format_excel_width(writer, 'All_Customers')
        
    output.seek(0)
    return send_file(output, download_name="All_Customers.xlsx", as_attachment=True)

@main.route('/report/director/<int:id>/customers')
def download_director_customers_report(id):
    director = Director.query.get_or_404(id)
    customers = director.customers
    
    data = []
    for c in customers:
        data.append({
            'Director Name': director.name,
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
        
    df = pd.DataFrame(data)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        sheet_name = 'Customers'
        df.to_excel(writer, sheet_name=sheet_name, index=False)
        format_excel_width(writer, sheet_name)
        
    output.seek(0)
    filename = f"Director_{secure_filename(director.name)}_Customers.xlsx"
    return send_file(output, download_name=filename, as_attachment=True)

@main.route('/report/customer/<int:id>')
def download_individual_customer_report(id):
    c = Customer.query.get_or_404(id)
    
    # 1. Profile Data
    profile_data = [{
        'Field': 'Customer ID', 'Value': c.customer_id},
        {'Field': 'Name', 'Value': c.name},
        {'Field': 'Director', 'Value': c.director.name},
        {'Field': 'Phone', 'Value': c.phone},
        {'Field': 'Plot No', 'Value': c.plot_no},
        {'Field': 'Total Price', 'Value': c.total_price},
        {'Field': 'Down Payment', 'Value': c.down_payment},
        {'Field': 'Monthly Installment', 'Value': c.monthly_installment},
        {'Field': 'Total Paid', 'Value': c.total_paid},
        {'Field': 'Due Amount', 'Value': c.due_amount}
    ]
    df_profile = pd.DataFrame(profile_data)
    
    # 2. Transactions Data
    tx_data = []
    for tx in c.transactions:
        tx_data.append({
            'Date': tx.date,
            'Amount': tx.amount,
            'Installment Type': tx.installment_type,
            'Bank Name': tx.bank_name,
            'Transaction ID': tx.transaction_id,
            'Remarks': tx.remarks
        })
    df_tx = pd.DataFrame(tx_data)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_profile.to_excel(writer, sheet_name='Profile', index=False)
        format_excel_width(writer, 'Profile')
        
        df_tx.to_excel(writer, sheet_name='Transactions', index=False)
        format_excel_width(writer, 'Transactions')
        
    output.seek(0)
    filename = f"Customer_{secure_filename(c.name)}_Report.xlsx"
    return send_file(output, download_name=filename, as_attachment=True)

    return send_file(output, download_name=filename, as_attachment=True)

# --- Bank Management Routes ---
@main.route('/banks', methods=['GET', 'POST'])
def manage_banks():
    if request.method == 'POST':
        if not verify_password():
            flash('Invalid Admin Password!', 'danger')
            return redirect(url_for('main.manage_banks'))

        # Add New Bank
        new_bank = Bank(
            bank_name=request.form.get('bank_name'),
            branch=request.form.get('branch'),
            account_holder_name=request.form.get('account_holder_name'),
            joint_name=request.form.get('joint_name'),
            fhp=request.form.get('fhp'),
            address=request.form.get('address'),
            city=request.form.get('city'),
            phone=request.form.get('phone'),
            customer_id=request.form.get('customer_id'),
            account_no=request.form.get('account_no'),
            prev_account_no=request.form.get('prev_account_no'),
            account_type=request.form.get('account_type'),
            currency=request.form.get('currency'),
            status=request.form.get('status')
        )
        db.session.add(new_bank)
        db.session.commit()
        sync_to_excel()
        flash('Bank Account Added!', 'success')
        return redirect(url_for('main.manage_banks'))
        
    banks = Bank.query.all()
    return render_template('banks.html', banks=banks)

@main.route('/bank/edit/<int:id>', methods=['POST'])
def edit_bank(id):
    if not verify_password():
        flash('Invalid Admin Password!', 'danger')
        return redirect(url_for('main.manage_banks'))

    bank = Bank.query.get_or_404(id)
    
    bank.bank_name = request.form.get('bank_name')
    bank.branch = request.form.get('branch')
    bank.account_holder_name = request.form.get('account_holder_name')
    bank.joint_name = request.form.get('joint_name')
    bank.fhp = request.form.get('fhp')
    bank.address = request.form.get('address')
    bank.city = request.form.get('city')
    bank.phone = request.form.get('phone')
    bank.customer_id = request.form.get('customer_id')
    bank.account_no = request.form.get('account_no')
    bank.prev_account_no = request.form.get('prev_account_no')
    bank.account_type = request.form.get('account_type')
    bank.currency = request.form.get('currency')
    bank.status = request.form.get('status')
    
    db.session.commit()
    sync_to_excel()
    flash('Bank Account Updated!', 'success')
    return redirect(url_for('main.manage_banks'))

@main.route('/bank/delete/<int:id>', methods=['POST'])
def delete_bank(id):
    if not verify_password():
        flash('Invalid Admin Password!', 'danger')
        return redirect(url_for('main.manage_banks'))

    bank = Bank.query.get_or_404(id)
    db.session.delete(bank)
    db.session.commit()
    sync_to_excel()
    flash('Bank Account Deleted!', 'warning')
    return redirect(url_for('main.manage_banks'))

@main.route('/bank/<int:id>/ledger', methods=['GET', 'POST'])
def bank_ledger(id):
    bank = Bank.query.get_or_404(id)
    
    if request.method == 'POST':
        if not verify_password():
            flash('Invalid Admin Password!', 'danger')
            return redirect(url_for('main.bank_ledger', id=id))

        date = request.form.get('date')
        cheque_no = request.form.get('cheque_no')
        ref_no = request.form.get('ref_no')
        narration = request.form.get('narration')
        transaction_details = request.form.get('transaction_details')
        debit = float(request.form.get('debit') or 0)
        credit = float(request.form.get('credit') or 0)
        
        # Calculate Balance
        # Simple approach: Get last transaction balance or 0, then add credit/sub debit
        # NOTE: This simple approach assumes append-only. 
        # For a real ledger with back-dated edits, we'd need to recompute subsequent balances.
        # Given the requirements (like Petty Cash), we'll do simple running balance for now.
        
        last_tx = BankTransaction.query.filter_by(bank_id=id).order_by(BankTransaction.id.desc()).first()
        current_bal = last_tx.balance if last_tx else 0.0
        new_balance = current_bal + credit - debit
        
        new_tx = BankTransaction(
            date=date,
            cheque_no=cheque_no,
            ref_no=ref_no,
            narration=narration,
            transaction_details=transaction_details,
            debit=debit,
            credit=credit,
            balance=new_balance,
            bank=bank
        )
        
        db.session.add(new_tx)
        db.session.commit()
        sync_to_excel()
        flash('Transaction Added to Ledger!', 'success')
        return redirect(url_for('main.bank_ledger', id=id))
        
    transactions = BankTransaction.query.filter_by(bank_id=id).order_by(BankTransaction.id).all()
    
    # --- Date Filter Logic ---
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    
    if start_date_str or end_date_str:
        filtered_transactions = []
        
        # Convert filter inputs (YYYY-MM-DD -> datetime)
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d') if start_date_str else None
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d') if end_date_str else None
        
        for tx in transactions:
            try:
                # Convert DB date (DD-MM-YYYY -> datetime)
                tx_date = datetime.strptime(tx.date, '%d-%m-%Y')
                
                # Apply Filter
                if start_date and tx_date < start_date:
                    continue
                if end_date and tx_date > end_date:
                    continue
                
                filtered_transactions.append(tx)
            except ValueError:
                # Handle cases where DB date format might be irregular
                filtered_transactions.append(tx)
                
        transactions = filtered_transactions

    return render_template('bank_ledger.html', bank=bank, transactions=transactions, start_date=start_date_str, end_date=end_date_str)

@main.route('/bank/transaction/delete/<int:id>', methods=['POST'])
def delete_bank_transaction(id):
    if not verify_password():
        flash('Invalid Admin Password!', 'danger')
        # We need bank_id to redirect
        tx = BankTransaction.query.get(id)
        if tx:
            return redirect(url_for('main.bank_ledger', id=tx.bank_id))
        return redirect(url_for('main.manage_banks'))

    tx = BankTransaction.query.get_or_404(id)
    bank_id = tx.bank_id
    
    # NOTE: Deleting a transaction in the middle breaks running balance for subsequent rows.
    # We will delete it, but advise user to export/re-import or handle carefully.
    # A full recompute function would be ideal here if strict accounting is needed.
    # For now, we just delete.
    
    db.session.delete(tx)
    db.session.commit()
    
    # Simple Recompute of ALL transactions for this bank to fix balance
    all_txs = BankTransaction.query.filter_by(bank_id=bank_id).order_by(BankTransaction.date, BankTransaction.id).all()
    running_bal = 0
    for t in all_txs:
        running_bal += (t.credit - t.debit)
        t.balance = running_bal
    db.session.commit()
    
    sync_to_excel()
    flash('Transaction Deleted & Balances Recomputed!', 'warning')
    return redirect(url_for('main.bank_ledger', id=bank_id))

@main.route('/bank/<int:id>/export')
def export_bank_ledger(id):
    bank = Bank.query.get_or_404(id)
    transactions = BankTransaction.query.filter_by(bank_id=id).order_by(BankTransaction.date).all()
    
    data = []
    for tx in transactions:
        data.append({
            'Date': tx.date,
            'Cheque No': tx.cheque_no,
            'Ref No': tx.ref_no,
            'Narration': tx.narration,
            'Debit': tx.debit,
            'Credit': tx.credit,
            'Balance': tx.balance
        })
        
    df = pd.DataFrame(data)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        sheet_name = 'Ledger'
        df.to_excel(writer, sheet_name=sheet_name, index=False)
        format_excel_width(writer, sheet_name)
        
    output.seek(0)
    filename = f"Bank_Ledger_{secure_filename(bank.bank_name)}.xlsx"
    return send_file(output, download_name=filename, as_attachment=True)

# --- Settings & Restore ---
@main.route('/settings')
def settings():
    # List available backups
    backups = []
    backup_dir = os.path.join(current_app.root_path, 'backups')
    if os.path.exists(backup_dir):
        files = sorted(os.listdir(backup_dir), reverse=True)
        for f in files:
            if f.endswith('.xlsx'):
                backups.append(f)
    return render_template('settings.html', backups=backups)

@main.route('/settings/restore', methods=['POST'])
def restore_data():
    if 'backup_file' in request.files:
        file = request.files['backup_file']
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            success, msg = restore_from_excel(filepath)
            os.remove(filepath) # Clean up temp file
            
            if success:
                flash('System successfully restored from upload!', 'success')
            else:
                flash(f'Restore failed: {msg}', 'danger')
                
    elif 'backup_filename' in request.form:
        # Restore from internal backup
        filename = request.form.get('backup_filename')
        filepath = os.path.join(current_app.root_path, 'backups', filename)
        if os.path.exists(filepath):
            success, msg = restore_from_excel(filepath)
            if success:
                flash(f'System restored from {filename}', 'success')
            else:
                flash(f'Restore failed: {msg}', 'danger')
        else:
            flash('Backup file not found.', 'danger')
            
    return redirect(url_for('main.settings'))
