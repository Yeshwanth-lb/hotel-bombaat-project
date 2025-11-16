import datetime
from flask import Blueprint, render_template, session, flash, request, redirect, url_for
from utils.db import mongo
from functools import wraps
from bson.objectid import ObjectId
import re # <-- 1. IMPORT REGEX

admin_bp = Blueprint('admin', __name__)

# --- Decorator for ADMIN protection ---
def admin_required(f):
    """
    Decorator to ensure a user is logged in AND is an admin.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_email' not in session:
            flash('You must be logged in to view this page.', 'warning')
            return redirect(url_for('auth.login'))
        
        user = mongo.db.users.find_one({'email': session['user_email']})
        
        if not user or not user.get('is_admin', False):
            flash('You do not have permission to access this page.', 'error')
            return redirect(url_for('main.dashboard'))
            
        session['is_admin'] = True
        return f(*args, **kwargs)
    return decorated_function

# --- Admin Dashboard ---
@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    """Serves the admin dashboard with site-wide stats."""
    total_users = mongo.db.users.count_documents({})
    total_bookings = mongo.db.bookings.count_documents({})
    total_orders = mongo.db.food_orders.count_documents({})
    
    total_revenue_bookings = sum(b.get('total_cost', 0) for b in mongo.db.bookings.find(
        {'payment_status': 'paid'}
    ))
    total_revenue_food = sum(f.get('total_cost', 0) for f in mongo.db.food_orders.find(
        {'payment_status': 'paid'}
    ))
    total_revenue = total_revenue_bookings + total_revenue_food
    
    stats = {
        'total_users': total_users,
        'total_bookings': total_bookings,
        'total_orders': total_orders,
        'total_revenue': round(total_revenue, 0)
    }
    
    recent_bookings = list(mongo.db.bookings.find().sort('created_at', -1).limit(5))
    
    return render_template('admin_dashboard.html', stats=stats, recent_bookings=recent_bookings)

# --- Manage Users ---
@admin_bp.route('/users')
@admin_required
def manage_users():
    """Displays all users."""
    users = list(mongo.db.users.find())
    return render_template('admin_users.html', users=users)

@admin_bp.route('/users/delete/<id>')
@admin_required
def delete_user(id):
    """Deletes a user."""
    mongo.db.users.delete_one({'_id': ObjectId(id)})
    flash('User deleted successfully.', 'success')
    return redirect(url_for('admin.manage_users'))

# --- Manage Bookings ---
@admin_bp.route('/bookings')
@admin_required
def manage_bookings():
    """Displays all bookings, WITH SEARCH."""
    
    # 2. Get the search query from the URL
    search_query = request.args.get('search_query')
    
    query_filter = {} # Start with an empty filter
    
    if search_query:
        # 3. Create a case-insensitive regex
        regex = re.compile(f'.*{re.escape(search_query)}.*', re.IGNORECASE)
        
        # 4. Build a query to search multiple fields
        query_filter = {
            '$or': [
                {'user_email': regex},
                {'room_type': regex},
                {'booking_id': regex}
            ]
        }
    
    # 5. Find bookings using the filter (it's empty if no search)
    bookings = list(mongo.db.bookings.find(query_filter).sort('created_at', -1))
    
    # 6. Pass the search query back to the template
    return render_template('admin_bookings.html', bookings=bookings, search_query=search_query)


@admin_bp.route('/bookings/delete/<booking_id_str>')
@admin_required
def delete_booking(booking_id_str):
    """Deletes a booking by its string UUID."""
    mongo.db.bookings.delete_one({'booking_id': booking_id_str})
    flash('Booking deleted successfully.', 'success')
    return redirect(url_for('admin.manage_bookings'))