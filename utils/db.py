from flask_pymongo import PyMongo
from flask_mail import Mail

# --- Create all extension instances ---
mongo = PyMongo()
mail = Mail()
# (The serializer is GONE from this file)
# -------------------------------------

def init_db(app):
    """
    Initializes all extensions with the Flask app.
    """
    
    # Initialize mongo and mail
    mongo.init_app(app)
    mail.init_app(app)
    
    return mongo