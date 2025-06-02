# auth.py
from flask import Blueprint, render_template, redirect, url_for, request, flash, g, current_app
# from werkzeug.security import generate_password_hash, check_password_hash # DataManager এ আছে
from flask_login import login_user, logout_user, login_required, current_user
from data_manager import JSONUser # UserMixin এর মতো কাজ করার জন্য

auth_bp = Blueprint('auth', __name__, template_folder='templates')

# DataManager ইনস্ট্যান্স প্রতিটি রুটে g থেকে নেওয়া হবে
# def get_data_manager():
#     if 'data_manager' not in g:
#         g.data_manager = DataManager(current_app.config['DATA_JSON_PATH'])
#     return g.data_manager

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    
    data_manager = g.data_manager # app.before_request থেকে g.data_manager সেট করা হয়েছে

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email', '').strip()
        password = request.form.get('password')

        if not username or not password:
            flash('ইউজারনেম এবং পাসওয়ার্ড আবশ্যক।', 'error')
            return render_template('signup.html') # একই পেজে এরর দেখান

        # DataManager ব্যবহার করে ইউজার তৈরি
        created_user_dict = data_manager.create_user(username, password, email if email else None)
        
        if created_user_dict is None:
            # create_user None রিটার্ন করবে যদি ইউজারনেম বা ইমেইল আগে থেকে থাকে
            flash('এই ইউজারনেম বা ইমেইল ইতিমধ্যে ব্যবহৃত হয়েছে।', 'error')
        else:
            flash('সফলভাবে সাইনআপ সম্পন্ন হয়েছে! এখন লগইন করুন।', 'success')
            return redirect(url_for('auth.login'))
            
    return render_template('signup.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))

    data_manager = g.data_manager

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False

        if not username or not password:
            flash('ইউজারনেম এবং পাসওয়ার্ড দিন।', 'error')
            return render_template('login.html')

        user_dict = data_manager.get_user_by_username(username)
        
        # JSONUser অবজেক্ট তৈরি করে check_password কল করা
        if user_dict and JSONUser(user_dict).check_password(password):
            user_obj = JSONUser(user_dict)
            login_user(user_obj, remember=remember) # Flask-Login এর login_user
            flash('সফলভাবে লগইন করেছেন!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.home'))
        else:
            flash('ইউজারনেম বা পাসওয়ার্ড সঠিক নয়।', 'error')
            
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required # current_user এখন JSONUser অবজেক্ট হবে
def logout():
    logout_user()
    flash('আপনি সফলভাবে লগআউট হয়েছেন।', 'info')
    return redirect(url_for('auth.login'))
