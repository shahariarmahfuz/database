# utils.py (আগের উত্তর থেকে অপরিবর্তিত)
import os
import subprocess
import datetime

USER_FILES_BASE_DIR_DEFAULT_IN_UTILS = 'user_files' 

def perform_project_backup_utility(project, app_instance_for_config):
    if not project.db_connection_string:
        return False, None, None, "ডাটাবেজ কানেকশন স্ট্রিং সেট করা নেই।"

    current_backup_time = datetime.datetime.utcnow()
    
    user_project_backup_dir = os.path.join(
        app_instance_for_config.config.get('USER_FILES_BASE_DIR', USER_FILES_BASE_DIR_DEFAULT_IN_UTILS),
        str(project.user_id), 
        'projects',
        str(project.id)
    )
    if not os.path.exists(user_project_backup_dir):
        os.makedirs(user_project_backup_dir, exist_ok=True)

    new_backup_filename = f"backup_{current_backup_time.strftime('%Y%m%d%H%M%S')}.sql"
    new_backup_file_path = os.path.join(user_project_backup_dir, new_backup_filename)

    if project.backup_file_name:
        old_backup_file_path = os.path.join(user_project_backup_dir, project.backup_file_name)
        if os.path.exists(old_backup_file_path):
            try:
                os.remove(old_backup_file_path)
                print(f"Utility: Deleted old backup: {old_backup_file_path}")
            except Exception as e_del:
                print(f"Utility: Could not delete old backup {old_backup_file_path}: {e_del}")
    
    pg_dump_command = ['pg_dump', project.db_connection_string, '-F', 'p', '-f', new_backup_file_path]
    
    try:
        process = subprocess.run(pg_dump_command, capture_output=True, text=True, check=False)
        if process.returncode == 0:
            print(f"Utility: Successfully ran pg_dump for {project.project_name} to {new_backup_file_path}")
            return True, new_backup_filename, current_backup_time, None
        else:
            error_msg = f"pg_dump এরর (Code: {process.returncode}): {process.stderr}"
            print(f"Utility: Error pg_dump for {project.project_name}: {error_msg}")
            if os.path.exists(new_backup_file_path): 
                try: os.remove(new_backup_file_path)
                except Exception as e_rem_fail: print(f"Utility: Error deleting failed backup file {new_backup_file_path}: {e_rem_fail}")
            return False, None, None, error_msg
            
    except FileNotFoundError:
        error_msg = "pg_dump কমান্ড খুঁজে পাওয়া যায়নি।"
        print(f"Utility: FileNotFoundError for pg_dump (Project: {project.project_name})")
        return False, None, None, error_msg
    except Exception as e:
        error_msg = f"ব্যাকআপে অপ্রত্যাশিত সমস্যা: {str(e)}"
        print(f"Utility: Exception during backup (Project: {project.project_name}): {str(e)}")
        if os.path.exists(new_backup_file_path):
            try: os.remove(new_backup_file_path)
            except Exception as e_rem_ex: print(f"Utility: Error deleting exception backup file {new_backup_file_path}: {e_rem_ex}")
        return False, None, None, error_msg
