import datetime
import os
import uuid
from flask import Blueprint, render_template, session, flash, request, redirect, url_for, jsonify, current_app
from utils.db import mongo
from functools import wraps
from werkzeug.utils import secure_filename

main_bp = Blueprint('main', __name__)

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Decorator for login protection ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_email' not in session:
            flash('You must be logged in to view this page.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

# --- Static Routes ---
@main_bp.route('/')
def index():
    return render_template('index.html')

@main_bp.route('/gallery')
def gallery():
    return render_template('gallery.html')

# --- Dashboard ---
@main_bp.route('/dashboard')
@login_required
def dashboard():
    user_email = session['user_email']
    user = mongo.db.users.find_one({'email': user_email})
    loyalty_points = user.get('loyalty_points', 0)

    active_bookings = mongo.db.bookings.count_documents({
        'user_email': user_email,
        'status': 'active'
    })
    food_orders_count = mongo.db.food_orders.count_documents({
        'user_email': user_email
    })
    total_spent_bookings = sum(b.get('total_cost', 0) for b in mongo.db.bookings.find(
        {'user_email': user_email, 'payment_status': 'paid'}
    ))
    total_spent_food = sum(f.get('total_cost', 0) for f in mongo.db.food_orders.find(
        {'user_email': user_email, 'payment_status': 'paid'}
    ))
    total_spent = total_spent_bookings + total_spent_food

    stats = {
        'active_bookings': active_bookings,
        'food_orders': food_orders_count,
        'total_spent': round(total_spent, 0),
        'loyalty_points': loyalty_points
    }
    return render_template('dashboard.html', stats=stats)

# --- Reviews (FIXED Image Upload!) ---
@main_bp.route('/reviews', methods=['GET', 'POST'])
def reviews():
    if request.method == 'POST':
        if 'user_email' not in session:
            flash('You must be logged in to submit a review.', 'warning')
            return redirect(url_for('auth.login'))

        image_filename = None
        if 'review_image' in request.files:
            file = request.files['review_image']
            if file and file.filename != '' and allowed_file(file.filename):
                
                original_name = secure_filename(file.filename)
                unique_name = f"{uuid.uuid4().hex}_{original_name}"
                
                save_folder = os.path.join(current_app.root_path, UPLOAD_FOLDER)
                full_save_path = os.path.join(save_folder, unique_name)

                os.makedirs(save_folder, exist_ok=True)
                file.save(full_save_path)
                image_filename = unique_name

        mongo.db.reviews.insert_one({
            'user_email': session['user_email'],
            'username': session['username'],
            'rating': int(request.form['rating']),
            'review_type': request.form['review_type'],
            'comment': request.form['comment'],
            'image_file': image_filename,
            'created_at': datetime.datetime.now(datetime.timezone.utc)
        })
        flash('Thank you for your review!', 'success')
        return redirect(url_for('main.reviews'))
    
    all_reviews = list(mongo.db.reviews.find().sort('created_at', -1))
    return render_template('reviews.html', reviews=all_reviews)

# --- Contact Form ---
@main_bp.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        mongo.db.contacts.insert_one({
            'name': request.form['name'],
            'email': request.form['email'],
            'subject': request.form['subject'],
            'message': request.form['message'],
            'submitted_at': datetime.datetime.now(datetime.timezone.utc)
        })
        flash('Your message has been sent. We will get back to you soon.', 'success')
        return redirect(url_for('main.contact'))
    return render_template('contact.html')

# --- Admin Maker ---
@main_bp.route('/make-me-admin-12345')
@login_required
def make_me_admin():
    user_email = session.get('user_email')
    if not user_email: return redirect(url_for('main.dashboard'))
    user = mongo.db.users.find_one({'email': user_email})
    if not user: return redirect(url_for('main.dashboard'))
    if user.get('is_admin', False):
        flash('You are already an admin.', 'info')
        session['is_admin'] = True 
        return redirect(url_for('main.dashboard'))
    mongo.db.users.update_one({'email': user_email}, {'$set': {'is_admin': True}})
    flash('You have been successfully made an admin.', 'success')
    session['is_admin'] = True 
    return redirect(url_for('main.dashboard'))

# -----------------------------------------
# FEATURE: ROBOT BOMBAAT (Professional Version)
# -----------------------------------------
@main_bp.route('/chatbot', methods=['POST'])
def chatbot():
    data = request.get_json()
    user_msg = data.get('message', '').lower()
    
    # Default response if nothing matches
    bot_reply = "I'm sorry, I don't understand that. Please ask about rooms, food, check-in times, or our location."

    # --- 1. GREETINGS & BASICS ---
    if any(x in user_msg for x in ['hello', 'hi', 'hey', 'namaskara']):
        bot_reply = "ನಮಸ್ಕಾರ! (Namaskara!) Welcome to Hotel Bombaat. How can I assist you today?"
    
    elif 'who are you' in user_msg or 'your name' in user_msg:
        bot_reply = "I am Robot Bombaat, your virtual assistant for the hotel."
    
    elif 'how are you' in user_msg:
        bot_reply = "I am functioning well, thank you! How may I help you?"

    # --- 2. ROOMS & BOOKING ---
    elif any(x in user_msg for x in ['room', 'price', 'cost', 'rate', 'tariff']):
        bot_reply = "We have five room types, from Standard (₹1500) to Presidential Suite (₹15000). Please see the 'Book Room' page for details."
    
    elif 'book' in user_msg or 'reservation' in user_msg:
        bot_reply = "You can book a room by clicking the 'Book Room' button in the main menu and selecting your dates."
    
    elif 'ac' in user_msg or 'air condition' in user_msg:
        bot_reply = "Yes, all our rooms are fully air-conditioned for your comfort."
    
    elif 'extra bed' in user_msg or 'mattress' in user_msg:
        bot_reply = "Yes, an extra mattress can be provided for a nominal fee. Please contact the front desk."

    # --- 3. FOOD & DINING ---
    elif any(x in user_msg for x in ['food', 'hungry', 'restaurant', 'eat', 'dinner', 'lunch']):
        bot_reply = "We offer a multi-cuisine menu (North Indian, South Indian, etc.). You can order from the 'Order Food' section in your dashboard."
    
    elif 'breakfast' in user_msg or 'tiffin' in user_msg:
        bot_reply = "Our complimentary breakfast buffet is served from 7:00 AM to 10:30 AM."
    
    elif 'coffee' in user_msg or 'tea' in user_msg:
        bot_reply = "We have 24/7 room service for beverages, including excellent South Indian filter coffee."
    
    elif 'veg' in user_msg or 'vegetarian' in user_msg:
        bot_reply = "Yes, we have a wide variety of vegetarian (ಶುದ್ಧ ಸಸ್ಯಾಹಾರಿ) options and a separate vegetarian-friendly kitchen."

    elif 'bar' in user_msg or 'alcohol' in user_msg or 'beer' in user_msg:
        bot_reply = "Yes, our Rooftop Lounge serves a full selection of cocktails, mocktails, and other beverages."

    # --- 4. AMENITIES ---
    elif 'pool' in user_msg or 'swim' in user_msg:
        bot_reply = "Yes, we have a beautiful infinity pool on the terrace, open from 6 AM to 10 PM."
    
    elif 'gym' in user_msg or 'fitness' in user_msg or 'workout' in user_msg:
        bot_reply = "Our fitness center is open 24/7 and is fully equipped for all your workout needs."
    
    elif 'wifi' in user_msg or 'internet' in user_msg:
        bot_reply = "We offer complimentary high-speed Wi-Fi (500 Mbps). The password is 'Bombaat123'."
    
    elif 'parking' in user_msg or 'car' in user_msg:
        bot_reply = "Yes, we offer complimentary and secure basement parking for all our guests."
    
    elif 'laundry' in user_msg or 'wash' in user_msg:
        bot_reply = "We provide same-day laundry and dry-cleaning services. You can find the laundry bag in your room closet."

    # --- 5. POLICIES ---
    elif 'check-in' in user_msg or 'check in' in user_msg:
        bot_reply = "Our standard check-in time is **12:00 PM**."
    
    elif 'check-out' in user_msg or 'check out' in user_msg:
        bot_reply = "Our standard check-out time is **11:00 AM**."
    
    elif 'cancel' in user_msg or 'refund' in user_msg:
        bot_reply = "You can cancel active bookings from your 'My Bookings' page. Please check our cancellation policy for refund details."
    
    elif 'couple' in user_msg or 'unmarried' in user_msg:
        bot_reply = "We welcome all couples, provided both guests are 18+ and present valid government-issued photo ID at check-in."
    
    elif 'id' in user_msg or 'document' in user_msg:
        bot_reply = "We require a valid government-issued photo ID (like Aadhar, Passport, or Driver's License) for all guests."

    # --- 6. LOCATION & BANGALORE ---
    elif 'location' in user_msg or 'address' in user_msg or 'where' in user_msg:
        bot_reply = "We are located in Indiranagar, Bengaluru, known for its vibrant restaurants and shopping."
    
    elif 'airport' in user_msg:
        bot_reply = "The Kempegowda International Airport (BLR) is approximately 40km away. It can take 60-90 minutes by taxi, depending on traffic."
    
    elif 'metro' in user_msg:
        bot_reply = "The nearest Namma Metro station is Indiranagar, just a 5-minute walk from the hotel."

    # --- 7. OFFERS & FUN ---
    elif 'offer' in user_msg or 'discount' in user_msg or 'promo' in user_msg:
        bot_reply = "Yes! You can use code **'SAKKATH'** for 10% off or **'BOMBAAT'** for 20% off on the billing page."

    elif 'thank' in user_msg or 'dhanyavadagalu' in user_msg:
        bot_reply = "You're welcome! (ನಿಮಗೆ ಸ್ವಾಗತ - Nimage Swagata). Is there anything else I can help you with?"

    return jsonify({'response': bot_reply})