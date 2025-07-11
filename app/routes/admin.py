# app/routes/admin.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db, bcrypt
from app.models.user import User, Role
from app.models.quiz import Quiz, Question, Contestant
from app.routes.auth import role_required
from datetime import datetime

admin_bp = Blueprint('admin', __name__)

# Define a specific decorator for superadmin access
def superadmin_required(f):
    return role_required('superadmin')(f)

@admin_bp.route('/dashboard')
@role_required('admin', 'superadmin')
def dashboard():
    total_quizzes = Quiz.query.count()
    total_users = User.query.count()
    total_contestants = Contestant.query.count()
    upcoming_quizzes = Quiz.query.filter(Quiz.quiz_date > datetime.now()).order_by(Quiz.quiz_date.asc()).limit(5).all()
    return render_template('admin/dashboard.html',
                           total_quizzes=total_quizzes,
                           total_users=total_users,
                           total_contestants=total_contestants,
                           upcoming_quizzes=upcoming_quizzes)

# --- Admin Management Routes ---

@admin_bp.route('/manage_admins')
@login_required
@superadmin_required # Only superadmins can manage other admins
def manage_admins():
    # Fetch all users who have the 'admin' role
    # We explicitly exclude superadmins from this list for management, as they manage admins
    # and superadmins might have different management flows.
    admin_role = Role.query.filter_by(name='admin').first()
    if admin_role:
        admins = User.query.filter_by(role=admin_role).all()
    else:
        admins = [] # No admin role defined, no admins to show
        flash('Admin role not found in the database. Please ensure roles are seeded.', 'danger')
    return render_template('admin/manage_admins.html', admins=admins)

@admin_bp.route('/add_admin', methods=['GET', 'POST'])
@login_required
@superadmin_required # Only superadmins can add new admins
def add_admin():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if not username or not email or not password or not confirm_password:
            flash('All fields are required.', 'danger')
            return render_template('admin/add_admin.html')

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('admin/add_admin.html')

        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'danger')
            return render_template('admin/add_admin.html')

        if User.query.filter_by(email=email).first():
            flash('Email already exists.', 'danger')
            return render_template('admin/add_admin.html')

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        admin_role = Role.query.filter_by(name='admin').first()
        if not admin_role:
            flash('Admin role not found in the database. Please ensure roles are seeded.', 'danger')
            return render_template('admin/add_admin.html')

        new_admin = User(username=username, email=email, password=hashed_password, role=admin_role)
        db.session.add(new_admin)
        db.session.commit()
        flash(f'Admin {username} added successfully!', 'success')
        return redirect(url_for('admin.manage_admins'))

    return render_template('admin/add_admin.html')

@admin_bp.route('/delete_admin/<int:admin_id>', methods=['POST'])
@login_required
@superadmin_required # Only superadmins can delete admins
def delete_admin(admin_id):
    admin_to_delete = User.query.get_or_404(admin_id)

    # Prevent superadmin from deleting themselves or other superadmins
    if admin_to_delete.has_role('superadmin'):
        flash('Cannot delete a superadmin account through this interface.', 'danger')
        return redirect(url_for('admin.manage_admins'))

    if admin_to_delete.id == current_user.id:
        flash('You cannot delete your own account.', 'danger')
        return redirect(url_for('admin.manage_admins'))

    if not admin_to_delete.has_role('admin'):
        flash('User is not an admin and cannot be deleted via this interface.', 'danger')
        return redirect(url_for('admin.manage_admins'))

    # Check if the admin is associated with any quizzes
    associated_quizzes = Quiz.query.filter_by(admin_id=admin_to_delete.id).all()
    if associated_quizzes:
        flash(f'Cannot delete admin {admin_to_delete.username}. They are currently associated with {len(associated_quizzes)} quiz(es). Please reassign or delete these quizzes first.', 'danger')
        return redirect(url_for('admin.manage_admins'))

    try:
        db.session.delete(admin_to_delete)
        db.session.commit()
        flash(f'Admin {admin_to_delete.username} deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting admin: {e}', 'danger')
    return redirect(url_for('admin.manage_admins'))

@admin_bp.route('/change_admin_password/<int:admin_id>', methods=['GET', 'POST'])
@login_required
@superadmin_required # Only superadmins can change other admin's passwords
def change_admin_password(admin_id):
    admin_user = User.query.get_or_404(admin_id)

    # Prevent superadmin from changing another superadmin's password through this route
    if admin_user.has_role('superadmin'):
        flash('Cannot change a superadmin\'s password through this interface. Superadmins manage their own password.', 'danger')
        return redirect(url_for('admin.manage_admins'))

    if not admin_user.has_role('admin'):
        flash('User is not an admin. Password can only be changed for admin users via this interface.', 'danger')
        return redirect(url_for('admin.manage_admins'))


    if request.method == 'POST':
        new_password = request.form.get('new_password')
        confirm_new_password = request.form.get('confirm_new_password')

        if not new_password or not confirm_new_password:
            flash('New password and confirmation are required.', 'danger')
        elif new_password != confirm_new_password:
            flash('New password and confirm new password do not match.', 'danger')
        elif len(new_password) < 6: # Example: set a minimum password length
            flash('New password must be at least 6 characters long.', 'danger')
        else:
            admin_user.password = bcrypt.generate_password_hash(new_password).decode('utf-8')
            try:
                db.session.commit()
                flash(f'Password for admin {admin_user.username} changed successfully!', 'success')
                return redirect(url_for('admin.manage_admins'))
            except Exception as e:
                db.session.rollback()
                flash(f'Error updating password: {e}', 'danger')

    return render_template('admin/change_admin_password.html', admin_user=admin_user)


@admin_bp.route('/moderators')
@role_required('admin', 'superadmin')
def moderator_list():
    moderators = User.query.join(Role).filter(Role.name == 'moderator').all()
    return render_template('admin/moderator_list.html', moderators=moderators)

@admin_bp.route('/moderators/add', methods=['GET', 'POST'])
@role_required('admin', 'superadmin')
def add_moderator():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        if not username or not email or not password:
            flash('All fields are required.', 'danger')
            return redirect(url_for('admin.add_moderator'))

        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            flash('Username or Email already exists.', 'danger')
            return redirect(url_for('admin.add_moderator'))

        moderator_role = Role.query.filter_by(name='moderator').first()
        if not moderator_role:
            flash('Moderator role not found. Please seed roles.', 'danger')
            return redirect(url_for('admin.moderator_list'))

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        new_moderator = User(username=username, email=email, password=hashed_password, role=moderator_role)
        db.session.add(new_moderator)
        db.session.commit()
        flash('Moderator added successfully!', 'success')
        return redirect(url_for('admin.moderator_list'))
    return render_template('admin/add_moderator.html')

@admin_bp.route('/moderators/edit/<int:user_id>', methods=['GET', 'POST'])
@role_required('admin', 'superadmin')
def edit_moderator(user_id):
    moderator = User.query.get_or_404(user_id)
    if not moderator.has_role('moderator'):
        flash('User is not a moderator.', 'danger')
        return redirect(url_for('admin.moderator_list'))

    if request.method == 'POST':
        moderator.username = request.form.get('username')
        moderator.email = request.form.get('email')
        new_password = request.form.get('password')

        if not moderator.username or not moderator.email:
            flash('Username and Email are required.', 'danger')
            return redirect(url_for('admin.edit_moderator', user_id=user_id))

        if new_password:
            moderator.password = bcrypt.generate_password_hash(new_password).decode('utf-8')

        try:
            db.session.commit()
            flash('Moderator updated successfully!', 'success')
            return redirect(url_for('admin.moderator_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating moderator: {e}', 'danger')

    return render_template('admin/edit_moderator.html', moderator=moderator)

@admin_bp.route('/moderators/disable/<int:user_id>')
@role_required('admin', 'superadmin')
def disable_moderator(user_id):
    # For simplicity, we'll just delete the user. In a real app, you might add an `is_active` flag.
    moderator = User.query.get_or_404(user_id)
    if not moderator.has_role('moderator'):
        flash('User is not a moderator.', 'danger')
        return redirect(url_for('admin.moderator_list'))

    try:
        db.session.delete(moderator)
        db.session.commit()
        flash('Moderator disabled (deleted) successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error disabling moderator: {e}', 'danger')
    return redirect(url_for('admin.moderator_list'))

@admin_bp.route('/quizzes')
@role_required('admin', 'superadmin')
def quiz_settings():
    quizzes = Quiz.query.all()
    return render_template('admin/quiz_settings.html', quizzes=quizzes)

@admin_bp.route('/quizzes/add', methods=['GET', 'POST'])
@role_required('admin', 'superadmin')
def add_quiz():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        quiz_date_str = request.form.get('quiz_date')

        if not title or not quiz_date_str:
            flash('Title and Quiz Date are required.', 'danger')
            return redirect(url_for('admin.add_quiz'))

        try:
            quiz_date = datetime.strptime(quiz_date_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            flash('Invalid date format. Please use YYYY-MM-DDTHH:MM.', 'danger')
            return redirect(url_for('admin.add_quiz'))

        new_quiz = Quiz(title=title, description=description, quiz_date=quiz_date, admin_id=current_user.id)
        db.session.add(new_quiz)
        db.session.commit()
        flash('Quiz added successfully!', 'success')
        return redirect(url_for('admin.quiz_settings'))
    return render_template('admin/add_quiz.html')

@admin_bp.route('/quizzes/edit/<int:quiz_id>', methods=['GET', 'POST'])
@role_required('admin', 'superadmin')
def edit_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    if request.method == 'POST':
        quiz.title = request.form.get('title')
        quiz.description = request.form.get('description')
        quiz_date_str = request.form.get('quiz_date')
        quiz.is_active = 'is_active' in request.form

        if not quiz.title or not quiz_date_str:
            flash('Title and Quiz Date are required.', 'danger')
            return redirect(url_for('admin.edit_quiz', quiz_id=quiz_id))

        try:
            quiz.quiz_date = datetime.strptime(quiz_date_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            flash('Invalid date format. Please use YYYY-MM-DDTHH:MM.', 'danger')
            return redirect(url_for('admin.edit_quiz', quiz_id=quiz_id))

        try:
            db.session.commit()
            flash('Quiz updated successfully!', 'success')
            return redirect(url_for('admin.quiz_settings'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating quiz: {e}', 'danger')
    return render_template('admin/edit_quiz.html', quiz=quiz)

@admin_bp.route('/quizzes/delete/<int:quiz_id>', methods=['POST'])
@role_required('admin', 'superadmin')
def delete_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)

    try:
        # If your database relationships for Question and Contestant
        # are configured with ON DELETE CASCADE, deleting the quiz
        # will automatically delete its associated questions and contestants.
        # Otherwise, you might need to explicitly delete them here
        # before deleting the quiz to avoid foreign key constraint errors.
        # Example if not using cascade:
        # Question.query.filter_by(quiz_id=quiz.id).delete()
        # Contestant.query.filter_by(quiz_id=quiz.id).delete()
        # db.session.commit() # Commit these deletions if done explicitly

        db.session.delete(quiz)
        db.session.commit()
        flash('Quiz deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting quiz: {e}', 'danger')
    return redirect(url_for('admin.quiz_settings'))

@admin_bp.route('/quizzes/<int:quiz_id>/questions')
@role_required('admin', 'superadmin')
def manage_questions(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    questions = Question.query.filter_by(quiz_id=quiz.id).all()
    return render_template('admin/manage_questions.html', quiz=quiz, questions=questions)

@admin_bp.route('/quizzes/<int:quiz_id>/questions/add', methods=['GET', 'POST'])
@role_required('admin', 'superadmin')
def add_question(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    if request.method == 'POST':
        question_text = request.form.get('question_text')
        option_a = request.form.get('option_a')
        option_b = request.form.get('option_b')
        option_c = request.form.get('option_c')
        option_d = request.form.get('option_d')
        correct_answer = request.form.get('correct_answer')

        if not all([question_text, option_a, option_b, option_c, option_d, correct_answer]):
            flash('All question fields and correct answer are required.', 'danger')
            return redirect(url_for('admin.add_question', quiz_id=quiz_id))

        if correct_answer not in ['a', 'b', 'c', 'd']:
            flash('Correct answer must be a, b, c, or d.', 'danger')
            return redirect(url_for('admin.add_question', quiz_id=quiz_id))

        new_question = Question(
            quiz_id=quiz.id,
            question_text=question_text,
            option_a=option_a,
            option_b=option_b,
            option_c=option_c,
            option_d=option_d,
            correct_answer=correct_answer
        )
        db.session.add(new_question)
        db.session.commit()
        flash('Question added successfully!', 'success')
        return redirect(url_for('admin.manage_questions', quiz_id=quiz_id))
    return render_template('admin/add_question.html', quiz=quiz)

@admin_bp.route('/quizzes/<int:quiz_id>/questions/edit/<int:question_id>', methods=['GET', 'POST'])
@role_required('admin', 'superadmin')
def edit_question(quiz_id, question_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    question = Question.query.get_or_404(question_id)
    if question.quiz_id != quiz.id:
        flash('Question does not belong to this quiz.', 'danger')
        return redirect(url_for('admin.manage_questions', quiz_id=quiz_id))

    if request.method == 'POST':
        question.question_text = request.form.get('question_text')
        question.option_a = request.form.get('option_a')
        question.option_b = request.form.get('option_b')
        question.option_c = request.form.get('option_c')
        question.option_d = request.form.get('option_d')
        question.correct_answer = request.form.get('correct_answer')

        if not all([question.question_text, question.option_a, question.option_b, question.option_c, question.option_d, question.correct_answer]):
            flash('All question fields and correct answer are required.', 'danger')
            return redirect(url_for('admin.edit_question', quiz_id=quiz_id, question_id=question_id))

        if question.correct_answer not in ['a', 'b', 'c', 'd']:
            flash('Correct answer must be a, b, c, or d.', 'danger')
            return redirect(url_for('admin.edit_question', quiz_id=quiz_id, question_id=question_id))

        try:
            db.session.commit()
            flash('Question updated successfully!', 'success')
            return redirect(url_for('admin.manage_questions', quiz_id=quiz_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating question: {e}', 'danger')
    return render_template('admin/edit_question.html', quiz=quiz, question=question)

@admin_bp.route('/quizzes/<int:quiz_id>/questions/delete/<int:question_id>')
@role_required('admin', 'superadmin')
def delete_question(quiz_id, question_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    question = Question.query.get_or_404(question_id)
    if question.quiz_id != quiz.id:
        flash('Question does not belong to this quiz.', 'danger')
        return redirect(url_for('admin.manage_questions', quiz_id=quiz_id))

    try:
        db.session.delete(question)
        db.session.commit()
        flash('Question deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting question: {e}', 'danger')
    return redirect(url_for('admin.manage_questions', quiz_id=quiz_id))


@admin_bp.route('/quizzes/<int:quiz_id>/contestants')
@role_required('admin', 'superadmin')
def contestant_registration(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    contestants = Contestant.query.filter_by(quiz_id=quiz_id).all()
    return render_template('admin/contestant_registration.html', quiz=quiz, contestants=contestants)

@admin_bp.route('/quizzes/<int:quiz_id>/contestants/add', methods=['GET', 'POST'])
@role_required('admin', 'superadmin')
def add_contestant(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email') # Email is optional as per requirements

        if not name:
            flash('Contestant name is required.', 'danger')
            return redirect(url_for('admin.add_contestant', quiz_id=quiz_id))

        new_contestant = Contestant(quiz_id=quiz.id, name=name, email=email if email else None)
        db.session.add(new_contestant)
        db.session.commit()
        flash('Contestant registered successfully!', 'success')
        return redirect(url_for('admin.contestant_registration', quiz_id=quiz_id))
    return render_template('admin/add_contestant.html', quiz=quiz)

@admin_bp.route('/quizzes/<int:quiz_id>/contestants/edit/<int:contestant_id>', methods=['GET', 'POST'])
@role_required('admin', 'superadmin')
def edit_contestant(quiz_id, contestant_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    contestant = Contestant.query.get_or_404(contestant_id)
    if contestant.quiz_id != quiz.id:
        flash('Contestant does not belong to this quiz.', 'danger')
        return redirect(url_for('admin.contestant_registration', quiz_id=quiz_id))

    if request.method == 'POST':
        contestant.name = request.form.get('name')
        contestant.email = request.form.get('email')

        if not contestant.name:
            flash('Contestant name is required.', 'danger')
            return redirect(url_for('admin.edit_contestant', quiz_id=quiz_id, contestant_id=contestant_id))

        try:
            db.session.commit()
            flash('Contestant updated successfully!', 'success')
            return redirect(url_for('admin.contestant_registration', quiz_id=quiz_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating contestant: {e}', 'danger')
    return render_template('admin/edit_contestant.html', quiz=quiz, contestant=contestant)

@admin_bp.route('/quizzes/<int:quiz_id>/contestants/delete/<int:contestant_id>')
@role_required('admin', 'superadmin')
def delete_contestant(quiz_id, contestant_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    contestant = Contestant.query.get_or_404(contestant_id)
    if contestant.quiz_id != quiz.id:
        flash('Contestant does not belong to this quiz.', 'danger')
        return redirect(url_for('admin.contestant_registration', quiz_id=quiz_id))

    try:
        db.session.delete(contestant)
        db.session.commit()
        flash('Contestant deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting contestant: {e}', 'danger')
    return redirect(url_for('admin.contestant_registration', quiz_id=quiz_id))
