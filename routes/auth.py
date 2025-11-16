import datetime
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from flask import current_app # <-- 1. Import current_app
from werkzeug.security import generate_password_hash, check_password_hash
from utils.db import mongo, mail # <-- 2. No more 'serializer' import
from flask_mail import Message
from itsdangerous import URLSafeTimedSerializer # <-- 3. Import the tool

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Handles user registration."""
    if request.method == 'POST':
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']
        phone = request.form['phone']
        
        users_collection = mongo.db.users
        existing_user = users_collection.find_one({'email': email})

        if existing_user:
            flash('Email already registered. Please login.', 'warning')
            return redirect(url_for('auth.login'))

        hashed_password = generate_password_hash(password)
        
        users_collection.insert_one({
            'email': email,
            'username': username,
            'password': hashed_password,
            'phone': phone,
            'created_at': datetime.datetime.now(datetime.timezone.utc)
        })

        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handles user login."""
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        users_collection = mongo.db.users
        user = users_collection.find_one({'email': email})

        if user and check_password_hash(user['password'], password):
            session['user_email'] = user['email']
            session['username'] = user['username']
            if user.get('is_admin', False):
                session['is_admin'] = True
            flash('Login successful! Welcome back.', 'success')
            return redirect(url_for('main.dashboard'))
        else:
            flash('Invalid email or password. Please try again.', 'error')
            return redirect(url_for('auth.login'))

    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    """Clears the session and logs the user out."""
    session.pop('user_email', None)
    session.pop('username', None)
    session.pop('is_admin', None) 
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))

# -----------------------------------------------
# !! FORGOT PASSWORD ROUTE (FIXED) !!
# -----------------------------------------------
@auth_bp.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        user = mongo.db.users.find_one({'email': email})

        if not user:
            flash('Email not found. Please register.', 'warning')
            return redirect(url_for('auth.forgot_password'))
        
        # 4. Create serializer on-the-fly
        s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        token = s.dumps(email, salt='password-reset-salt')
        
        reset_url = url_for('auth.reset_password_token', token=token, _external=True)
        
        try:
            msg = Message(
                subject="Password Reset Request for Hotel Bombaat",
                sender=('Hotel Bombaat', 'your-email@gmail.com'),
                recipients=[email]
            )
            msg.html = render_template(
                'email_reset.html', 
                username=user.get('username', 'Guest'), 
                reset_url=reset_url
            )
            mail.send(msg)
            flash('Password reset link sent! Check your email.', 'success')
        except Exception as e:
            flash(f'Failed to send email: {e}', 'error')
            
        return redirect(url_for('auth.login'))
        
    return render_template('forgot_password.html')

# -----------------------------------------------
# !! RESET PASSWORD TOKEN ROUTE (FIXED) !!
# -----------------------------------------------
@auth_bp.route('/reset/<token>', methods=['GET', 'POST'])
def reset_password_token(token):
    
    # 5. Create serializer on-the-fly
    s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    
    try:
        email = s.loads(token, salt='password-reset-salt', max_age=3600)
    except Exception as e:
        flash('The password reset link is invalid or has expired.', 'error')
        return redirect(url_for('auth.login'))
        
    if request.method == 'POST':
        new_password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if new_password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('reset_password.html', token=token)
            
        hashed_password = generate_password_hash(new_password)
        mongo.db.users.update_one(
            {'email': email},
            {'$set': {'password': hashed_password}}
        )
        
        flash('Your password has been reset! You can now login.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('reset_password.html', token=token)