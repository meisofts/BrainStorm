from app import db
from datetime import datetime

class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    quiz_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    questions = db.relationship('Question', backref='quiz', lazy=True, cascade='all, delete-orphan')
    contestants = db.relationship('Contestant', backref='quiz', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Quiz '{self.title}'>"

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    option_a = db.Column(db.String(200), nullable=False)
    option_b = db.Column(db.String(200), nullable=False)
    option_c = db.Column(db.String(200), nullable=False)
    option_d = db.Column(db.String(200), nullable=False)
    correct_answer = db.Column(db.String(1), nullable=False) # 'a', 'b', 'c', 'd'
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    def __repr__(self):
        return f"<Question '{self.question_text[:30]}...'>"

class Contestant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=True) # Optional, for future use
    score = db.Column(db.Integer, default=0)
    submitted_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    answers = db.relationship('ContestantAnswer', backref='contestant', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Contestant '{self.name}'>"

class ContestantAnswer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    contestant_id = db.Column(db.Integer, db.ForeignKey('contestant.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    selected_option = db.Column(db.String(1), nullable=False) # 'a', 'b', 'c', 'd'
    is_correct = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    question = db.relationship('Question', backref='contestant_answers', lazy=True)

    def __repr__(self):
        return f"<ContestantAnswer Contestant:{self.contestant_id} Question:{self.question_id} Selected:{self.selected_option}>"
