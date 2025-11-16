import datetime
import uuid
import io
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from flask import send_file, Blueprint, render_template, request, redirect, url_for, session, flash
from utils.db import mongo
from routes.main import login_required

payment_bp = Blueprint('payment', __name__)

# Re-define Promo Codes here (or import from config/booking)
PROMO_CODES = {
    'SAKKATH': 10, 
    'BOMBAAT': 20,
    'WELCOME': 5
}

@payment_bp.route('/process', methods=['POST'])
@login_required
def process_payment():
    user_email = session['user_email']
    payment_method = request.form['payment_method']
    promo_code = request.form.get('promo_code', '').upper() # Get code from hidden input
    
    unpaid_bookings = list(mongo.db.bookings.find({
        'user_email': user_email,
        'payment_status': 'unpaid',
        'status': 'active'
    }))
    unpaid_food_orders = list(mongo.db.food_orders.find({
        'user_email': user_email,
        'payment_status': 'unpaid'
    }))

    if not unpaid_bookings and not unpaid_food_orders:
        flash('No pending payments found.', 'info')
        return redirect(url_for('main.dashboard'))

    # 1. Calculate Original Total
    total_booking_cost = sum(b['total_cost'] for b in unpaid_bookings)
    total_food_cost = sum(f['total_cost'] for f in unpaid_food_orders)
    original_total = total_booking_cost + total_food_cost
    
    # 2. Apply Discount (Server-Side Verification)
    discount_amount = 0
    if promo_code and promo_code in PROMO_CODES:
        percent = PROMO_CODES[promo_code]
        discount_amount = (original_total * percent) / 100
        
    final_amount = original_total - discount_amount

    payment_id = uuid.uuid4().hex
    internal_order_id = f"PAY-{uuid.uuid4().hex[:8].upper()}"
    
    booking_ids_paid = [b['booking_id'] for b in unpaid_bookings]
    food_order_ids_paid = [f['order_id'] for f in unpaid_food_orders]

    payment_doc = {
        'user_email': user_email,
        'payment_id': payment_id,
        'order_id': internal_order_id, 
        'amount': final_amount, # Save final discounted amount
        'original_amount': original_total, # Keep record of original
        'discount_applied': discount_amount,
        'promo_code': promo_code,
        'payment_method': payment_method,
        'booking_ids': booking_ids_paid,
        'food_order_ids': food_order_ids_paid,
        'status': 'success',
        'created_at': datetime.datetime.now(datetime.timezone.utc)
    }
    mongo.db.payments.insert_one(payment_doc)

    if booking_ids_paid:
        mongo.db.bookings.update_many(
            {'booking_id': {'$in': booking_ids_paid}},
            {'$set': {'payment_status': 'paid'}}
        )
    
    if food_order_ids_paid:
        mongo.db.food_orders.update_many(
            {'order_id': {'$in': food_order_ids_paid}},
            {'$set': {'payment_status': 'paid'}}
        )

    # Loyalty Points (Based on Final Amount)
    points_earned = int(final_amount / 100)
    mongo.db.users.update_one(
        {'email': user_email},
        {'$inc': {'loyalty_points': points_earned}}
    )
    
    flash(f'Payment successful! Discount: ₹{discount_amount:.2f}. Earned {points_earned} Points!', 'success')
    return redirect(url_for('payment.confirmation', order_id=internal_order_id))

@payment_bp.route('/confirmation/<order_id>')
@login_required
def confirmation(order_id):
    payment_details = mongo.db.payments.find_one({
        'order_id': order_id,
        'user_email': session['user_email']
    })
    
    if not payment_details:
        flash('Payment confirmation not found.', 'error')
        return redirect(url_for('main.dashboard'))
    
    return render_template('payment_confirmation.html', payment=payment_details)

@payment_bp.route('/download_invoice/<order_id>')
@login_required
def download_invoice(order_id):
    """Generates PDF with Discount Details."""
    payment = mongo.db.payments.find_one({
        'order_id': order_id,
        'user_email': session['user_email']
    })
    
    if not payment:
        flash('Invoice not found.', 'error')
        return redirect(url_for('main.dashboard'))

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    c.setFont("Helvetica-Bold", 24)
    c.drawString(50, height - 50, "Hotel Bombaat")
    c.setFont("Helvetica", 12)
    c.drawString(50, height - 70, "Bengaluru, Karnataka, India")
    c.line(50, height - 100, width - 50, height - 100)
    
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 130, "INVOICE")
    c.setFont("Helvetica", 12)
    c.drawString(50, height - 155, f"Order ID: {payment['order_id']}")
    c.drawString(50, height - 175, f"Date: {payment['created_at'].strftime('%Y-%m-%d %H:%M')}")
    
    y = height - 260
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Description")
    c.drawString(400, y, "Amount (INR)")
    c.line(50, y - 10, width - 50, y - 10)
    y -= 30
    
    c.setFont("Helvetica", 12)
    # (Item listing code same as before...)
    if 'booking_ids' in payment:
        bookings = mongo.db.bookings.find({'booking_id': {'$in': payment['booking_ids']}})
        for b in bookings:
            desc = f"Room Booking: {b['room_type']}"
            c.drawString(50, y, desc)
            c.drawString(400, y, f"{b['total_cost']:.2f}")
            y -= 20

    if 'food_order_ids' in payment:
        orders = mongo.db.food_orders.find({'order_id': {'$in': payment['food_order_ids']}})
        for f in orders:
            desc = f"Food Order #{f['order_id'][:8]}"
            c.drawString(50, y, desc)
            c.drawString(400, y, f"{f['total_cost']:.2f}")
            y -= 20
            
    c.line(50, y - 10, width - 50, y - 10)
    y -= 30
    
    # SHOW DISCOUNT ON INVOICE
    if payment.get('discount_applied', 0) > 0:
        c.drawString(300, y, "Subtotal:")
        c.drawString(400, y, f"{payment.get('original_amount', payment['amount']):.2f}")
        y -= 20
        c.setFont("Helvetica-Bold", 12)
        c.setFillColorRGB(0, 0.5, 0) # Green color for discount
        c.drawString(300, y, f"Discount ({payment['promo_code']}):")
        c.drawString(400, y, f"-{payment['discount_applied']:.2f}")
        c.setFillColorRGB(0, 0, 0) # Reset color
        y -= 20
        
    c.setFont("Helvetica-Bold", 14)
    c.drawString(300, y, "GRAND TOTAL:")
    c.drawString(400, y, f"{payment['amount']:.2f}")
    
    c.showPage()
    c.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f"Invoice_{order_id}.pdf", mimetype='application/pdf')