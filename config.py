import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # ... (your other config is here) ...
    SECRET_KEY = os.environ.get('SECRET_KEY') or '...'
    MONGO_URI = os.environ.get('MONGO_URI') or '...'
    
    # Add these for Mail
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') is not None
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')