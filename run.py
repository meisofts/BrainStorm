import os
from app import create_app, db
from app.models.user import User, Role
from app.models.quiz import Quiz, Question, Contestant
from dotenv import load_dotenv

load_dotenv() # Load environment variables from .env file

app = create_app()

@app.shell_context_processor
def make_shell_context():
    return dict(db=db, User=User, Role=Role, Quiz=Quiz, Question=Question, Contestant=Contestant)

if __name__ == '__main__':
    with app.app_context():
        db.create_all() # Create database tables
        # Initial seeding if needed (can be run via seeder.py)
    app.run(debug=os.getenv('FLASK_DEBUG', 'True') == 'True') # Set FLASK_DEBUG in .env or shell
