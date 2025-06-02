# auth.py (আগের উত্তর থেকে অপরিবর্তিত)
from flask import Blueprint, render_template, redirect, url_for, request, flash
# from werkzeug.security import generate_password_hash, check_password_hash # User মডেলে আছে
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User

auth_bp = Blueprint('auth', __name__, template_folder='templates')

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email') 
        password = request.form.get('password')

        if not username or not password:
            flash('ইউজারনেম এবং পাসওয়ার্ড আবশ্যক।', 'error')
            return redirect(url_for('auth.signup'))

        user_by_username = User.query.filter_by(username=username).first()
        if user_by_username:
            flash('এই ইউজারনেম ইতিমধ্যে ব্যবহৃত হয়েছে।', 'error')
            return redirect(url_for('auth.signup'))
        
        if email: # যদি ইমেইল দেওয়া হয়, তবেই ইউনিকনেস চেক করুন
            user_by_email = User.query.filter_by(email=email).first()
            if user_by_email:
                flash('এই ইমেইল ইতিমধ্যে ব্যবহৃত হয়েছে।', 'error')
                return redirect(url_for('auth.signup'))

        new_user = User(username=username, email=email if email else None)
        new_user.set_password(password)
        
        try:
            db.session.add(new_user)
            db.session.commit()
            flash('সফলভাবে সাইনআপ সম্পন্ন হয়েছে! এখন লগইন করুন।', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            flash(f'সাইনআপে সমস্যা হয়েছে: {str(e)}', 'error')
            # return redirect(url_for('auth.signup')) # একই পেজে থাকা ভালো, যাতে ইউজার আবার চেষ্টা করতে পারে
            return render_template('signup.html')


    return render_template('signup.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False

        if not username or not password:
            flash('ইউজারনেম এবং পাসওয়ার্ড দিন।', 'error')
            return redirect(url_for('auth.login'))

        user = User.query.filter_by(username=username).first()
        
        if not user or not user.check_password(password):
            flash('ইউজারনেম বা পাসওয়ার্ড সঠিক নয়।', 'error')
            return redirect(url_for('auth.login'))
        
        login_user(user, remember=remember)
        flash('সফলভাবে লগইন করেছেন!', 'success')
        # লগইন করার পর ব্যবহারকারী যে পেজে যেতে চেয়েছিল (যদি থাকে)
        next_page = request.args.get('next')
        return redirect(next_page or url_for('main.home')) 
        
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('আপনি সফলভাবে লগআউট হয়েছেন।', 'info')
    return redirect(url_for('auth.login'))
