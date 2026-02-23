from flask import Flask
from database import db
from routes import main
import os
import sys
import logging

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
    app = Flask(__name__)

    # precise determination of the application path
    # If run_gui.py set the environment variable, we use that as the source of truth for DATA.
    data_dir = os.environ.get('NEXUS_DATA_PATH')
    
    if not data_dir:
        # Fallback logic (Dev mode or standalone run without launcher)
        if getattr(sys, 'frozen', False):
            base_path = os.path.dirname(sys.executable)
            data_dir = base_path
        else:
            base_path = app.root_path
            data_dir = app.instance_path
    
    logger = setup_logging(data_dir)
    logger.info("Application starting...")

    # DB Path
    # Always put DB in the determined data_dir
    db_path = os.path.join(data_dir, 'nexus.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['DATA_FOLDER'] = data_dir # Expose for other modules
    app.config['DATABASE_PATH'] = db_path # Expose DB path for backups
        
    app.config['SECRET_KEY'] = 'dev-key-nexus-river-view'
    
    # Load Admin Config
    # Priority: Data Dir > Bundled
    
    # 1. Try Data Dir
    external_config_path = os.path.join(data_dir, 'admin_config.json')
    # 2. Try bundled (inside _MEI... or source root)
    bundled_config_path = os.path.join(app.root_path, 'admin_config.json')
    
    config_loaded = False
    
    if os.path.exists(external_config_path):
        try:
            import json
            with open(external_config_path, 'r') as f:
                config = json.load(f)
                app.config['ADMIN_PASSWORD'] = config.get('ADMIN_PASSWORD', '1234')
            config_loaded = True
        except:
             pass # Fallback
    
    # Auto-generate if missing in data_dir
    if not config_loaded:
        # If we have a bundled one, try to read it first to get default
        default_password = '1234'
        if os.path.exists(bundled_config_path):
             try:
                import json
                with open(bundled_config_path, 'r') as f:
                    config = json.load(f)
                    default_password = config.get('ADMIN_PASSWORD', '1234')
             except:
                 pass
        
        # Write to data_dir
        try:
            import json
            with open(external_config_path, 'w') as f:
                json.dump({"ADMIN_PASSWORD": default_password}, f)
            app.config['ADMIN_PASSWORD'] = default_password
        except Exception as e:
            print(f"Failed to auto-create config: {e}")
            app.config['ADMIN_PASSWORD'] = default_password # Fallback in memory

    if 'ADMIN_PASSWORD' not in app.config:
        app.config['ADMIN_PASSWORD'] = '1234' # Default Master Password

    # Upload Folder
    # Put uploads in data_dir/uploads
    app.config['UPLOAD_FOLDER'] = os.path.join(data_dir, 'uploads')
    
    # Ensure upload folder exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    db.init_app(app)
    
    app.register_blueprint(main)
    
    with app.app_context():
        db.create_all()
        # Startup Sync Check
        from sync_manager import sync_manager
        db_path = app.config.get('DATABASE_PATH')
        
        if not os.path.exists(db_path) or os.path.getsize(db_path) == 0:
            print("Database missing. Attempting recovery from Google Sheets...")
            success, msg = sync_manager.restore_db_from_sheets()
            if success:
                print("Database restored from Google Sheets.")
            else:
                print(f"Recovery failed: {msg}")
        else:
            # Check for mismatches
            status, details = sync_manager.check_for_mismatches()
            if status == "mismatch":
                app.config['SYNC_MISMATCH'] = details
                print(f"Sync Mismatch Detected: {details}")
            elif status == "empty_sheets":
                print("Google Sheets is empty. Initializing with local data...")
                sync_manager.sync_to_sheets()
        
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
