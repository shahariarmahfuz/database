import os
from flask import Flask
from flask_login import LoginManager
from models import db as main_db, User # models.py থেকে db এবং User import করুন
from auth import auth_bp
from routes import main_bp

# --- Flask App ইনিশিয়ালাইজেশন ---
app = Flask(__name__)

# --- কনফিগারেশন ---
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'a_very_strong_default_secret_key_for_dev_123_change_this_properly_in_env')

# --- PostgreSQL ডাটাবেজ কনফিগারেশন ---
# ব্যবহারকারীর দেওয়া PostgreSQL কানেকশন স্ট্রিং সরাসরি ব্যবহার করা হচ্ছে
# সতর্কতা: প্রোডাকশনে সরাসরি কোডে ক্রেডেনশিয়ালস রাখা উচিত নয়।
# আপনার দেওয়া কানেকশন স্ট্রিং:
POSTGRESQL_CONNECTION_STRING = "postgresql://unknown_h8v3_user:kpU1Kgvo5PomlfVa8sA5Z3obRiOpDW8K@dpg-d0uk3r63jp1c7387sr5g-a/unknown_h8v3"

# যদি Render.com এ তাদের নিজস্ব PostgreSQL ডাটাবেজ ব্যবহার করেন, 
# তাহলে os.environ.get('DATABASE_URL') ব্যবহার করাই ভালো হতো।
# কিন্তু আপনার অনুরোধ অনুযায়ী সরাসরি স্ট্রিং ব্যবহার করা হলো।
app.config['SQLALCHEMY_DATABASE_URI'] = POSTGRESQL_CONNECTION_STRING
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024  # ৩২ মেগাবাইট ফাইল আপলোড লিমিট

# আপলোড ফোল্ডার (অস্থায়ী ফাইল রাখার জন্য)
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads_temp')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ইউজার-স্পেসিফিক ফাইল (শিডিউলড ব্যাকআপ) রাখার মূল ফোল্ডার
# Render.com এ এটি একটি মাউন্ট করা Persistent Disk এর পাথ হওয়া উচিত।
USER_FILES_BASE_DIR = os.environ.get('USER_FILES_STORAGE_DIR', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'user_files_local_dev'))
if not os.path.exists(USER_FILES_BASE_DIR):
    os.makedirs(USER_FILES_BASE_DIR, exist_ok=True)
app.config['USER_FILES_BASE_DIR'] = USER_FILES_BASE_DIR


# --- ডাটাবেজ ও এক্সটেনশন ইনিশিয়ালাইজেশন ---
main_db.init_app(app)

login_manager = LoginManager()
login_manager.login_view = 'auth.login' # লগইন পেজের রুট
login_manager.login_message = "এই পাতাটি অ্যাক্সেস করার জন্য অনুগ্রহ করে লগইন করুন।"
login_manager.login_message_category = "info" # ফ্ল্যাশ মেসেজের স্টাইল কন্ট্রোল করার জন্য
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- ব্লুপ্রিন্ট রেজিস্টার করা ---
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(main_bp, url_prefix='/')

# --- CLI কমান্ড (ডাটাবেজ টেবিল তৈরি করার জন্য) ---
@app.cli.command("init-db")
def init_db_command():
    """ডাটাবেজ টেবিল তৈরি করে (যদি না থাকে)।"""
    with app.app_context():
        main_db.create_all()
    print(f"Initialized the database and created tables (if they didn't exist) on {app.config['SQLALCHEMY_DATABASE_URI']}")

# --- অ্যাপ চালানো ---
if __name__ == '__main__':
    with app.app_context(): 
        # অ্যাপ চালু হওয়ার সময় টেবিল তৈরি করা (যদি init-db ব্যবহার না করেন)
        # db.create_all() কল করলে টেবিল না থাকলে তৈরি হবে, থাকলে কিছু করবে না।
        main_db.create_all() 
    
    # debug=False প্রোডাকশনের জন্য, debug=True ডেভেলপমেন্টের জন্য
    # Render এ PORT এনভায়রনমেন্ট ভেরিয়েবল থেকে পোর্ট নেওয়া হয়।
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
