# models.py (আগের উত্তর থেকে অপরিবর্তিত)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    password_hash = db.Column(db.String(256), nullable=False)
    projects = db.relationship('Project', backref='owner', lazy=True, cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    project_name = db.Column(db.String(100), nullable=False)
    db_connection_string = db.Column(db.String(500), nullable=True)
    backup_interval_minutes = db.Column(db.Integer, default=60, nullable=False)
    last_backup_timestamp = db.Column(db.DateTime, nullable=True)
    backup_file_name = db.Column(db.String(255), nullable=True)
    next_scheduled_backup = db.Column(db.DateTime, nullable=True)
    is_schedule_active = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f'<Project {self.project_name}>'
