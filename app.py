from flask import Flask
from database import db
from routes import main
import os

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(app.instance_path, "nexus.db")}'
    app.config['SECRET_KEY'] = 'dev-key-nexus-river-view'
    
    # Load Admin Config
    config_path = os.path.join(app.root_path, 'admin_config.json')
    if os.path.exists(config_path):
        import json
        with open(config_path, 'r') as f:
            config = json.load(f)
            app.config['ADMIN_PASSWORD'] = config.get('ADMIN_PASSWORD', '1234')
    else:
        app.config['ADMIN_PASSWORD'] = '1234' # Default Master Password

    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
    
    # Ensure upload folder exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    db.init_app(app)
    
    app.register_blueprint(main)
    
    with app.app_context():
        db.create_all()
        
    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
