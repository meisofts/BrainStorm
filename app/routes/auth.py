# app/routes/auth.py

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, current_user, login_required
from app import db, bcrypt
from app.models.user import User
import functools

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        # Redirect authenticated users based on their role
        return redirect(url_for('auth.dashboard_redirect'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            flash(f'Logged in successfully as {user.username}.', 'success')
            return redirect(url_for('auth.dashboard_redirect'))
        else:
            flash('Login Unsuccessful. Please check username and password', 'danger')
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    user = current_user # The user currently logged in (this is defined here)
    if request.method == 'POST':
        old_password = request.form.get('old_password') # Corrected to match template
        new_password = request.form.get('new_password')
        confirm_new_password = request.form.get('confirm_new_password')

        # 1. Validate current password
        if not user.check_password(old_password): # Using the new method from User model
            flash('Incorrect current password.', 'danger')
        # 2. Check if new password matches confirmation
        elif new_password != confirm_new_password:
            flash('New password and confirm new password do not match.', 'danger')
        # 3. Basic password strength (adjust length or add more complexity checks)
        elif len(new_password) < 8: # Increased to 8 for better security
            flash('New password must be at least 8 characters long.', 'danger')
        else:
            try:
                # Hash and update password using the new method from User model
                user.set_password(new_password)
                db.session.commit()
                flash('Your password has been changed successfully! Please log in again with your new password.', 'success')
                logout_user() # Log user out for security after password change
                return redirect(url_for('auth.login'))
            except Exception as e:
                db.session.rollback() # Rollback in case of database error
                flash(f'An error occurred while changing password: {e}', 'danger')
    # For GET request or if validation fails on POST, render the form
    # --- THIS IS THE CORRECTED LINE ---
    return render_template('auth/change_password.html', user=user)
    # --- END OF CORRECTED LINE ---

@auth_bp.route('/dashboard_redirect')
@login_required
def dashboard_redirect():
    """Redirects the user to their appropriate dashboard based on their role."""
    if current_user.has_role('superadmin') or current_user.has_role('admin'):
        return redirect(url_for('admin.dashboard'))
    elif current_user.has_role('moderator'):
        return redirect(url_for('moderator.dashboard'))
    else:
        flash('You do not have a specific dashboard assigned.', 'warning')
        return redirect(url_for('auth.login'))

def role_required(*roles):
    def wrapper(fn):
        @functools.wraps(fn)
        @login_required
        def decorated_view(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('auth.login'))

            if current_user.role.name not in roles:
                flash('You do not have permission to access this page.', 'danger')
                if current_user.has_role('admin') or current_user.has_role('superadmin'):
                    return redirect(url_for('admin.dashboard'))
                elif current_user.has_role('moderator'):
                    return redirect(url_for('moderator.dashboard'))
                else:
                    return redirect(url_for('auth.login'))
            return fn(*args, **kwargs)
        return decorated_view
    return wrapper
