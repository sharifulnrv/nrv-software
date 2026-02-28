from database import db
from datetime import datetime

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
    payment_history = db.Column(db.Text) # Date & Deposit text blob
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


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
    
    director_id = db.Column(db.Integer, db.ForeignKey('director.id'), nullable=False)
    
    transactions = db.relationship('Transaction', backref='customer', lazy=True, cascade="all, delete-orphan")

    # New Fields
    father_name = db.Column(db.String(100))
    mother_name = db.Column(db.String(100))
    dob = db.Column(db.String(20)) # Date of Birth
    religion = db.Column(db.String(50))
    profession = db.Column(db.String(100))
    nid_no = db.Column(db.String(50))
    present_address = db.Column(db.String(255))
    permanent_address = db.Column(db.String(255))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

Director.customers = db.relationship('Customer', backref='director', lazy=True, order_by=Customer.customer_id)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(20), nullable=False)
    amount = db.Column(db.Float, default=0.0)
    installment_type = db.Column(db.String(50)) # Full, Part, Booking, etc.
    bank_name = db.Column(db.String(100))
    transaction_id = db.Column(db.String(100))
    remarks = db.Column(db.Text)
    images = db.Column(db.Text) # Comma-separated paths
    
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class PettyCash(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(20), nullable=False)
    description = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    type = db.Column(db.String(20), nullable=False) # 'Income' or 'Expense'
    amount = db.Column(db.Float, nullable=False)
    images = db.Column(db.Text) # Comma-separated filenames
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

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
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    
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
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

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
            'bank_id': self.bank_id
        }
