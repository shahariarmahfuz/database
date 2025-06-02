# routes.py (আগের "System Cron Job" পদ্ধতির উত্তর থেকে অপরিবর্তিত)
import os
import subprocess # instant_backup ও restore_backup এর জন্য
import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, current_app
from flask_login import login_required, current_user
from models import db, Project
from werkzeug.utils import secure_filename
from utils import perform_project_backup_utility # utils.py থেকে

main_bp = Blueprint('main', __name__, template_folder='templates')

USER_FILES_BASE_DIR_DEFAULT = 'user_files' 
ALLOWED_EXTENSIONS_RESTORE = {'sql'}

def allowed_file_restore(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS_RESTORE

# --- প্রধান রুটগুলো ---
@main_bp.route('/')
@main_bp.route('/home')
@login_required
def home():
    return render_template('home.html', username=current_user.username)

# --- Instant Backup ---
@main_bp.route('/instant_backup', methods=['GET', 'POST'])
@login_required
def instant_backup():
    if request.method == 'POST':
        db_string = request.form.get('db_string_backup')
        if not db_string:
            flash('ডাটাবেজ কানেকশন স্ট্রিং দিন।', 'error')
            return render_template('instant_backup.html')

        temp_backup_dir = current_app.config.get('UPLOAD_FOLDER', 'uploads_temp') # app.py তে UPLOAD_FOLDER আছে
        if not os.path.exists(temp_backup_dir):
            os.makedirs(temp_backup_dir, exist_ok=True)

        backup_file_name = f"instant_backup_{current_user.id}_{datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')}.sql"
        backup_file_path = os.path.join(temp_backup_dir, backup_file_name)

        try:
            pg_dump_command = ['pg_dump', db_string, '-F', 'p', '-f', backup_file_path]
            process = subprocess.run(pg_dump_command, capture_output=True, text=True)

            if process.returncode == 0:
                try:
                    return send_file(backup_file_path, as_attachment=True, download_name='instant_db_backup.sql')
                finally: 
                    if os.path.exists(backup_file_path):
                        os.remove(backup_file_path)
            else:
                flash(f"pg_dump সমস্যা: {process.stderr}", 'error')
        except FileNotFoundError:
            flash("pg_dump কমান্ড পাওয়া যায়নি।", 'error')
        except Exception as e:
            flash(f"একটি সমস্যা হয়েছে: {str(e)}", 'error')
            if os.path.exists(backup_file_path):
                os.remove(backup_file_path)
        return render_template('instant_backup.html')
    return render_template('instant_backup.html')

# --- Restore Backup ---
@main_bp.route('/restore_backup', methods=['GET', 'POST'])
@login_required
def restore_backup():
    if request.method == 'POST':
        db_string = request.form.get('db_string_restore')
        sql_file = request.files.get('sql_file_restore')

        if not db_string or not sql_file or sql_file.filename == '':
            flash('ডাটাবেজ লিংক এবং SQL ফাইল দুটোই দিন।', 'error')
            return render_template('restore_backup.html')

        if allowed_file_restore(sql_file.filename):
            temp_upload_dir = current_app.config.get('UPLOAD_FOLDER', 'uploads_temp')
            if not os.path.exists(temp_upload_dir):
                os.makedirs(temp_upload_dir, exist_ok=True)
            
            filename = secure_filename(sql_file.filename)
            uploaded_file_path = os.path.join(temp_upload_dir, filename)
            
            psql_output = ""
            psql_error = ""
            success = False
            try:
                sql_file.save(uploaded_file_path)
                psql_command = ['psql', db_string, '-f', uploaded_file_path]
                process = subprocess.run(psql_command, capture_output=True, text=True)
                
                psql_output = process.stdout
                psql_error = process.stderr
                if process.returncode == 0:
                    flash('ডাটাবেজ সফলভাবে পুনরুদ্ধার করা হয়েছে (সম্ভবত)।', 'success')
                    success = True
                else:
                    flash(f"psql সমস্যা (Return Code: {process.returncode}): {psql_error}", 'error')
            
            except FileNotFoundError:
                flash("psql কমান্ড পাওয়া যায়নি।", 'error')
            except Exception as e:
                flash(f"একটি সমস্যা হয়েছে: {str(e)}", 'error')
            finally:
                if os.path.exists(uploaded_file_path):
                    os.remove(uploaded_file_path)
            
            return render_template('restore_backup.html', psql_output=psql_output, psql_error=psql_error, success=success)
        else:
            flash('শুধুমাত্র .sql ফাইল অনুমোদিত।', 'error')
    return render_template('restore_backup.html')

# --- Updateable (Scheduled) Backup - Project Management ---
@main_bp.route('/projects')
@login_required
def list_projects():
    projects = Project.query.filter_by(user_id=current_user.id).order_by(Project.project_name).all()
    return render_template('projects.html', projects=projects)

@main_bp.route('/projects/create', methods=['GET', 'POST'])
@login_required
def create_project():
    if request.method == 'POST':
        project_name = request.form.get('project_name')
        if not project_name:
            flash('প্রজেক্টের নাম দিন।', 'error')
        else:
            new_project = Project(project_name=project_name, user_id=current_user.id) 
            try:
                db.session.add(new_project)
                db.session.commit()
                flash('নতুন প্রজেক্ট তৈরি হয়েছে! এখন সেটিংস কনফিগার করুন।', 'success')
                return redirect(url_for('main.project_settings', project_id=new_project.id))
            except Exception as e:
                db.session.rollback()
                flash(f"প্রজেক্ট তৈরিতে সমস্যা: {str(e)}", 'error')
    return render_template('create_project.html')

@main_bp.route('/projects/<int:project_id>/settings', methods=['GET', 'POST'])
@login_required
def project_settings(project_id):
    project = Project.query.filter_by(id=project_id, user_id=current_user.id).first_or_404()
    
    if request.method == 'POST':
        old_db_connection_string = project.db_connection_string
        was_schedule_active = project.is_schedule_active
        
        project.project_name = request.form.get('project_name', project.project_name)
        new_db_connection_string = request.form.get('db_connection_string', '').strip()
        project.db_connection_string = new_db_connection_string if new_db_connection_string else None

        interval_str = request.form.get('backup_interval_minutes')
        try:
            interval = int(interval_str)
            project.backup_interval_minutes = max(5, interval)
            if interval < 5:
                 flash('ন্যূনতম ব্যাকআপ অন্তর ৫ মিনিট। ৫ মিনিট সেট করা হয়েছে।', 'warning')
        except (ValueError, TypeError):
            flash('ব্যাকআপ অন্তর একটি সংখ্যা হতে হবে। আগের মান বহাল আছে।', 'warning')

        new_schedule_status = True if request.form.get('is_schedule_active') == 'on' else False
        project.is_schedule_active = new_schedule_status
        
        trigger_immediate_backup = False
        if project.is_schedule_active and project.db_connection_string:
            if not was_schedule_active: 
                trigger_immediate_backup = True
            elif old_db_connection_string != project.db_connection_string:
                trigger_immediate_backup = True
        
        if trigger_immediate_backup:
            print(f"Project Settings: Triggering immediate backup for Project ID {project.id}...")
            success, new_filename, backup_time, error_msg = perform_project_backup_utility(project, current_app)
            if success:
                project.last_backup_timestamp = backup_time
                project.backup_file_name = new_filename
                project.next_scheduled_backup = backup_time + datetime.timedelta(minutes=project.backup_interval_minutes)
                flash(f'প্রাথমিক ব্যাকআপ সফল হয়েছে ({new_filename}) এবং শিডিউল আপডেট করা হয়েছে।', 'success')
            else:
                flash(f'প্রাথমিক ব্যাকআপ নিতে সমস্যা হয়েছে: {error_msg} পরবর্তী চেষ্টা নির্ধারিত সময়ে হবে।', 'error')
                if project.is_schedule_active: 
                    project.next_scheduled_backup = datetime.datetime.utcnow() + datetime.timedelta(minutes=project.backup_interval_minutes)
        elif project.is_schedule_active and project.db_connection_string:
            base_time_for_next_schedule = project.last_backup_timestamp or datetime.datetime.utcnow()
            project.next_scheduled_backup = base_time_for_next_schedule + \
                                            datetime.timedelta(minutes=project.backup_interval_minutes)
        elif not project.is_schedule_active:
            project.next_scheduled_backup = None

        try:
            db.session.commit()
            if not trigger_immediate_backup : 
                 flash('প্রজেক্ট সেটিংস আপডেট হয়েছে।', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f"সেটিংস আপডেটে সমস্যা: {str(e)}", 'error')
            
    return render_template('project_settings.html', project=project)

@main_bp.route('/projects/<int:project_id>/download_latest_backup')
@login_required
def download_latest_project_backup(project_id):
    project = Project.query.filter_by(id=project_id, user_id=current_user.id).first_or_404()
    if project.backup_file_name:
        user_project_backup_dir = os.path.join(
            current_app.config.get('USER_FILES_BASE_DIR', USER_FILES_BASE_DIR_DEFAULT), 
            str(current_user.id), 
            'projects', 
            str(project.id)
        )
        file_path = os.path.join(user_project_backup_dir, project.backup_file_name)
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True, download_name=f"{secure_filename(project.project_name)}_backup.sql")
        else:
            flash(f'ব্যাকআপ ফাইল ({project.backup_file_name}) খুঁজে পাওয়া যায়নি।', 'error')
    else:
        flash('এই প্রজেক্টের জন্য কোনো ব্যাকআপ তৈরি হয়নি।', 'error')
    return redirect(url_for('main.project_settings', project_id=project.id))
