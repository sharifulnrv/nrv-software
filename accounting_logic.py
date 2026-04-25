from datetime import datetime
from models import db, Account, JournalEntry, JournalEntryLine

class JournalManager:
    @staticmethod
    def post_balanced_entry(date, reference, description, lines, entry_type='Manual'):
        """
        lines: List of dicts [{'account_id': int, 'debit': float, 'credit': float, 'narration': str}]
        """
        total_debit = sum(line.get('debit', 0) for line in lines)
        total_credit = sum(line.get('credit', 0) for line in lines)
        
        if abs(total_debit - total_credit) > 0.01:
            raise ValueError(f"Unbalanced Entry: Total Debit ({total_debit}) != Total Credit ({total_credit})")
        
        entry = JournalEntry(
            date=date,
            reference=reference,
            description=description,
            type=entry_type
        )
        db.session.add(entry)
        db.session.flush() # Populate entry.id
        
        for line_data in lines:
            line = JournalEntryLine(
                journal_entry_id=entry.id,
                account_id=line_data['account_id'],
                debit=line_data.get('debit', 0.0),
                credit=line_data.get('credit', 0.0),
                narration=line_data.get('narration')
            )
            db.session.add(line)
        
        return entry

    @staticmethod
    def get_account_by_code(code):
        return Account.query.filter_by(code=code).first()

    @staticmethod
    def auto_post_voucher(voucher):
        """
        Automatically post a journal entry for a Debit/Credit Voucher.
        Handles total vs. paid amounts (Accrual logic).
        """
        if voucher.journal_entry_id:
            return None # Already posted
            
        # 1. Accounts Mapping
        cash_acc = JournalManager.get_account_by_code('1010')
        bank_acc = JournalManager.get_account_by_code('1200')
        ar_acc = JournalManager.get_account_by_code('1100') # Receivable
        ap_acc = JournalManager.get_account_by_code('2100') # Payable
        
        # Determine specific Bank if applicable
        pay_acc = bank_acc if voucher.payment_method == 'Bank' else cash_acc
        if voucher.payment_method == 'Bank' and voucher.bank_id:
            specific_bank = Account.query.filter_by(code=f"BANK_{voucher.bank_id}").first()
            if specific_bank: pay_acc = specific_bank

        # Determine Category Account
        cat_acc = Account.query.filter_by(name=voucher.category).first()
        if not cat_acc:
            default_code = 'DEFAULT_EXP' if voucher.type == 'Debit' else 'DEFAULT_REV'
            cat_acc = JournalManager.get_account_by_code(default_code)

        if not cat_acc or not pay_acc:
            return None # Missing critical accounts

        lines = []
        is_payout = (voucher.type == 'Debit')
        
        if voucher.is_payment:
            # SCENARIO: Paying/Receiving OLD dues (No new expense/income recognition)
            amt = voucher.amount_paid
            if amt <= 0: return None
            
            if is_payout:
                # We pay a supplier: DR Payable, CR Cash/Bank
                lines.append({'account_id': ap_acc.id, 'debit': amt, 'credit': 0.0, 'narration': f"Clearing dues: {voucher.description}"})
                lines.append({'account_id': pay_acc.id, 'debit': 0.0, 'credit': amt, 'narration': f"Payment via {voucher.payment_method}"})
            else:
                # We receive from customer: DR Cash/Bank, CR Receivable
                lines.append({'account_id': pay_acc.id, 'debit': amt, 'credit': 0.0, 'narration': f"Receipt via {voucher.payment_method}"})
                lines.append({'account_id': ar_acc.id, 'debit': 0.0, 'credit': amt, 'narration': f"Clearing dues: {voucher.description}"})
        else:
            # SCENARIO: New Bill/Receipt (Accrual Recognition)
            total = voucher.total_amount
            paid = voucher.amount_paid
            due = voucher.due_amount
            
            if is_payout:
                # Expense Recognition: DR Expense (Total), CR Cash (Paid), CR Payable (Due)
                lines.append({'account_id': cat_acc.id, 'debit': total, 'credit': 0.0, 'narration': voucher.description})
                if paid > 0:
                    lines.append({'account_id': pay_acc.id, 'debit': 0.0, 'credit': paid, 'narration': f"Cash/Bank Payment"})
                if due > 0:
                    lines.append({'account_id': ap_acc.id, 'debit': 0.0, 'credit': due, 'narration': f"Balance Due (Payable)"})
            else:
                # Revenue Recognition: DR Cash (Paid), DR Receivable (Due), CR Revenue (Total)
                if paid > 0:
                    lines.append({'account_id': pay_acc.id, 'debit': paid, 'credit': 0.0, 'narration': f"Cash/Bank Receipt"})
                if due > 0:
                    lines.append({'account_id': ar_acc.id, 'debit': due, 'credit': 0.0, 'narration': f"Balance Due (Receivable)"})
                lines.append({'account_id': cat_acc.id, 'debit': 0.0, 'credit': total, 'narration': voucher.description})

        if not lines: return None

        journal_entry = JournalManager.post_balanced_entry(
            date=voucher.date,
            reference=voucher.voucher_no,
            description=f"Auto-post: {voucher.type} Voucher {voucher.voucher_no}",
            lines=lines,
            entry_type='Automated'
        )
        
        voucher.journal_entry_id = journal_entry.id
        return journal_entry
    @staticmethod
    def sync_historical_data():
        """
        Retroactively scan the database and post missing journal entries for all historical data.
        """
        from models import CustomerInstallment, Transaction, Voucher, PettyCash, BankTransaction, ContraEntry
        
        # Mapping accounts
        receivable_acc = JournalManager.get_account_by_code('1100')
        revenue_acc = JournalManager.get_account_by_code('4100')
        cash_acc = JournalManager.get_account_by_code('1010')
        bank_acc = JournalManager.get_account_by_code('1200') # Default Bank
        
        if not receivable_acc or not revenue_acc:
            return "Required accounts (1100, 4100) missing. Please ensure COA is seeded."

        count = 0
        
        # --- 1. Installments (Revenue Recognition) ---
        # For accrual, the moment an installment is created/due, it's revenue.
        cis = CustomerInstallment.query.all()
        for ci in cis:
            # Check if we already have a journal for this. 
            # Since CI doesn't have journal_entry_id, we check if reference exists.
            ref = f"INST-{ci.id}"
            if JournalEntry.query.filter_by(reference=ref).first(): continue
            
            if ci.total_amount > 0:
                lines = [
                    {'account_id': receivable_acc.id, 'debit': ci.total_amount, 'credit': 0.0, 'narration': f"Installment Due: {ci.installment.name} for {ci.customer.name}"},
                    {'account_id': revenue_acc.id, 'debit': 0.0, 'credit': ci.total_amount, 'narration': f"Revenue identified for {ci.installment.name}"}
                ]
                JournalManager.post_balanced_entry(
                    date=datetime.now().strftime('%Y-%m-%d'), # Use current date or installment creation date if available
                    reference=ref,
                    description=f"Accrual: Installment {ci.installment.name} for Customer {ci.customer.name}",
                    lines=lines,
                    entry_type='Automated'
                )
                count += 1

        # --- 2. Transactions (Payment Collections) ---
        txs = Transaction.query.all()
        for tx in txs:
            ref = f"TX-{tx.id}"
            if JournalEntry.query.filter_by(reference=ref).first(): continue
            
            if tx.amount > 0:
                # Decide if Cash or Bank
                pay_acc = bank_acc if tx.bank_name else cash_acc
                
                lines = [
                    {'account_id': pay_acc.id, 'debit': tx.amount, 'credit': 0.0, 'narration': f"Collection from {tx.customer.name} - {tx.installment_type}"},
                    {'account_id': receivable_acc.id, 'debit': 0.0, 'credit': tx.amount, 'narration': f"Receivable cleared for {tx.customer.name}"}
                ]
                JournalManager.post_balanced_entry(
                    date=tx.date,
                    reference=ref,
                    description=f"Payment Collection: {tx.customer.name} ({tx.installment_type})",
                    lines=lines,
                    entry_type='Automated'
                )
                count += 1

        # --- 3. Vouchers (Expense/Receipts) ---
        vouchers = Voucher.query.filter_by(journal_entry_id=None).all()
        for v in vouchers:
            JournalManager.auto_post_voucher(v)
            count += 1

        # --- 4. Loose Petty Cash (Income/Expenses not in Vouchers) ---
        pc_entries = PettyCash.query.filter_by(journal_entry_id=None, voucher_id=None, contra_entry_id=None).all()
        for pc in pc_entries:
            JournalManager.auto_post_petty_cash(pc)
            count += 1

        # --- 5. Contra Entries ---
        contras = ContraEntry.query.all()
        for c in contras:
            # Check if reference exists
            ref = f"CON-{c.id}"
            if not JournalEntry.query.filter_by(reference=ref).first():
                JournalManager.auto_post_contra(c)
                count += 1

        # --- 6. Bank Transactions (Loose) ---
        bank_txs = BankTransaction.query.filter_by(journal_entry_id=None, voucher_id=None, contra_entry_id=None).all()
        for bt in bank_txs:
            if bt.debit == 0 and bt.credit == 0: continue
            
            # Map specific bank account if possible
            specific_bank_acc = Account.query.filter_by(code=f"BANK_{bt.bank_id}").first()
            pay_acc = specific_bank_acc or bank_acc
            
            # We assume loose bank transactions are either Revenue (if Credit) or Expense (if Debit)
            if bt.credit > 0:
                # Money in: Debit Bank, Credit Revenue
                lines = [
                    {'account_id': pay_acc.id, 'debit': bt.credit, 'credit': 0.0, 'narration': bt.narration},
                    {'account_id': JournalManager.get_account_by_code('DEFAULT_REV').id, 'debit': 0.0, 'credit': bt.credit, 'narration': "Misc Bank Receipt"}
                ]
            else:
                # Money out: Debit Expense, Credit Bank
                lines = [
                    {'account_id': JournalManager.get_account_by_code('DEFAULT_EXP').id, 'debit': bt.debit, 'credit': 0.0, 'narration': bt.narration},
                    {'account_id': pay_acc.id, 'debit': 0.0, 'credit': bt.debit, 'narration': "Misc Bank Payment"}
                ]
                
            entry = JournalManager.post_balanced_entry(
                date=bt.date,
                reference=f"BT-{bt.id}",
                description=f"Legacy Bank Tx: {bt.narration}",
                lines=lines,
                entry_type='Automated'
            )
            bt.journal_entry_id = entry.id
            count += 1
            
        return count
    @staticmethod
    def auto_post_petty_cash(pc):
        """Automatically post a journal entry for a Petty Cash entry."""
        if pc.journal_entry_id or pc.voucher_id or pc.contra_entry_id:
            return None
        if pc.amount <= 0: return None
        
        cash_acc = JournalManager.get_account_by_code('1010')
        cat_acc = Account.query.filter_by(name=pc.category).first()
        if not cat_acc:
            cat_acc = Account.query.filter_by(code='DEFAULT_EXP' if pc.type == 'Expense' else 'DEFAULT_REV').first()
        
        if not cash_acc or not cat_acc: return None
        
        if pc.type == 'Income':
            lines = [
                {'account_id': cash_acc.id, 'debit': pc.amount, 'credit': 0.0, 'narration': pc.description},
                {'account_id': cat_acc.id, 'debit': 0.0, 'credit': pc.amount, 'narration': f"Petty Cash Income: {pc.category}"}
            ]
        else:
            lines = [
                {'account_id': cat_acc.id, 'debit': pc.amount, 'credit': 0.0, 'narration': pc.description},
                {'account_id': cash_acc.id, 'debit': 0.0, 'credit': pc.amount, 'narration': f"Petty Cash Expense: {pc.category}"}
            ]
            
        entry = JournalManager.post_balanced_entry(
            date=pc.date,
            reference=f"PC-{pc.id}",
            description=f"Petty Cash: {pc.description}",
            lines=lines,
            entry_type='Automated'
        )
        pc.journal_entry_id = entry.id
        return entry

    @staticmethod
    def auto_post_contra(c):
        """Automatically post a journal entry for a Contra Entry."""
        # Check if already posted by reference to be safe
        ref = f"CON-{c.id}"
        from models import JournalEntry
        if JournalEntry.query.filter_by(reference=ref).first():
            return None
            
        cash_acc = JournalManager.get_account_by_code('1010')
        bank_acc = JournalManager.get_account_by_code('1200')
        
        # From Account
        from_acc = cash_acc if c.from_account == 'Cash' else bank_acc
        # To Account
        to_acc = cash_acc if c.to_account == 'Cash' else bank_acc
        
        if c.from_account == 'Bank' and c.bank_id:
            specific = Account.query.filter_by(code=f"BANK_{c.bank_id}").first()
            if specific: from_acc = specific
        if c.to_account == 'Bank' and c.bank_id:
            specific = Account.query.filter_by(code=f"BANK_{c.bank_id}").first()
            if specific: to_acc = specific

        lines = [
            {'account_id': to_acc.id, 'debit': c.amount, 'credit': 0.0, 'narration': f"Transfer to {c.to_account}"},
            {'account_id': from_acc.id, 'debit': 0.0, 'credit': c.amount, 'narration': f"Transfer from {c.from_account}"}
        ]
        
        entry = JournalManager.post_balanced_entry(
            date=c.date,
            reference=ref,
            description=f"Contra: {c.description}",
            lines=lines,
            entry_type='Automated'
        )
        return entry

    @staticmethod
    def auto_post_transaction(tx):
        """
        Automatically post a journal entry for a customer payment (Transaction).
        Debit: Cash/Bank, Credit: Accounts Receivable
        """
        # Mapping accounts
        receivable_acc = JournalManager.get_account_by_code('1100')
        cash_acc = JournalManager.get_account_by_code('1010')
        bank_acc = JournalManager.get_account_by_code('1200')
        
        if not receivable_acc:
            return None

        # Determine payment account
        # If tx.bank_name contains 'Bank' or isn't empty, use bank_acc, else cash_acc
        pay_acc = bank_acc if tx.bank_name and 'Cash' not in tx.bank_name else cash_acc

        lines = [
            {'account_id': pay_acc.id, 'debit': tx.amount, 'credit': 0.0, 'narration': f"Collection from {tx.customer.name} - {tx.installment_type}"},
            {'account_id': receivable_acc.id, 'debit': 0.0, 'credit': tx.amount, 'narration': f"Receivable cleared for {tx.customer.name}"}
        ]
        
        journal_entry = JournalManager.post_balanced_entry(
            date=tx.date,
            reference=f"TX-{tx.id}",
            description=f"Automated Payment Receipt: {tx.customer.name}",
            lines=lines,
            entry_type='Automated'
        )
        return journal_entry
