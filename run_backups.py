# run_backups.py (আগের উত্তর থেকে অপরিবর্তিত)
import os
import sys
import datetime

try:
    from app import app, main_db as db 
    from models import Project 
    from utils import perform_project_backup_utility 
except ImportError as e:
    print(f"Error importing modules. Ensure this script can find your Flask app and its components.")
    print(f"Details: {e}")
    print(f"Current sys.path: {sys.path}")
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
        print(f"Added {current_dir} to sys.path. Please try running again if imports fail.")
    # Re-raise or exit if critical imports failed for app context
    if 'app' not in globals() or 'db' not in globals() or 'Project' not in globals() or 'perform_project_backup_utility' not in globals():
        print("Critical modules could not be imported. Exiting.")
        exit(1)


def run_scheduled_tasks():
    with app.app_context():
        now = datetime.datetime.utcnow()
        
        projects_to_backup = Project.query.filter(
            Project.is_schedule_active == True,
            Project.db_connection_string != None,
            Project.db_connection_string != '',
            Project.next_scheduled_backup != None,
            Project.next_scheduled_backup <= now
        ).all()

        print(f"CRON SCRIPT ({now.isoformat()}): Found {len(projects_to_backup)} project(s) due for backup.")
        
        backup_count = 0
        for project in projects_to_backup:
            print(f"CRON: Processing Project ID {project.id} - {project.project_name} (Owner ID: {project.user_id})")
            
            success, new_filename, backup_time, error_msg = perform_project_backup_utility(project, app) 
            
            if success:
                project.last_backup_timestamp = backup_time
                project.backup_file_name = new_filename
                print(f"CRON: Success - Project {project.id} backed up ({new_filename}).")
                backup_count += 1
            else:
                print(f"CRON: Error backing up Project ID {project.id}: {error_msg}")
            
            project.next_scheduled_backup = (backup_time or now) + \
                                             datetime.timedelta(minutes=project.backup_interval_minutes)
            try:
                db.session.commit()
            except Exception as e_commit:
                db.session.rollback()
                print(f"CRON: Error committing DB changes for project {project.id}: {e_commit}")
        
        print(f"CRON SCRIPT: Finished processing. Successfully backed up {backup_count} project(s).")

if __name__ == '__main__':
    print(f"Starting scheduled backup script at {datetime.datetime.now()}...")
    # একটি app_context তৈরি করা ভালো যদি app অবজেক্ট সরাসরি ইম্পোর্ট না হয় বা sys.path অ্যাডজাস্ট করতে হয়
    # তবে, from app import app... করা হলে, app.app_context() সরাসরি কাজ করার কথা।
    if 'app' in globals():
         run_scheduled_tasks()
    else:
        print("Flask app object not available for run_scheduled_tasks. Ensure imports are correct.")
    print(f"Scheduled backup script finished at {datetime.datetime.now()}.")
