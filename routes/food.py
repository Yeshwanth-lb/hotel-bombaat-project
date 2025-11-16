import datetime
import uuid
from flask_mail import Message
from utils.db import mail 
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from utils.db import mongo
from routes.main import login_required

food_bp = Blueprint('food', __name__)

# Menu data
menu = {
    'North Indian': [
        {'name': 'Butter Chicken', 'price': 450, 'description': 'Creamy chicken curry.'},
        {'name': 'Dal Makhani', 'price': 300, 'description': 'Black lentils and kidney beans.'},
        {'name': 'Paneer Tikka', 'price': 350, 'description': 'Marinated cheese cubes.'},
    ],
    'South Indian': [
        {'name': 'Masala Dosa', 'price': 150, 'description': 'Crispy crepe with potato filling.'},
        {'name': 'Idli Sambar', 'price': 100, 'description': 'Steamed rice cakes.'},
    ],
    'Chinese': [
        {'name': 'Hakka Noodles', 'price': 250, 'description': 'Stir-fried noodles.'},
        {'name': 'Manchurian', 'price': 280, 'description': 'Fried vegetable balls.'},
    ],
    'Continental': [
        {'name': 'Veg Au Gratin', 'price': 400, 'description': 'Baked vegetables with cheese.'},
        {'name': 'Grilled Chicken', 'price': 500, 'description': 'Served with mashed potatoes.'},
    ],
    'Desserts': [
        {'name': 'Gulab Jamun', 'price': 120, 'description': 'Sweet milk solids balls.'},
        {'name': 'Chocolate Brownie', 'price': 200, 'description': 'With ice cream.'},
    ],
    'Beverages': [
        {'name': 'Masala Chai', 'price': 50, 'description': 'Spiced Indian tea.'},
        {'name': 'Fresh Lime Soda', 'price': 80, 'description': 'Sweet or salted.'},
    ]
}

@food_bp.route('/', methods=['GET', 'POST'])
@login_required
def order():
    if 'cart' not in session:
        session['cart'] = [] 
        session['cart_total'] = 0.0

    if request.method == 'POST':
        room_number_str = request.form['room_number']
        if not room_number_str:
            flash('Please provide a room number for delivery.', 'error')
            return redirect(url_for('food.order'))
        
        if not session['cart']:
            flash('Your cart is empty.', 'error')
            return redirect(url_for('food.order'))
            
        try:
            room_number = int(room_number_str)
            booking = mongo.db.bookings.find_one({
                'user_email': session['user_email'],
                'room_number': room_number,
                'status': 'active'
            })
            if not booking:
                flash(f'You do not have an active booking for room {room_number}.', 'error')
                return redirect(url_for('food.order'))

            order_doc = {
                'user_email': session['user_email'],
                'order_id': uuid.uuid4().hex,
                'items': session['cart'],
                'total_cost': session['cart_total'],
                'room_number': room_number,
                'payment_status': 'unpaid',
                'created_at': datetime.datetime.now(datetime.timezone.utc)
            }
            mongo.db.food_orders.insert_one(order_doc)
            
            # Send Food Email
            try:
                msg = Message(
                    subject="Food Order Confirmation - Hotel Bombaat", # <-- Professional Subject
                    sender=('Hotel Bombaat Kitchen', 'your-email@gmail.com'),
                    recipients=[session['user_email']]
                )
                msg.html = render_template(
                    'email_food_confirmation.html', 
                    username=session['username'], 
                    order=order_doc
                )
                mail.send(msg)
            except Exception as e:
                print(f"Failed to send food email: {e}") # Just print error, don't stop user

            session.pop('cart', None)
            session.pop('cart_total', None)

            flash('Order placed successfully! Email sent. Proceed to billing.', 'success')
            return redirect(url_for('booking.billing'))

        except ValueError:
             flash('Invalid room number.', 'error')
             return redirect(url_for('food.order'))

    return render_template('food.html', menu=menu, cart=session.get('cart'), total=session.get('cart_total'))

@food_bp.route('/add_to_cart', methods=['POST'])
@login_required
def add_to_cart():
    item_name = request.form['name']
    item_price = float(request.form['price'])
    
    if 'cart' not in session:
        session['cart'] = []
        session['cart_total'] = 0.0

    found = False
    for item in session['cart']:
        if item['name'] == item_name:
            item['quantity'] += 1
            found = True
            break
    
    if not found:
        session['cart'].append({'name': item_name, 'price': item_price, 'quantity': 1})

    session['cart_total'] = round(session['cart_total'] + item_price, 2)
    session.modified = True 
    
    flash(f'Added {item_name} to cart.', 'info')
    return redirect(url_for('food.order'))

@food_bp.route('/remove_from_cart/<item_name>')
@login_required
def remove_from_cart(item_name):
    if 'cart' in session:
        item_to_remove = None
        for item in session['cart']:
            if item['name'] == item_name:
                session['cart_total'] = round(session['cart_total'] - item['price'], 2)
                item['quantity'] -= 1
                if item['quantity'] == 0:
                    item_to_remove = item 
                break
        
        if item_to_remove:
            session['cart'].remove(item_to_remove)
        
        session.modified = True
        flash(f'Removed one {item_name} from cart.', 'info')

    return redirect(url_for('food.order'))