import datetime
import uuid
import random
from flask_mail import Message
from utils.db import mail 
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from utils.db import mongo
from routes.main import login_required
from bson.objectid import ObjectId 

booking_bp = Blueprint('booking', __name__)

# Room data
room_types = {
    'Standard Single': {'price': 1500, 'description': 'A cozy room for a single traveler.'},
    'Standard Double': {'price': 2500, 'description': 'Comfortable room with a double bed.'},
    'Deluxe Double': {'price': 5000, 'description': 'Spacious room with luxury amenities.'},
    'Suite': {'price': 8000, 'description': 'A large suite with a separate living area.'},
    'Presidential Suite': {'price': 15000, 'description': 'The ultimate in luxury and space.'}
}

# Promo Codes
PROMO_CODES = {
    'SAKKATH': 10,  # 10% discount
    'BOMBAAT': 20,  # 20% discount
    'WELCOME': 5    # 5% discount
}

@booking_bp.route('/rooms', methods=['GET', 'POST'])
@login_required
def rooms():
    """Handles new room booking with Email Confirmation."""
    if request.method == 'POST':
        try:
            room_type = request.form['room_type']
            check_in_str = request.form['check_in']
            check_out_str = request.form['check_out']
            guests = int(request.form['guests'])
            
            check_in = datetime.datetime.strptime(check_in_str, '%Y-%m-%d')
            check_out = datetime.datetime.strptime(check_out_str, '%Y-%m-%d')
            today = datetime.datetime.combine(datetime.date.today(), datetime.time.min)

            if check_in < today:
                flash('Check-in date cannot be in the past.', 'error')
                return redirect(url_for('booking.rooms'))
            if check_out <= check_in:
                flash('Check-out date must be after check-in date.', 'error')
                return redirect(url_for('booking.rooms'))
            
            num_days = (check_out - check_in).days
            price_per_night = room_types[room_type]['price']
            total_cost = num_days * price_per_night
            room_number = random.randint(101, 250)

            booking_doc = {
                'user_email': session['user_email'],
                'booking_id': uuid.uuid4().hex, 
                'room_type': room_type,
                'room_number': room_number,
                'check_in': check_in_str,
                'check_out': check_out_str,
                'guests': guests,
                'total_cost': float(total_cost),
                'status': 'active',
                'payment_status': 'unpaid',
                'created_at': datetime.datetime.now(datetime.timezone.utc)
            }
            mongo.db.bookings.insert_one(booking_doc)

            # Send Email
            try:
                msg = Message(
                    subject="Booking Confirmation - Hotel Bombaat", # <-- Professional Subject
                    sender=('Hotel Bombaat', 'your-email@gmail.com'), 
                    recipients=[session['user_email']]
                )
                msg.html = render_template(
                    'email_confirmation.html', 
                    username=session['username'], 
                    booking=booking_doc
                )
                mail.send(msg)
                flash(f'{room_type} booked successfully! Total: ₹{total_cost:.2f}. Confirmation email sent!', 'success')
            except Exception as e:
                flash(f'Booking successful, but failed to send email: {e}', 'warning')

            return redirect(url_for('booking.billing'))

        except Exception as e:
            flash(f'An error occurred: {e}', 'error')
            return redirect(url_for('booking.rooms'))

    return render_template('rooms.html', room_types=room_types)

@booking_bp.route('/my_bookings')
@login_required
def my_bookings():
    """Displays all bookings with ANALYTICS DATA."""
    user_email = session['user_email']
    bookings = list(mongo.db.bookings.find({'user_email': user_email}).sort('created_at', -1))
    
    dates_map = {}
    for b in bookings:
        date_str = b['check_in'] 
        cost = b['total_cost']
        if date_str in dates_map:
            dates_map[date_str] += cost
        else:
            dates_map[date_str] = cost
            
    sorted_dates = sorted(dates_map.keys())
    spending_values = [dates_map[d] for d in sorted_dates]
    
    room_counts = {}
    for b in bookings:
        rtype = b['room_type']
        room_counts[rtype] = room_counts.get(rtype, 0) + 1
        
    room_labels = list(room_counts.keys())
    room_values = list(room_counts.values())

    return render_template('my_bookings.html', 
                           bookings=bookings,
                           chart_dates=sorted_dates,
                           chart_spending=spending_values,
                           chart_rooms=room_labels,
                           chart_room_counts=room_values)

@booking_bp.route('/cancel/<booking_id_str>')
@login_required
def cancel_booking(booking_id_str):
    user_email = session['user_email']
    result = mongo.db.bookings.update_one(
        {'booking_id': booking_id_str, 'user_email': user_email},
        {'$set': {'status': 'cancelled'}}
    )
    if result.modified_count > 0:
        flash('Booking cancelled successfully.', 'success')
    else:
        flash('Could not find or cancel booking.', 'error')
    return redirect(url_for('booking.my_bookings'))

@booking_bp.route('/billing')
@login_required
def billing():
    user_email = session['user_email']
    
    unpaid_bookings = list(mongo.db.bookings.find({
        'user_email': user_email,
        'payment_status': 'unpaid',
        'status': 'active' 
    }))
    
    unpaid_food_orders = list(mongo.db.food_orders.find({
        'user_email': user_email,
        'payment_status': 'unpaid'
    }))

    total_booking_cost = sum(b['total_cost'] for b in unpaid_bookings)
    total_food_cost = sum(f['total_cost'] for f in unpaid_food_orders)
    grand_total = total_booking_cost + total_food_cost

    return render_template('billing.html', 
                             bookings=unpaid_bookings,
                             food_orders=unpaid_food_orders,
                             total_booking_cost=total_booking_cost,
                             total_food_cost=total_food_cost,
                             grand_total=grand_total)

@booking_bp.route('/get_booked_dates/<room_type>')
@login_required
def get_booked_dates(room_type):
    booked_dates = set()
    bookings = mongo.db.bookings.find({
        'room_type': room_type,
        'status': 'active'
    })

    for booking in bookings:
        try:
            start_date = datetime.datetime.strptime(booking['check_in'], '%Y-%m-%d')
            end_date = datetime.datetime.strptime(booking['check_out'], '%Y-%m-%d')
            
            current_date = start_date
            while current_date < end_date:
                booked_dates.add(current_date.strftime('%Y-%m-%d'))
                current_date += datetime.timedelta(days=1)
        except Exception as e:
            print(f"Error processing booking {booking['_id']}: {e}")
            
    return jsonify(list(booked_dates))

@booking_bp.route('/apply_promo', methods=['POST'])
@login_required
def apply_promo():
    data = request.get_json()
    code = data.get('code', '').upper()
    
    if code in PROMO_CODES:
        discount_percent = PROMO_CODES[code]
        return jsonify({'valid': True, 'discount_percent': discount_percent})
    else:
        return jsonify({'valid': False})