import os

class Config:
    # SECRET_KEY = os.getenv('SECRET_KEY', 'your_key')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'postgresql://yourDBName:yourDBPass@localhost:5432/yourDB')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
