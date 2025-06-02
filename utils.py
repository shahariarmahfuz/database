# utils.py (আগের মতোই, user_id ব্যবহারের বিষয়টি নিশ্চিত করা হয়েছে)
import os
import subprocess
import datetime

USER_FILES_BASE_DIR_DEFAULT_IN_UTILS = 'user_files' 

def perform_project_backup_utility(project_obj, app_instance_for_config): # project_obj এখন ডিকশনারি বা সিম্পল অবজেক্ট হতে পারে
    # project_obj থেকে 'db_connection_string', 'user_id', 'id', 'backup_file_name', 'project_name' অ্যাট্রিবিউটগুলো অ্যাক্সেস করতে হবে
    # যদি project_obj একটি ডিকশনারি হয়: project_obj.get('db_connection_string')
    # যদি এটি একটি অবজেক্ট হয় (যেমন TempProjectHolder): project_obj.db_connection_string

    db_connection_string = getattr(project_obj, 'db_connection_string', None) or project_obj.get('db_connection_string')
    if not db_connection_string:
        return False, None, None, "ডাটাবেজ কানেকশন স্ট্রিং সেট করা নেই।"

    current_backup_time = datetime.datetime.utcnow()
    
    # project_obj.user_id এবং project_obj.id ব্যবহার
    user_id_val = getattr(project_obj, 'user_id', None) or project_obj.get('user_id')
    project_id_val = getattr(project_obj, 'id', None) or project_obj.get('id')
    project_name_val = getattr(project_obj, 'project_name', 'unknown_project') or project_obj.get('project_name', 'unknown_project')
    current_backup_file_name_val = getattr(project_obj, 'backup_file_name', None) or project_obj.get('backup_file_name')


    user_project_backup_dir = os.path.join(
        app_instance_for_config.config.get('USER_FILES_BASE_DIR', USER_FILES_BASE_DIR_DEFAULT_IN_UTILS),
        str(user_id_val), 
        'projects',
        str(project_id_val)
    )
    if not os.path.exists(user_project_backup_dir):
        os.makedirs(user_project_backup_dir, exist_ok=True)

    new_backup_filename = f"backup_{current_backup_time.strftime('%Y%m%d%H%M%S')}.sql"
    new_backup_file_path = os.path.join(user_project_backup_dir, new_backup_filename)

    if current_backup_file_name_val:
        old_backup_file_path = os.path.join(user_project_backup_dir, current_backup_file_name_val)
        if os.path.exists(old_backup_file_path):
            try:
                os.remove(old_backup_file_path)
                print(f"Utility: Deleted old backup: {old_backup_file_path}")
            except Exception as e_del:
                print(f"Utility: Could not delete old backup {old_backup_file_path}: {e_del}")
    
    pg_dump_command = ['pg_dump', db_connection_string, '-F', 'p', '-f', new_backup_file_path]
    
    try:
        process = subprocess.run(pg_dump_command, capture_output=True, text=True, check=False)
        if process.returncode == 0:
            print(f"Utility: Successfully ran pg_dump for {project_name_val} to {new_backup_file_path}")
            return True, new_backup_filename, current_backup_time, None
        else:
            error_msg = f"pg_dump এরর (Code: {process.returncode}): {process.stderr}"
            print(f"Utility: Error pg_dump for {project_name_val}: {error_msg}")
            if os.path.exists(new_backup_file_path): 
                try: os.remove(new_backup_file_path)
                except Exception as e_rem_fail: print(f"Utility: Error deleting failed backup file {new_backup_file_path}: {e_rem_fail}")
            return False, None, None, error_msg
            
    except FileNotFoundError:
        error_msg = "pg_dump কমান্ড খুঁজে পাওয়া যায়নি।"
        print(f"Utility: FileNotFoundError for pg_dump (Project: {project_name_val})")
        return False, None, None, error_msg
    except Exception as e:
        error_msg = f"ব্যাকআপে অপ্রত্যাশিত সমস্যা: {str(e)}"
        print(f"Utility: Exception during backup (Project: {project_name_val}): {str(e)}")
        if os.path.exists(new_backup_file_path):
            try: os.remove(new_backup_file_path)
            except Exception as e_rem_ex: print(f"Utility: Error deleting exception backup file {new_backup_file_path}: {e_rem_ex}")
        return False, None, None, error_msg
