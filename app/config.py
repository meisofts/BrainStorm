import os

class Config:
    # SECRET_KEY = os.getenv('SECRET_KEY', 'your_key')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'postgresql://yourDBName:yourDBPass@localhost:5432/yourDB')
    SQLALCHEMY_TRACK_MODIFICATIONS = False


<<<<<<< HEAD
#.env SECRET_KEY="your_key"  ==> Key for .env file
=======
#.env SECRET_KEY="you_key"  ==> Key for .env file
>>>>>>> 5fb4167a4de3fb9fa01850184040d4c1cbcae939
