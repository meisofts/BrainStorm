import os

class Config:
    # SECRET_KEY = os.getenv('SECRET_KEY', 'your_key')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'postgres://u9gvgp6uk5os24:p118f9ebab301230aede670e5cbd2ad81fae82e92f9c5c7d765073d4cef505439@c7itisjfjj8ril.cluster-czrs8kj4isg7.us-east-1.rds.amazonaws.com:5432/d4ej2m21agsabn')
    SQLALCHEMY_TRACK_MODIFICATIONS = False


#.env SECRET_KEY="you_key"  ==> Key for .env file
