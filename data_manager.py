# data_manager.py
import json
import os
import datetime
import uuid # ইউনিক আইডি তৈরির জন্য ব্যবহার করা যেতে পারে
import fcntl # ফাইল লকিং এর জন্য (Linux/macOS)
from werkzeug.security import generate_password_hash, check_password_hash

# DATA_FILE_PATH এনভায়রনমেন্ট ভেরিয়েবল থেকে নেওয়া উচিত অথবা app.py তে কনফিগার করা উচিত
# এবং Render.com এ Persistent Disk এর পাথ হবে।
# আপাতত, app.py তে যে DATA_JSON_PATH কনফিগার করা হবে, সেটি এখানে ব্যবহার করা হবে।
# এই ফাইলটি সরাসরি DATA_JSON_PATH ব্যবহার করবে না, বরং app.py থেকে পাথ পাবে।

class DataManager:
    def __init__(self, data_file_path):
        self.data_file_path = data_file_path
        self.lock_file_path = data_file_path + ".lock"
        self._ensure_data_file()

    def _ensure_data_file(self):
        if not os.path.exists(self.data_file_path):
            # প্রাথমিক খালি ডেটা স্ট্রাকচার
            initial_data = {
                "users": {},  # key: user_id (str), value: user_object
                "projects": {}, # key: project_id (str), value: project_object
                "next_user_numeric_id": 1 # শুধুমাত্র সিম্পল আইডি জেনারেশনের জন্য
            }
            self._write_data(initial_data)
            print(f"Initialized data file at: {self.data_file_path}")

    def _read_data(self):
        try:
            with open(self.data_file_path, 'r', encoding='utf-8') as f:
                # ফাইল খালি থাকলে বা json না থাকলে এরর হতে পারে
                content = f.read()
                if not content:
                    return {"users": {}, "projects": {}, "next_user_numeric_id": 1}
                return json.loads(content)
        except FileNotFoundError:
            self._ensure_data_file() # যদি কোনো কারণে ফাইল মুছে যায়, আবার তৈরি করবে
            return {"users": {}, "projects": {}, "next_user_numeric_id": 1}
        except json.JSONDecodeError:
            print(f"ERROR: Could not decode JSON from {self.data_file_path}. File might be corrupted.")
            # একটি খালি স্ট্রাকচার রিটার্ন করা বা এরর রেইজ করা যেতে পারে
            # আপাতত, ডেটা নষ্ট হওয়া থেকে বাঁচাতে খালি স্ট্রাকচার রিটার্ন করছি
            return {"users": {}, "projects": {}, "next_user_numeric_id": 1}


    def _write_data(self, data):
        # ফাইল লকিং (বেসিক)
        try:
            with open(self.lock_file_path, 'w') as lock_file:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX) # Exclusive lock
                try:
                    with open(self.data_file_path, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=4, ensure_ascii=False, default=str) # default=str for datetime
                finally:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN) # Unlock
                    if os.path.exists(self.lock_file_path):
                        try: os.remove(self.lock_file_path)
                        except OSError: pass # যদি অন্য কোনো প্রসেস মুছে ফেলে
        except Exception as e:
            print(f"Error writing data with lock: {e}")
            # এখানে আরও শক্তিশালী এরর হ্যান্ডলিং প্রয়োজন হতে পারে


    # --- User Management ---
    def create_user(self, username, password, email=None):
        data = self._read_data()
        
        # ইউজারনেম ইউনিক কিনা চেক করুন
        for user_data in data["users"].values():
            if user_data["username"] == username:
                return None # ইউজারনেম ইতিমধ্যে আছে

        # ইমেইল ইউনিক কিনা চেক করুন (যদি দেওয়া হয়)
        if email:
            for user_data in data["users"].values():
                if user_data.get("email") == email:
                    return None # ইমেইল ইতিমধ্যে আছে

        # নতুন ইউজার আইডি তৈরি
        # user_id = str(data.get("next_user_numeric_id", 1)) # সিম্পল ইনক্রিমেন্টিং আইডি
        user_id = str(uuid.uuid4()) # UUID ব্যবহার করা ভালো
        
        new_user = {
            "id": user_id,
            "username": username,
            "email": email,
            "password_hash": generate_password_hash(password)
            # "projects": [] # প্রজেক্টগুলো আলাদাভাবে "projects" ডিকশনারিতে থাকবে
        }
        data["users"][user_id] = new_user
        # data["next_user_numeric_id"] = int(user_id) + 1 # যদি ইনক্রিমেন্টিং আইডি হয়
        
        self._write_data(data)
        return new_user # অথবা শুধু user_id রিটার্ন করতে পারেন

    def get_user_by_username(self, username):
        data = self._read_data()
        for user_data in data["users"].values():
            if user_data["username"] == username:
                return user_data # ডিকশনারি রিটার্ন করবে
        return None

    def get_user_by_id(self, user_id):
        data = self._read_data()
        return data["users"].get(str(user_id)) # আইডি স্ট্রিং হিসেবে ব্যবহার করা হচ্ছে

    # --- Project Management ---
    def create_project(self, user_id, project_name):
        data = self._read_data()
        project_id = str(uuid.uuid4()) # প্রজেক্টের জন্য UUID

        new_project = {
            "id": project_id,
            "user_id": str(user_id),
            "project_name": project_name,
            "db_connection_string": None,
            "backup_interval_minutes": 60, # ডিফল্ট
            "last_backup_timestamp": None, # ISO 8601 format string e save kora bhalo
            "backup_file_name": None,
            "next_scheduled_backup": None, # ISO 8601 format string
            "is_schedule_active": False
        }
        data["projects"][project_id] = new_project
        self._write_data(data)
        return new_project # অথবা project_id

    def get_projects_by_user_id(self, user_id):
        data = self._read_data()
        user_projects = []
        for project_data in data["projects"].values():
            if project_data["user_id"] == str(user_id):
                # datetime string থেকে datetime object এ রূপান্তর (যদি প্রয়োজন হয়)
                if project_data.get("last_backup_timestamp"):
                    try: project_data["last_backup_timestamp_dt"] = datetime.datetime.fromisoformat(project_data["last_backup_timestamp"].replace('Z', '+00:00'))
                    except: project_data["last_backup_timestamp_dt"] = None
                else: project_data["last_backup_timestamp_dt"] = None

                if project_data.get("next_scheduled_backup"):
                    try: project_data["next_scheduled_backup_dt"] = datetime.datetime.fromisoformat(project_data["next_scheduled_backup"].replace('Z', '+00:00'))
                    except: project_data["next_scheduled_backup_dt"] = None
                else: project_data["next_scheduled_backup_dt"] = None
                
                user_projects.append(project_data)
        return user_projects

    def get_project_by_id(self, project_id, user_id=None): # user_id ঐচ্ছিক, অথরাইজেশনের জন্য
        data = self._read_data()
        project_data = data["projects"].get(str(project_id))
        if project_data:
            if user_id and project_data["user_id"] != str(user_id):
                return None # অথরাইজেশন ফেইল
            # datetime string থেকে datetime object
            if project_data.get("last_backup_timestamp"):
                try: project_data["last_backup_timestamp_dt"] = datetime.datetime.fromisoformat(project_data["last_backup_timestamp"].replace('Z', '+00:00'))
                except: project_data["last_backup_timestamp_dt"] = None
            else: project_data["last_backup_timestamp_dt"] = None
            if project_data.get("next_scheduled_backup"):
                try: project_data["next_scheduled_backup_dt"] = datetime.datetime.fromisoformat(project_data["next_scheduled_backup"].replace('Z', '+00:00'))
                except: project_data["next_scheduled_backup_dt"] = None
            else: project_data["next_scheduled_backup_dt"] = None

            return project_data
        return None

    def update_project(self, project_id, updates): # updates একটি ডিকশনারি হবে
        data = self._read_data()
        project_data = data["projects"].get(str(project_id))
        if project_data:
            for key, value in updates.items():
                if key in project_data:
                    # datetime অবজেক্ট হলে ISO ফরম্যাটে স্ট্রিং হিসেবে সেভ করা
                    if isinstance(value, datetime.datetime):
                        project_data[key] = value.isoformat() + "Z" # UTC বোঝানোর জন্য
                    else:
                        project_data[key] = value
            self._write_data(data)
            return True
        return False

    def get_all_active_due_projects(self, current_time_utc):
        data = self._read_data()
        due_projects = []
        for project_data in data["projects"].values():
            if project_data.get("is_schedule_active") and project_data.get("db_connection_string"):
                next_backup_str = project_data.get("next_scheduled_backup")
                if next_backup_str:
                    try:
                        # Z থাকলে সেটি UTC বোঝায়, fromisoformat হ্যান্ডেল করতে পারে
                        # অথবা +00:00 তে পরিবর্তন করা যেতে পারে।
                        next_backup_time = datetime.datetime.fromisoformat(next_backup_str.replace('Z', '+00:00'))
                        # নিশ্চিত করুন current_time_utc ও timezone aware (UTC)
                        if next_backup_time <= current_time_utc:
                            due_projects.append(project_data)
                    except ValueError:
                        print(f"Warning: Could not parse next_scheduled_backup for project {project_data.get('id')}: {next_backup_str}")
        return due_projects

# --- UserMixin এর জন্য প্রয়োজনীয় কিছু মেথড (Flask-Login এর জন্য) ---
# এগুলি User ডিকশনারির সাথে কাজ করার জন্য Flask-Login এর UserMixin এর মতো আচরণ করবে
class JSONUser:
    def __init__(self, user_dict):
        self._user_dict = user_dict
        self.id = user_dict.get('id') # Flask-Login এর জন্য id অ্যাট্রিবিউট প্রয়োজন

    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return True # এখানে আপনি চাইলে is_active ফিল্ড যোগ করতে পারেন ইউজার ডেটাতে

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id) # আইডি স্ট্রিং হিসেবে রিটার্ন করতে হবে

    def check_password(self, password_to_check):
        return check_password_hash(self._user_dict.get("password_hash", ""), password_to_check)
    
    # current_user.username ব্যবহার করার জন্য
    @property
    def username(self):
        return self._user_dict.get('username')
