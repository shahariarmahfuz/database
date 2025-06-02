import os
from flask import Flask
from flask_login import LoginManager
from models import db as main_db, User # models.py থেকে db এবং User import করুন
from auth import auth_bp
from routes import main_bp
# utils.py থেকে কোনো ফাংশন সরাসরি এখানে import করার প্রয়োজন নেই, routes বা run_backups করবে

# --- Flask App ইনিশিয়ালাইজেশন ---
app = Flask(__name__)

# --- কনফিগারেশন ---
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'change_this_to_a_very_strong_random_secret_in_production')

# Render.com এ PostgreSQL ডাটাবেজের জন্য কানেকশন স্ট্রিং এনভায়রনমেন্ট ভেরিয়েবল থেকে নেওয়া হবে।
# Render সাধারণত 'DATABASE_URL' নামে এটি দিয়ে থাকে যদি আপনি তাদের ডাটাবেজ সার্ভিস ব্যবহার করেন।
# আপনি যে স্ট্রিংটি দিয়েছেন, সেটি Render এ 'APP_DB_URL' নামে একটি এনভায়রনমেন্ট ভেরিয়েবলে সেট করতে পারেন।
DATABASE_CONNECTION_STRING = os.environ.get(
    'APP_DB_URL',  # Render এ এই নামে এনভায়রনমেন্ট ভেরিয়েবল সেট করুন আপনার দেওয়া PostgreSQL লিংক দিয়ে
    'sqlite:///./instance/user_dev.db' # লোকাল ডেভেলপমেন্টের জন্য ফলব্যাক (instance ফোল্ডারে)
)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_CONNECTION_STRING
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024  # ৩২ মেগাবাইট ফাইল আপলোড লিমিট

# আপলোড ফোল্ডার (অস্থায়ী ফাইল রাখার জন্য)
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads_temp')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ইউজার-স্পেসিফিক ফাইল (শিডিউলড ব্যাকআপ) রাখার মূল ফোল্ডার
# Render.com এ এটি একটি মাউন্ট করা Persistent Disk এর পাথ হওয়া উচিত।
# উদাহরণ: '/mnt/disk/user_files' (Render Disk মাউন্ট পাথ অনুযায়ী)
USER_FILES_BASE_DIR = os.environ.get('USER_FILES_DIR', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'user_files_local_dev'))
if not os.path.exists(USER_FILES_BASE_DIR):
    os.makedirs(USER_FILES_BASE_DIR, exist_ok=True)
app.config['USER_FILES_BASE_DIR'] = USER_FILES_BASE_DIR


# --- ডাটাবেজ ও এক্সটেনশন ইনিশিয়ালাইজেশন ---
main_db.init_app(app)

login_manager = LoginManager()
login_manager.login_view = 'auth.login' # লগইন পেজের রুট
login_manager.login_message = "এই পাতাটি অ্যাক্সেস করার জন্য অনুগ্রহ করে লগইন করুন।"
login_manager.login_message_category = "info"
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
        main_db.create_all()
    print("Initialized the database and created tables (if they didn't exist).")

# --- অ্যাপ চালু করার জন্য (Gunicorn এটি সরাসরি ব্যবহার করবে না, তবে লোকাল টেস্টিং এর জন্য) ---
if __name__ == '__main__':
    # ডেভেলপমেন্টের সময় instance ফোল্ডারে SQLite ডাটাবেজ তৈরি হবে যদি APP_DB_URL সেট না করা থাকে
    instance_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance')
    if not os.path.exists(instance_path) and 'sqlite:///' in DATABASE_CONNECTION_STRING:
        os.makedirs(instance_path, exist_ok=True)
        
    with app.app_context(): 
        main_db.create_all() 
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False) # debug=False প্রোডাকশনের জন্য
