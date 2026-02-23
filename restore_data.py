import sqlite3
from datetime import datetime
from routes import recompute_bank_balances
from app import create_app

app = create_app()

# Data from user (parsed from text)
# Fields: date, cheque_no, ref_no, narration, debit, credit, bank_id, transaction_details
raw_data = [
    ("10/12/2025", None, "8.42534E+15", "Trn. Br: 084 Cash Deposit", 0, 1000, 1, "Cash Deposit"),
    ("18-12-2025", None, "1.38254E+16", "Trn. Br: 138 Cash Deposit", 0, 50000, 1, "Cash Deposit"),
    ("22-12-2025", None, "084CHBK253510006", "Trn. Br: 084", 300, 0, 1, "Cheque Issuance"),
    ("22-12-2025", None, "084CHBK253510006", "Trn. Br: 084", 45, 0, 1, "Value Added Tax"),
    ("31-12-2025", None, "084RSGNBDT000001", "Trn. Br: 084 Related Account: 0843201000809046", 0, 0.58, 1, "Credit Interest"),
    ("31-12-2025", None, "084RSGNBDT000002", "Trn. Br: 084 Related Account: 0843201000809046", 0.09, 0, 1, "Tax"),
    ("14-01-2026", "1655546", "8.42601E+15", "Trn. Br: 084 Cheque Withdrawal", 30000, 0, 1, "Cheque Withdrawal"),
    ("19-01-2026", None, "2.60196E+12", "Trn. Br: 000 000245******0000 IBBLOMNI 000840207655", 0, 50000, 1, "Atm Bill Payment / Ft"),
    ("20-01-2026", None, "2.60196E+12", "Trn. Br: 000 000245******0000 90001000 000840527911", 0, 200000, 1, "Atm Bill Payment / Ft"),
    ("20-01-2026", None, "2.60196E+12", "Trn. Br: 000 000245******0000 90001000 000840528466", 0, 200000, 1, "Atm Bill Payment / Ft"),
    ("20-01-2026", None, "084EI19012696822", "Trn. Br: 084 MDAJIJUR RAHMAN 0100200190160 DILHARMIN-ID: B13526019X772010 _JANATA BANK LTD..HEAD OFFICE", 0, 100000, 1, "Beftn Inward Credit"),
    ("20-01-2026", None, "084EI19012696819", "Trn. Br: 084 MDAJIJUR RAHMAN 0100200190160 AJIJUR RAHMAN-ID: B13526019U261582 _JANATA BANK LTD..HEAD OFFICE", 0, 100000, 1, "Beftn Inward Credit"),
    ("20-01-2026", None, "RGI8260120695338", "Trn. Br: 084 JANBBDDH, DHAKA COLLEGE GATE, MD MOHIDUL ISLAM - Nexus River View", 0, 200000, 1, "Rtgs Inward"),
    ("20-01-2026", None, "2.60206E+12", "Trn. Br: 000 000245******0000 IBBLOMNI 000840708177", 0, 50000, 1, "Atm Bill Payment / Ft"),
    ("20-01-2026", None, "2.60206E+12", "Trn. Br: 000 000245******0000 61000765 000840714780", 0, 200000, 1, "Atm Bill Payment / Ft"),
    ("20-01-2026", None, "RGI8260120696184", "Trn. Br: 084 BSONBDDH, BUET Branch, Aparna Bali - INTELECT", 0, 200000, 1, "Rtgs Inward"),
    ("20-01-2026", None, "2.60206E+12", "Trn. Br: 000 000245******0000 NPSBIBFT 000841001652", 0, 200000, 1, "Atm Bill Payment / Ft"),
    ("20-01-2026", None, "IB26012064855472", "Trn. Br: 120 IB(Unet) Nexus Riverview Payment", 0, 200000, 1, "Banking Fund Transfer - Credit"),
    ("21-01-2026", None, "2.60216E+12", "Trn. Br: 000 000245******0000 00600009 000841231133", 0, 100000, 1, "Atm Bill Payment / Ft"),
    ("21-01-2026", None, "RGI8260121697499", "Trn. Br: 084 AGBKBDDH, JATIYA PRESS CLUB, MD ATAUR RAHMAN CHOWDHURY - PAYMENT - SCCT", 0, 100000, 1, "Rtgs Inward"),
    ("21-01-2026", None, "RGI8260121698331", "Trn. Br: 084 IBBLBDDH, UTTARA, Shahidul Islam -", 0, 100000, 1, "Rtgs Inward"),
    ("22-01-2026", None, "2.60226E+12", "Trn. Br: 000 000245******0000 00600009 000842082313", 0, 100000, 1, "Atm Bill Payment / Ft"),
    ("25-01-2026", None, "RGI8260125702253", "Trn. Br: 084 IBBLBDDH, FENI, MOHAMMED JAHIR ULLAH -", 0, 200000, 1, "Rtgs Inward"),
    ("26-01-2026", "7352369", "2.6026E+15", "Trn. Br: 084 ISLAMI BANK BANGLDESH LTD., AGENT BANKING Related Account: 0843201000809046", 0, 100000, 1, "Outward Clearing"),
    ("26-01-2026", "7352369", "2.6026E+15", "Trn. Br: 084 ISLAMI BANK BANGLDESH LTD., AGENT BANKING Related Account: 0843201000809046", 10, 0, 1, "Outward Clearing Charge"),
    ("26-01-2026", None, "IB26012613481562", "Trn. Br: 777 IB(Unet) pay", 0, 200000, 1, "Banking Fund Transfer - Credit"),
    ("28-01-2026", None, "084EI27012672250", "Trn. Br: 084 SUMIYA BINTE SHAHID 2706101119862 Alimuzzman-ID: B17526027A326697 _Pubali Bank PLC, TRUNCATION POINT", 0, 90000, 1, "Beftn Inward Credit"),
    ("28-01-2026", None, "084EI27012672758", "Trn. Br: 084 ALIMUZZAMAN 1161030187123 Alimuzzman-ID: B09026027A030590 _Dutch-Bangla Bank PLC,LOCAL OFFICE", 0, 110000, 1, "Beftn Inward Credit"),
    ("28-01-2026", None, "084EI27012672399", "Trn. Br: 084 SUSMITA DAS 0100007463043 1st Installment N-ID: B13526027O074980 _JANATA BANK LTD..HEAD OFFICE", 0, 100000, 1, "Beftn Inward Credit"),
    ("28-01-2026", None, "2.60286E+12", "Trn. Br: 000 000245******0000 90001000 000845920253", 0, 100000, 1, "Atm Bill Payment / Ft"),
    ("31-01-2026", None, "EB26013143518294", "Trn. Br: 786 EB (Unet)businesses", 0, 300000, 1, "Banking Fund Transfer - Credit"),
    ("31-01-2026", None, "EB26013125395914", "Trn. Br: 786 EB (Unet)Business", 0, 100000, 1, "Banking Fund Transfer - Credit"),
    ("02-02-2026", None, None, "", 80000, 0, 1, "Cheque Issuance"),
    ("05-02-2026", None, None, "RTGS", 0, 100000, 1, "Abdul Aziz REFF Sahadat"),
    ("09-02-2026", None, None, "Banking Fund Transfer - Credit", 0, 200000, 1, "Samsul Alam REF AK Azad"),
    ("10-02-2026", "1655548", None, "For Salary and Rent", 26500, 0, 1, "Cheque Issuance"),
    ("16-02-2026", None, "AGBK****10449", "Banking Fund Transfer - Credit", 0, 100000, 1, "Mrs. Shahina Reff: AK Azad"),
    ("16-02-2026", None, "AGBK****10449", "Cash Deposit", 0, 200000, 1, "Hasina Sikha Ref; Anowar Khan"),
    ("17-02-2026", None, "AGBK****10449", "Banking Fund Transfer - Credit", 0, 200000, 1, "Ibrahim Molla Ref Giash Uddin")
]

conn = sqlite3.connect('instance/nexus.db')
cursor = conn.cursor()

def normalize_date(d):
    # Convert input to DD-MM-YYYY
    # Handle / or -
    d = d.replace('/', '-')
    try:
        dt = datetime.strptime(d, '%d-%m-%Y')
        return dt.strftime('%d-%m-%Y')
    except ValueError:
        return d # Fallback

print("Inserting data...")
for row in raw_data:
    date_str, cheque, ref, narr, deb, cred, bid, details = row
    
    # Normalize Date
    norm_date = normalize_date(date_str)
    
    cursor.execute('''
        INSERT INTO bank_transaction (date, cheque_no, ref_no, narration, debit, credit, balance, bank_id, transaction_details)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (norm_date, cheque, ref, narr, deb, cred, 0, bid, details))

conn.commit()
conn.close()

# Use app context to recompute
with app.app_context():
    recompute_bank_balances(1)

print("Restoration Complete.")
