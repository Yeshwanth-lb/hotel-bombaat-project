from flask import Flask
from config import Config
from utils.db import init_db, mail # <-- Import mail from utils.db

# Import blueprints
from routes.main import main_bp
from routes.auth import auth_bp
from routes.booking import booking_bp
from routes.food import food_bp
from routes.payment import payment_bp
from routes.admin import admin_bp

def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize database & mail
    init_db(app) 
    # (mail.init_app is now handled inside init_db)

    # Register blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(booking_bp, url_prefix='/booking')
    app.register_blueprint(food_bp, url_prefix='/food')
    app.register_blueprint(payment_bp, url_prefix='/payment')
    app.register_blueprint(admin_bp, url_prefix='/admin') 

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5000)