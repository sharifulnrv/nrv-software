from database import db
from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=True)
    telegram_chat_id = db.Column(db.String(50), nullable=True) # For password reset

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Director(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    bank_name = db.Column(db.String(100))
    
    # Financials
    # Financials
    total_share = db.Column(db.Float, default=0.0)
    per_share_value = db.Column(db.Float, default=0.0)
    fair_cost = db.Column(db.Float, default=0.0)
    land_value_extra_share = db.Column(db.Float, default=0.0)
    
    total_paid = db.Column(db.Float, default=0.0)
    total_due = db.Column(db.Float, default=0.0)
    payment_history = db.Column(db.Text) # Date & Deposit text blob
    updated_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    @property
    def available_shares(self):
        assigned_shares = sum(c.shares for c in self.customers)
        return self.total_share - assigned_shares


class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.String(50), nullable=False) # User visible ID
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    plot_no = db.Column(db.String(50))
    total_price = db.Column(db.Float, default=0.0)
    down_payment = db.Column(db.Float, default=0.0)
    monthly_installment = db.Column(db.Float, default=0.0)
    total_paid = db.Column(db.Float, default=0.0)
    due_amount = db.Column(db.Float, default=0.0)
    shares = db.Column(db.Float, default=0.0)
    
    director_id = db.Column(db.Integer, db.ForeignKey('director.id'), nullable=False)
    
    transactions = db.relationship('Transaction', backref='customer', lazy=True, cascade="all, delete-orphan")
    installments = db.relationship('CustomerInstallment', backref='customer', lazy=True, cascade="all, delete-orphan")

    # New Fields
    father_name = db.Column(db.String(100))
    mother_name = db.Column(db.String(100))
    dob = db.Column(db.String(20)) # Date of Birth
    religion = db.Column(db.String(50))
    profession = db.Column(db.String(100))
    nid_no = db.Column(db.String(50))
    present_address = db.Column(db.String(255))
    permanent_address = db.Column(db.String(255))
    updated_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

Director.customers = db.relationship('Customer', backref='director', lazy=True, order_by=Customer.customer_id)

class Installment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False) # e.g. "Piling Installment"
    amount_per_share = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    
    customer_installments = db.relationship('CustomerInstallment', backref='installment', lazy=True, cascade="all, delete-orphan")

    @property
    def total_expected(self):
        from models import Director
        total_shares = sum(d.total_share for d in Director.query.all())
        return total_shares * self.amount_per_share

    @property
    def total_collected(self):
        return sum(ci.paid_amount for ci in self.customer_installments)

    @property
    def total_due(self):
        return self.total_expected - self.total_collected

class CustomerInstallment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    installment_id = db.Column(db.Integer, db.ForeignKey('installment.id'), nullable=False)
    total_amount = db.Column(db.Float, default=0.0) # Calculated: shares * amount_per_share
    paid_amount = db.Column(db.Float, default=0.0)
    due_amount = db.Column(db.Float, default=0.0) # Calculated: total_amount - paid_amount
    
    transactions = db.relationship('Transaction', backref='customer_installment', lazy=True)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(20), nullable=False)
    amount = db.Column(db.Float, default=0.0)
    installment_type = db.Column(db.String(50)) # Full, Part, Booking, Installment Name, etc.
    bank_name = db.Column(db.String(100))
    transaction_id = db.Column(db.String(100))
    remarks = db.Column(db.Text)
    images = db.Column(db.Text) # Comma-separated paths
    
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    customer_installment_id = db.Column(db.Integer, db.ForeignKey('customer_installment.id'), nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

class PettyCashCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))

class PartyCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))

class PettyCash(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(20), nullable=False)
    description = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    type = db.Column(db.String(20), nullable=False) # 'Income' or 'Expense'
    amount = db.Column(db.Float, nullable=False)
    images = db.Column(db.Text) # Comma-separated filenames
    
    # Financial Integration
    voucher_id = db.Column(db.Integer, db.ForeignKey('voucher.id'), nullable=True)
    journal_entry_id = db.Column(db.Integer, db.ForeignKey('journal_entries.id'), nullable=True)
    contra_entry_id = db.Column(db.Integer, db.ForeignKey('contra_entry.id'), nullable=True)
    
    updated_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

class Bank(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bank_name = db.Column(db.String(100), nullable=False)
    branch = db.Column(db.String(100))
    account_holder_name = db.Column(db.String(100))
    joint_name = db.Column(db.String(100))
    fhp = db.Column(db.String(100)) # Father/Husband/Parent
    address = db.Column(db.String(255))
    city = db.Column(db.String(50))
    phone = db.Column(db.String(20))
    customer_id = db.Column(db.String(50)) # Bank's customer ID
    account_no = db.Column(db.String(50), nullable=False)
    prev_account_no = db.Column(db.String(50))
    account_type = db.Column(db.String(50)) # Savings, Current, etc.
    currency = db.Column(db.String(10))
    status = db.Column(db.String(20), default='Active') # Active/Inactive
    updated_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    
    
    transactions = db.relationship('BankTransaction', backref='bank', lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id': self.id,
            'bank_name': self.bank_name,
            'branch': self.branch,
            'account_holder_name': self.account_holder_name,
            'joint_name': self.joint_name,
            'fhp': self.fhp,
            'address': self.address,
            'city': self.city,
            'phone': self.phone,
            'customer_id': self.customer_id,
            'account_no': self.account_no,
            'prev_account_no': self.prev_account_no,
            'account_type': self.account_type,
            'currency': self.currency,
            'status': self.status
        }

class BankTransaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(20), nullable=False)
    cheque_no = db.Column(db.String(50))
    ref_no = db.Column(db.String(50))
    narration = db.Column(db.String(255))
    transaction_details = db.Column(db.String(255))
    debit = db.Column(db.Float, default=0.0)
    credit = db.Column(db.Float, default=0.0)
    balance = db.Column(db.Float, default=0.0) # Running balance at time of tx
    
    bank_id = db.Column(db.Integer, db.ForeignKey('bank.id'), nullable=False)
    
    # Financial Integration
    voucher_id = db.Column(db.Integer, db.ForeignKey('voucher.id'), nullable=True)
    contra_entry_id = db.Column(db.Integer, db.ForeignKey('contra_entry.id'), nullable=True)
    journal_entry_id = db.Column(db.Integer, db.ForeignKey('journal_entries.id'), nullable=True)
    category = db.Column(db.String(100), nullable=True) # Added for categorizing bank movements
    
    updated_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'date': self.date,
            'cheque_no': self.cheque_no,
            'ref_no': self.ref_no,
            'narration': self.narration,
            'transaction_details': self.transaction_details,
            'debit': self.debit,
            'credit': self.credit,
            'balance': self.balance,
            'bank_id': self.bank_id,
            'category': self.category
        }

class Party(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False) # Supplier, Contractor, Individual
    phone = db.Column(db.String(20))
    address = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    
    ledger_entries = db.relationship('PartyLedger', backref='party', lazy=True, cascade="all, delete-orphan")

    @property
    def current_balance(self):
        from sqlalchemy import func
        # Sum of bill_amount (Credit) - sum of paid_amount (Debit)
        # Note: In our system, positive = we owe them (Due), negative = they owe us (Advance)
        results = db.session.query(
            func.sum(PartyLedger.bill_amount), 
            func.sum(PartyLedger.paid_amount)
        ).filter(PartyLedger.party_id == self.id).first()
        
        bill_sum = results[0] or 0.0
        paid_sum = results[1] or 0.0
        return bill_sum - paid_sum

class PartyLedger(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    party_id = db.Column(db.Integer, db.ForeignKey('party.id'), nullable=False)
    date = db.Column(db.String(20), nullable=False)
    description = db.Column(db.String(255))
    bill_amount = db.Column(db.Float, default=0.0) # Credit
    paid_amount = db.Column(db.Float, default=0.0) # Debit
    balance = db.Column(db.Float, default=0.0) # Running balance
    reference = db.Column(db.String(100)) # Invoice/Memo No
    
    # Financial Integration
    voucher_id = db.Column(db.Integer, db.ForeignKey('voucher.id'), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

class Voucher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    voucher_no = db.Column(db.String(50), unique=True, nullable=False) # Editable
    type = db.Column(db.String(20), nullable=False) # 'Debit' or 'Credit'
    date = db.Column(db.String(20), nullable=False)
    
    party_id = db.Column(db.Integer, db.ForeignKey('party.id'), nullable=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=True)
    description = db.Column(db.Text)
    
    total_amount = db.Column(db.Float, default=0.0)
    amount_paid = db.Column(db.Float, default=0.0)
    due_amount = db.Column(db.Float, default=0.0)
    payment_percentage = db.Column(db.Float, default=0.0)
    
    payment_method = db.Column(db.String(20), nullable=False) # 'Cash' or 'Bank'
    bank_id = db.Column(db.Integer, db.ForeignKey('bank.id'), nullable=True)
    
    category = db.Column(db.String(100)) # e.g. "Salary", "Material", "Advance"
    notes = db.Column(db.Text)
    attachment = db.Column(db.String(255)) # Filename
    is_payment = db.Column(db.Boolean, default=False) # True if paying previous dues (no new bill)
    journal_entry_id = db.Column(db.Integer, db.ForeignKey('journal_entries.id'), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    # Relationships for easier access
    party_obj = db.relationship('Party', backref='vouchers', lazy=True)
    customer_obj = db.relationship('Customer', backref='vouchers', lazy=True)
    bank_obj = db.relationship('Bank', backref='vouchers', lazy=True)
    
    petty_cash_entries = db.relationship('PettyCash', backref='voucher', lazy=True, cascade="all, delete-orphan")
    bank_entries = db.relationship('BankTransaction', backref='voucher', lazy=True, cascade="all, delete-orphan")
    ledger_entries = db.relationship('PartyLedger', backref='voucher', lazy=True, cascade="all, delete-orphan")

class ContraEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    contra_no = db.Column(db.String(50), unique=True, nullable=False)
    date = db.Column(db.String(20), nullable=False)
    from_account = db.Column(db.String(20), nullable=False) # 'Cash' or 'Bank'
    to_account = db.Column(db.String(20), nullable=False)   # 'Cash' or 'Bank'
    bank_id = db.Column(db.Integer, db.ForeignKey('bank.id'), nullable=True) # Linked bank if from/to involves Bank
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text)
    cheque_no = db.Column(db.String(50))
    attachments = db.Column(db.Text) # Comma-separated filenames
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    # Financial Integration
    bank_obj = db.relationship('Bank', backref='contra_entries', lazy=True)
    petty_cash_entries = db.relationship('PettyCash', backref='contra_entry', lazy=True, cascade="all, delete-orphan")
    bank_entries = db.relationship('BankTransaction', backref='contra_entry', lazy=True, cascade="all, delete-orphan")

class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(50), default='General') # Work, Personal, etc.
    due_date = db.Column(db.String(20)) # Date for reminder
    due_time = db.Column(db.String(10)) # Time for reminder
    is_completed = db.Column(db.Boolean, default=False)
    reminder_sent = db.Column(db.Boolean, default=False) # To prevent duplicate alerts
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Relationship to User
    user = db.relationship('User', backref='todos', lazy=True)

# --- Employee Management Models ---

class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    designation = db.Column(db.String(100))
    department = db.Column(db.String(100))
    joining_date = db.Column(db.String(20))
    net_salary = db.Column(db.Float, default=0.0)
    phone = db.Column(db.String(20))
    
    # Leave Allocations (Yearly)
    cl_total = db.Column(db.Integer, default=10) # Casual Leave
    ml_total = db.Column(db.Integer, default=14) # Medical Leave
    fl_total = db.Column(db.Integer, default=0)  # Festival Leave
    el_total = db.Column(db.Integer, default=0)  # Earned Leave
    
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    # Relationships
    attendances = db.relationship('Attendance', backref='employee', lazy=True, cascade="all, delete-orphan")
    leaves = db.relationship('Leave', backref='employee', lazy=True, cascade="all, delete-orphan")
    salaries = db.relationship('Salary', backref='employee', lazy=True, cascade="all, delete-orphan")

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    date = db.Column(db.String(20), nullable=False)
    in_time = db.Column(db.String(20))
    out_time = db.Column(db.String(20))
    status = db.Column(db.String(20), nullable=False) # 'Present', 'Absent', 'Leave', 'Late'
    working_hours = db.Column(db.Float, default=0.0)
    notes = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

class Leave(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    leave_type = db.Column(db.String(20), nullable=False) # 'CL', 'ML', 'FL', 'EL'
    from_date = db.Column(db.String(20), nullable=False)
    to_date = db.Column(db.String(20), nullable=False)
    total_days = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='Approved') # 'Approved', 'Pending', 'Rejected'
    reason = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

class Salary(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    month = db.Column(db.String(20), nullable=False) # e.g. '03'
    year = db.Column(db.String(20), nullable=False) # e.g. '2026'
    
    net_salary = db.Column(db.Float, default=0.0)
    working_days = db.Column(db.Integer, default=0)
    present_days = db.Column(db.Integer, default=0)
    absent_days = db.Column(db.Integer, default=0)
    leave_days = db.Column(db.Integer, default=0)
    late_days = db.Column(db.Integer, default=0)
    off_days = db.Column(db.Integer, default=0)
    
    per_day_salary = db.Column(db.Float, default=0.0)
    deduction = db.Column(db.Float, default=0.0)
    mobile_bill = db.Column(db.Float, default=0.0)
    bonus = db.Column(db.Float, default=0.0)
    final_salary = db.Column(db.Float, default=0.0)
    
    status = db.Column(db.String(20), default='Unpaid') # 'Unpaid', 'Paid'
    payment_date = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))


class AccountCategory(db.Model):
    """Optional: To group accounts like 'Cash', 'Bank', 'Expense' for easier UI filtering"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    type = db.Column(db.String(20), nullable=False) # Asset, Liability, etc.

class Account(db.Model):
    __tablename__ = 'accounts'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(20), nullable=False) # Asset, Liability, Equity, Revenue, Expense
    parent_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    description = db.Column(db.String(255))
    
    # Hierarchy
    children = db.relationship('Account', backref=db.backref('parent', remote_side=[id]))
    ledger_lines = db.relationship('JournalEntryLine', backref='account', lazy=True)

class JournalEntry(db.Model):
    __tablename__ = 'journal_entries'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(20), nullable=False) # String for consistency with other models
    reference = db.Column(db.String(100)) # e.g. "VOU-DV-101"
    description = db.Column(db.Text)
    type = db.Column(db.String(50), default='Manual') # Manual, Automated, Voucher
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    
    lines = db.relationship('JournalEntryLine', backref='entry', lazy=True, cascade="all, delete-orphan")

class JournalEntryLine(db.Model):
    __tablename__ = 'journal_entry_lines'
    id = db.Column(db.Integer, primary_key=True)
    journal_entry_id = db.Column(db.Integer, db.ForeignKey('journal_entries.id'), nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    debit = db.Column(db.Float, default=0.0)
    credit = db.Column(db.Float, default=0.0)
    narration = db.Column(db.String(255))

class SystemSetting(db.Model):
    __tablename__ = 'system_settings'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.String(255), nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
