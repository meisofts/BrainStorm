# app/models/user.py

from app import db, bcrypt # Import bcrypt here
from flask_login import UserMixin

class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    users = db.relationship('User', backref='role', lazy=True)

    def __repr__(self):
        return f"<Role '{self.name}'>"

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    admin_quizzes = db.relationship('Quiz', backref='admin', lazy=True)

    # --- ADD THESE METHODS ---
    def set_password(self, password):
        self.password = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password, password)
    # --- END ADDITIONS ---

    def __repr__(self):
        return f"<User '{self.username}'>"

    def has_role(self, role_name):
        return self.role.name == role_name
