from flask import Flask, request, redirect, url_for
from flask_login import LoginManager
from database import db
from routes import main
import os
import sys
import logging
from dotenv import load_dotenv

# Load .env — works both in dev mode and when bundled as a PyInstaller exe
if getattr(sys, 'frozen', False):
    # Running as compiled exe: .env is extracted to the temp _MEIPASS folder
    _env_path = os.path.join(sys._MEIPASS, '.env')
else:
    _env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
load_dotenv(_env_path)

# Setup Logging
def setup_logging(data_dir):
    log_file = os.path.join(data_dir, 'nexus_startup.log')
    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)

def create_app():
    # precise determination of data_dir path
    data_dir = os.environ.get('NEXUS_DATA_PATH')
    if not data_dir: # Corrected the variable name
         data_dir = os.getenv('NEXUS_DATA_PATH', '.')
    
    if getattr(sys, 'frozen', False):
        if not data_dir or data_dir == '.':
            base_path = os.path.dirname(sys.executable)
            data_dir = base_path
    else:
        # Resolve any relative paths to absolute
        data_dir = os.path.abspath(data_dir)
            
    # Ensure data_dir exists before setting up logging
    os.makedirs(data_dir, exist_ok=True)
            
    # Ensure data_dir exists before setting up logging
    os.makedirs(data_dir, exist_ok=True)
    
    logger = setup_logging(data_dir)
    logger.info(f"Application starting with data_dir: {data_dir}")

    if getattr(sys, 'frozen', False):
        # When running as EXE, resources are in sys._MEIPASS
        template_folder = os.path.join(sys._MEIPASS, 'templates')
        static_folder = os.path.join(sys._MEIPASS, 'static')
        app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
    else:
        app = Flask(__name__)

    # DB Path
    db_path = os.path.join(data_dir, 'nexus.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['DATA_FOLDER'] = data_dir 
    app.config['DATABASE_PATH'] = db_path 
    app.config['SECRET_KEY'] = 'dev-key-nexus-river-view'
    
    # Load Admin Config from Environment
    app.config['ADMIN_PASSWORD'] = os.environ.get('ADMIN_PASSWORD', '1234')

    # Upload Folder
    app.config['UPLOAD_FOLDER'] = os.path.join(data_dir, 'uploads')
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    db.init_app(app)
    
    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.login_view = 'main.login'
    login_manager.init_app(app)

    from models import User
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))
        
    app.register_blueprint(main)
    
    # Startup Sync & DB Check (Run in background thread to prevent GUI/Startup hang)
    from sync_manager import sync_manager
    
    def run_startup_sync(app_to_sync, logger_to_use, db_path_to_use):
        with app_to_sync.app_context():
            # Ensure tables exist
            try:
                db.create_all()
                logger_to_use.info("Database tables verified/created.")
                
                # Setup Initial Data
                from models import User, Account
                
                # 1. Admin User
                if not User.query.filter_by(username='admin').first():
                    admin = User(username='admin')
                    pwd = app_to_sync.config.get('ADMIN_PASSWORD', '1234')
                    admin.set_password(pwd)
                    db.session.add(admin)
                    db.session.commit()
                    logger_to_use.info("Default admin user created.")
                
                # 2. Chart of Accounts
                logger_to_use.info("Verifying Chart of Accounts...")
                initial_accounts = [
                    # Assets
                    {'code': '1000', 'name': 'Assets', 'type': 'Asset'},
                    {'code': '1010', 'name': 'Cash in Hand', 'type': 'Asset', 'parent_code': '1000'},
                    {'code': '1100', 'name': 'Accounts Receivable', 'type': 'Asset', 'parent_code': '1000'},
                    {'code': '1200', 'name': 'Bank Accounts', 'type': 'Asset', 'parent_code': '1000'},
                    # Liabilities
                    {'code': '2000', 'name': 'Liabilities', 'type': 'Liability'},
                    {'code': '2100', 'name': 'Accounts Payable', 'type': 'Liability', 'parent_code': '2000'},
                    # Equity
                    {'code': '3000', 'name': 'Equity', 'type': 'Equity'},
                    {'code': '3100', 'name': 'Share Capital', 'type': 'Equity', 'parent_code': '3000'},
                    {'code': '3200', 'name': 'Retained Earnings', 'type': 'Equity', 'parent_code': '3000'},
                    # Revenue
                    {'code': '4000', 'name': 'Revenue', 'type': 'Revenue'},
                    {'code': '4100', 'name': 'Sales/Installments', 'type': 'Revenue', 'parent_code': '4000'},
                    # Expenses
                    {'code': '5000', 'name': 'Expenses', 'type': 'Expense'},
                    {'code': '5100', 'name': 'Administrative Expenses', 'type': 'Expense', 'parent_code': '5000'},
                    {'code': '5200', 'name': 'Operational Expenses', 'type': 'Expense', 'parent_code': '5000'},
                    {'code': 'DEFAULT_EXP', 'name': 'Uncategorized Expense', 'type': 'Expense', 'parent_code': '5000'},
                    {'code': 'DEFAULT_REV', 'name': 'Uncategorized Revenue', 'type': 'Revenue', 'parent_code': '4000'},
                ]
                
                # Create missing accounts
                seeded_any = False
                for acc_data in initial_accounts:
                    if not Account.query.filter_by(code=acc_data['code']).first():
                        acc = Account(code=acc_data['code'], name=acc_data['name'], type=acc_data['type'])
                        db.session.add(acc)
                        seeded_any = True
                
                if seeded_any:
                    db.session.commit()
                    # Set parents
                    for acc_data in initial_accounts:
                        if 'parent_code' in acc_data:
                            parent = Account.query.filter_by(code=acc_data['parent_code']).first()
                            child = Account.query.filter_by(code=acc_data['code']).first()
                            if parent and child and not child.parent_id:
                                child.parent_id = parent.id
                    db.session.commit()
                    logger_to_use.info("Chart of Accounts verified/updated.")

            except Exception as e:
                logger_to_use.error(f"Initialization or Seeding failed: {e}")
                db.session.rollback()

            if not os.path.exists(db_path_to_use) or os.path.getsize(db_path_to_use) == 0:
                logger_to_use.info("Database missing. Attempting recovery from Google Sheets...")
                try:
                    success, msg = sync_manager.restore_db_from_sheets()
                    if success:
                        logger_to_use.info("Database restored from Google Sheets.")
                    else:
                        logger_to_use.error(f"Recovery failed: {msg}")
                except Exception as e:
                    logger_to_use.error(f"Recovery hang/error: {e}")
            else:
                logger_to_use.info("Database found. Skipping heavy startup sync for performance.")
                # We skip check_for_mismatches and sync_to_sheets here.
                # Background sync will happen normally after first user action if enabled.
            
            # --- Added Telegram Backup on Startup (Safe Direct Call) ---
            try:
                db_path = app_to_sync.config.get('DATABASE_PATH')
                if db_path and os.path.exists(db_path):
                    from telegram_utils import send_telegram_document
                    from datetime import datetime
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    caption = f"DB Backup triggered by: Application Startup\nTime: {timestamp}"
                    send_telegram_document(db_path, caption=caption)
                
                # --- NEW: Automated Local Backup Cleanup (30 Days) ---
                from logic import cleanup_old_backups
                cleanup_old_backups(days=30)
                
            except Exception as e:
                logger_to_use.error(f"Startup tasks (backup/cleanup) failed: {e}")

    @app.context_processor
    def inject_company_settings():
        company_name = os.environ.get('COMPANY_NAME', 'Company Name')
        company_address = os.environ.get('COMPANY_ADDRESS', '')
        return dict(global_company_name=company_name, global_company_address=company_address)

    import threading
    sync_thread = threading.Thread(target=run_startup_sync, args=(app, logger, db_path))
    sync_thread.daemon = True
    sync_thread.start()
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='127.0.0.1', port=5001, use_reloader=True,debug=True)
