import os
from app import create_app, db
from app.models.user import User, Role
from app.models.quiz import Quiz, Question, Contestant
from datetime import datetime, timedelta
from flask_bcrypt import Bcrypt
from dotenv import load_dotenv

load_dotenv() # Load environment variables

app = create_app()
bcrypt = Bcrypt(app)

def seed_data():
    with app.app_context():
        print("Seeding database...")
        db.drop_all() # Drop all tables to ensure clean slate
        db.create_all() # Recreate all tables

        # Create Roles
        superadmin_role = Role.query.filter_by(name='superadmin').first()
        if not superadmin_role:
            superadmin_role = Role(name='superadmin')
            db.session.add(superadmin_role)

        admin_role = Role.query.filter_by(name='admin').first()
        if not admin_role:
            admin_role = Role(name='admin')
            db.session.add(admin_role)

        moderator_role = Role.query.filter_by(name='moderator').first()
        if not moderator_role:
            moderator_role = Role(name='moderator')
            db.session.add(moderator_role)
        db.session.commit()

        # Create Users
        # Superadmin
        superadmin_user = User.query.filter_by(username='superadmin').first()
        if not superadmin_user:
            hashed_password = bcrypt.generate_password_hash('superpass').decode('utf-8')
            superadmin_user = User(username='superadmin', email='superadmin@example.com', password=hashed_password, role=superadmin_role)
            db.session.add(superadmin_user)

        # Admin
        admin_user = User.query.filter_by(username='adminuser').first()
        if not admin_user:
            hashed_password = bcrypt.generate_password_hash('adminpass').decode('utf-8')
            admin_user = User(username='adminuser', email='admin@example.com', password=hashed_password, role=admin_role)
            db.session.add(admin_user)

        # Moderator
        mod_user = User.query.filter_by(username='moduser').first()
        if not mod_user:
            hashed_password = bcrypt.generate_password_hash('modpass').decode('utf-8')
            mod_user = User(username='moduser', email='moderator@example.com', password=hashed_password, role=moderator_role)
            db.session.add(mod_user)
        db.session.commit()

        # Create Sample Quiz and Questions
        sample_quiz = Quiz.query.filter_by(title='General Knowledge Quiz').first()
        if not sample_quiz:
            quiz_date = datetime.now() + timedelta(days=7)
            sample_quiz = Quiz(
                title='General Knowledge Quiz',
                description='A quiz to test your general knowledge.',
                quiz_date=quiz_date,
                admin_id=admin_user.id
            )
            db.session.add(sample_quiz)
            db.session.commit()

            question1 = Question(
                quiz_id=sample_quiz.id,
                question_text='What is the capital of France?',
                option_a='Berlin',
                option_b='Madrid',
                option_c='Paris',
                option_d='Rome',
                correct_answer='c'
            )
            question2 = Question(
                quiz_id=sample_quiz.id,
                question_text='Which planet is known as the Red Planet?',
                option_a='Earth',
                option_b='Mars',
                option_c='Jupiter',
                option_d='Venus',
                correct_answer='b'
            )
            db.session.add_all([question1, question2])
            db.session.commit()

        print("Seeding complete.")

if __name__ == '__main__':
    seed_data()
