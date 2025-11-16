from flask import Flask
from flask_mail import Mail, Message
from dotenv import load_dotenv
import os

# Load .env
load_dotenv()

app = Flask(__name__)

# Config
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')

mail = Mail(app)

print(f"Attempting to send email from: {app.config['MAIL_USERNAME']}")

with app.app_context():
    try:
        msg = Message(
            subject="Bombaat Test Email (Retry)",
            sender=app.config['MAIL_USERNAME'],
            recipients=[app.config['MAIL_USERNAME']], # Sending to yourself
            body="If you see this, the connection is working!"
        )
        mail.send(msg)
        print("✅ SUCCESS! Email sent. Check your inbox.")
    except Exception as e:
        print(f"❌ FAILED: {e}")