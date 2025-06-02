import os
from flask import Flask
from flask_login import LoginManager
from models import db as main_db, User # models.py থেকে db এবং User import করুন
from auth import auth_bp
from routes import main_bp

# --- Flask App ইনিশিয়ালাইজেশন ---
app = Flask(__name__) 
# instance_relative_config=True দিলে Flask instance ফোল্ডার থেকে কনফিগ ফাইল লোড করতে পারে, 
# তবে আমরা সরাসরি পাথ ম্যানেজ করছি।

# --- কনফিগারেশন ---
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'fallback_a_very_very_strong_secret_key_for_dev_123_change_this')

# --- SQLite ডাটাবেজ কনফিগারেশন ---
# Render.com এ Persistent Disk এর পাথ এখানে সঠিকভাবে দিতে হবে।
# DATABASE_STORAGE_DIR এনভায়রনমেন্ট ভেরিয়েবল Render এ সেট করতে হবে, 
# যার মান হবে Persistent Disk এ তৈরি করা একটি ফোল্ডারের পাথ (যেমন /mnt/disk/app_data)
# লোকাল ডেভেলপমেন্টের জন্য এটি বর্তমান ডিরেক্টরির পাশে 'instance' ফোল্ডার ব্যবহার করবে।
DATABASE_DIR = os.environ.get('DATABASE_STORAGE_DIR', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance'))

# নিশ্চিত করুন যে DATABASE_DIR (instance ফোল্ডার) বিদ্যমান আছে
# Flask অ্যাপ চালু হওয়ার সময় এটি চেক করা ভালো।
if not os.path.exists(DATABASE_DIR):
    try:
        os.makedirs(DATABASE_DIR, exist_ok=True)
        print(f"Created database storage directory at: {DATABASE_DIR}")
    except OSError as e:
        print(f"CRITICAL: Error creating database storage directory at {DATABASE_DIR}: {e}")
        # এখানে অ্যাপ ক্র্যাশ করানো বা একটি ফলব্যাক পাথ ব্যবহার করার সিদ্ধান্ত নিতে পারেন।
        # আপাতত, অ্যাপ চলতে থাকবে, কিন্তু ডাটাবেজ তৈরি নাও হতে পারে।

app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(DATABASE_DIR, 'user.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024  # ৩২ মেগাবাইট ফাইল আপলোড লিমিট

# আপলোড ফোল্ডার (অস্থায়ী ফাইল, যেমন রিস্টোরের জন্য SQL ফাইল, রাখার জন্য)
# এটি Render এর ephemeral filesystem এ থাকতে পারে।
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads_temp')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ইউজার-স্পেসিফিক ফাইল (শিডিউলড pg_dump ব্যাকআপ) রাখার মূল ফোল্ডার
# Render.com এ এটি একটি মাউন্ট করা Persistent Disk এর পাথ হওয়া উচিত।
# (DATABASE_STORAGE_DIR এর মতোই, USER_FILES_DIR নামে আরেকটি এনভায়রনমেন্ট ভেরিয়েবল ব্যবহার করা ভালো)
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

# --- CLI কমান্ড (ঐচ্ছিক, Render এ Deploy Script ব্যবহার করা যেতে পারে) ---
@app.cli.command("init-db")
def init_db_command():
    """ডাটাবেজ টেবিল তৈরি করে (যদি না থাকে)।"""
    with app.app_context():
        # DATABASE_DIR তৈরি হয়েছে কিনা আবার নিশ্চিত করা (যদি অ্যাপ চালু হওয়ার সময় না হয়ে থাকে)
        if not os.path.exists(DATABASE_DIR):
             try:
                os.makedirs(DATABASE_DIR, exist_ok=True)
                print(f"init-db: Created database storage directory at: {DATABASE_DIR}")
             except OSError:
                print(f"init-db: Could not create database storage directory at {DATABASE_DIR}. Check permissions.")
                return
        main_db.create_all()
    print(f"Initialized the SQLite database at {app.config['SQLALCHEMY_DATABASE_URI']}")

# --- অ্যাপ চালানো ---
if __name__ == '__main__':
    with app.app_context(): 
        # DATABASE_DIR তৈরি হয়েছে কিনা আবার নিশ্চিত করা
        if not os.path.exists(DATABASE_DIR):
             try:
                os.makedirs(DATABASE_DIR, exist_ok=True)
             except OSError:
                print(f"Could not create database storage directory at {DATABASE_DIR} on startup.")
        main_db.create_all() # ডাটাবেজ ফাইল এবং টেবিল তৈরি করবে যদি না থাকে
    
    # debug=False প্রোডাকশনের জন্য, debug=True ডেভেলপমেন্টের জন্য
    # Render এ PORT এনভায়রনমেন্ট ভেরিয়েবল থেকে পোর্ট নেওয়া হয়।
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
