# run_backups.py
import os
import sys
import datetime
# subprocess utils.py এর মাধ্যমে ব্যবহৃত হচ্ছে

# Flask অ্যাপ্লিকেশনের পাথ sys.path এ যোগ করার প্রয়োজন হতে পারে
# sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app import app # app.py থেকে app অবজেক্ট ইম্পোর্ট করুন
    from data_manager import DataManager # data_manager.py থেকে
    from utils import perform_project_backup_utility
except ImportError as e:
    # ... (আগের মতোই এরর হ্যান্ডলিং) ...
    print(f"Error importing modules in run_backups.py: {e}")
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
        print(f"Added {current_dir} to sys.path. Please try running again.")
    exit(1)


def run_scheduled_tasks_json():
    # Flask অ্যাপ্লিকেশনের কনটেক্সট তৈরি করুন যাতে কনফিগারেশন (DATA_JSON_PATH) অ্যাক্সেস করা যায়
    with app.app_context():
        data_manager = DataManager(app.config['DATA_JSON_PATH'])
        now_utc = datetime.datetime.now(datetime.timezone.utc) # Timezone aware current time

        # DataManager থেকে ডিউ প্রজেক্টগুলো আনা
        projects_to_backup = data_manager.get_all_active_due_projects(now_utc)

        print(f"CRON SCRIPT (JSON) ({now_utc.isoformat()}): Found {len(projects_to_backup)} project(s) due for backup.")
        
        backup_count = 0
        for project_dict in projects_to_backup: # এখন এটি ডিকশনারি
            print(f"CRON: Processing Project ID {project_dict['id']} - {project_dict['project_name']} (Owner ID: {project_dict['user_id']})")
            
            # perform_project_backup_utility একটি অবজেক্ট আশা করতে পারে, তাই ডিকশনারিকে একটি সিম্পল অবজেক্টে রূপান্তর
            class TempProjectHolder:
                 def __init__(self, p_dict): self.__dict__.update(p_dict)
            
            project_obj_for_util = TempProjectHolder(project_dict)

            success, new_filename, backup_time_utc, error_msg = perform_project_backup_utility(project_obj_for_util, app) 
            
            updates_for_json = {}
            if success:
                updates_for_json["last_backup_timestamp"] = backup_time_utc # datetime object
                updates_for_json["backup_file_name"] = new_filename
                print(f"CRON: Success - Project {project_dict['id']} backed up ({new_filename}).")
                backup_count += 1
            else:
                print(f"CRON: Error backing up Project ID {project_dict['id']}: {error_msg}")
            
            # পরবর্তী ব্যাকআপের সময় ক্যালকুলেট করুন (UTC তে)
            next_backup_base_time = backup_time_utc if success else now_utc
            updates_for_json["next_scheduled_backup"] = next_backup_base_time + \
                                             datetime.timedelta(minutes=project_dict["backup_interval_minutes"])
            
            try:
                data_manager.update_project(project_dict['id'], updates_for_json)
            except Exception as e_commit:
                print(f"CRON: Error updating project data in JSON for project {project_dict['id']}: {e_commit}")
        
        print(f"CRON SCRIPT (JSON): Finished processing. Successfully backed up {backup_count} project(s).")

if __name__ == '__main__':
    print(f"Starting scheduled backup script (JSON version) at {datetime.datetime.now()}...")
    if 'app' in globals(): # নিশ্চিত করুন app ইম্পোর্ট হয়েছে
         run_scheduled_tasks_json()
    else:
        print("Flask app object not available. Ensure imports in run_backups.py are correct and app.py is accessible.")
    print(f"Scheduled backup script (JSON version) finished at {datetime.datetime.now()}.")
