import os

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'mat_key')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'postgresql://dbuser:dbpassword:5432/brainstorm')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
