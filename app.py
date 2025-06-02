import os
from flask import Flask, g # g ব্যবহার করা যেতে পারে data_manager instance রাখার জন্য
from flask_login import LoginManager
from data_manager import DataManager, JSONUser # নতুন DataManager ও JSONUser ক্লাস
from auth import auth_bp
from routes import main_bp

# --- Flask App ইনিশিয়ালাইজেশন ---
app = Flask(__name__) 

# --- কনফিগারেশন ---
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'fallback_json_super_secret_key_12345')

# data.json ফাইলের পাথ (Render.com এ Persistent Disk এর পাথ হবে)
DATA_JSON_FILE_PATH = os.environ.get('DATA_JSON_PATH', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'data.json'))
app.config['DATA_JSON_PATH'] = DATA_JSON_FILE_PATH

# data.json এর ডিরেক্টরি তৈরি করা (যদি না থাকে)
data_json_dir = os.path.dirname(DATA_JSON_FILE_PATH)
if not os.path.exists(data_json_dir):
    try:
        os.makedirs(data_json_dir, exist_ok=True)
    except OSError as e:
        print(f"CRITICAL: Error creating directory for data.json at {data_json_dir}: {e}")

# আপলোড ফোল্ডার (অস্থায়ী ফাইল রাখার জন্য)
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads_temp')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ইউজার-স্পেসিফিক ফাইল (শিডিউলড ব্যাকআপ) রাখার মূল ফোল্ডার
USER_FILES_BASE_DIR = os.environ.get('USER_FILES_STORAGE_DIR', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'user_files_local_dev'))
if not os.path.exists(USER_FILES_BASE_DIR):
    os.makedirs(USER_FILES_BASE_DIR, exist_ok=True)
app.config['USER_FILES_BASE_DIR'] = USER_FILES_BASE_DIR

# --- DataManager ইনিশিয়ালাইজেশন ---
# অ্যাপ চালু হওয়ার সময় একবার DataManager তৈরি করা এবং g অবজেক্টে রাখা যেতে পারে,
# অথবা প্রতিটি রিকোয়েস্টে নতুন করে তৈরি করা যেতে পারে।
# গ্লোবাল ইনস্ট্যান্স তৈরি করছি, তবে রিকোয়েস্ট কনটেক্সটে ব্যবহার করা ভালো হতে পারে।
# data_manager_instance = DataManager(app.config['DATA_JSON_PATH'])

@app.before_request
def before_request():
    # প্রতিটি রিকোয়েস্টের জন্য g.data_manager এ DataManager এর একটি ইনস্ট্যান্স রাখুন
    # এটি ফাইল লকিং এর জন্য ভালো হতে পারে যদি প্রতিটি রিকোয়েস্ট আলাদা ইনস্ট্যান্স পায়
    # তবে, একই ইনস্ট্যান্স ব্যবহার করাই ভালো, যাতে next_id গুলোর সিঙ্ক্রোনাইজেশন ঠিক থাকে (যদি থাকে)
    # অথবা DataManager ক্লাসটিকে singleton হিসেবে ডিজাইন করা যেতে পারে।
    # আপাতত, একটি গ্লোবাল ইনস্ট্যান্স (যদি তৈরি করা হয়) বা প্রতি রিকোয়েস্টে নতুন ইনস্ট্যান্স।
    # সরলতার জন্য, আমরা প্রতিটি রুটে DataManager তৈরি করতে পারি, অথবা Flask 'g' অবজেক্ট ব্যবহার করতে পারি।
    # Flask 'g' ব্যবহার করা ভালো:
    if 'data_manager' not in g:
        g.data_manager = DataManager(current_app.config['DATA_JSON_PATH'])


# --- Flask-Login ইনিশিয়ালাইজেশন ---
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = "এই পাতাটি অ্যাক্সেস করার জন্য অনুগ্রহ করে লগইন করুন।"
login_manager.login_message_category = "info"
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    # রিকোয়েস্ট কনটেক্সট থেকে data_manager নিন
    # from flask import current_app
    # data_manager = DataManager(current_app.config['DATA_JSON_PATH']) 
    # উপরের g.data_manager ব্যবহার করলে:
    data_manager = getattr(g, 'data_manager', None)
    if not data_manager: # যদি কোনো কারণে g তে না থাকে (যেমন CLI কমান্ড থেকে)
        from flask import current_app
        data_manager = DataManager(current_app.config['DATA_JSON_PATH'])

    user_dict = data_manager.get_user_by_id(user_id)
    if user_dict:
        return JSONUser(user_dict) # JSONUser ক্লাস UserMixin এর মতো কাজ করবে
    return None

# --- ব্লুপ্রিন্ট রেজিস্টার করা ---
# ব্লুপ্রিন্টগুলো app কনটেক্সট তৈরি হওয়ার পর রেজিস্টার করা ভালো, যাতে তারা g.data_manager পায়
# অথবা ব্লুপ্রিন্টের ভেতরে current_app.data_manager ব্যবহার করতে হবে
# from flask import current_app # ব্লুপ্রিন্টের ভেতরে current_app.data_manager ব্যবহার করার জন্য

app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(main_bp, url_prefix='/')


# --- CLI কমান্ড (init-db এর পরিবর্তে data.json ফাইল তৈরি নিশ্চিত করা) ---
@app.cli.command("init-datafile")
def init_datafile_command():
    """data.json ফাইল তৈরি এবং প্রাথমিক কাঠামো নিশ্চিত করে।"""
    print(f"Ensuring data file exists at: {app.config['DATA_JSON_PATH']}")
    # DataManager ইনিশিয়ালাইজ করলেই ফাইল তৈরি হয়ে যাবে যদি না থাকে
    _ = DataManager(app.config['DATA_JSON_PATH']) 
    print("Data file check/initialization complete.")

# --- অ্যাপ চালানো ---
if __name__ == '__main__':
    # data.json ফাইল তৈরি (যদি না থাকে) DataManager ইনিশিয়ালাইজেশনের মাধ্যমে হবে
    # _ = DataManager(app.config['DATA_JSON_PATH']) # অ্যাপ চালু হওয়ার সময় একবার কল করা

    # debug=False প্রোডাকশনের জন্য
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
