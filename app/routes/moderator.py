# app/routes/moderator.py

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
# Ensure these imports match your actual models path
from app.models.quiz import Quiz, Question, Contestant, ContestantAnswer
from app.models.user import User, Role # Import User and Role models
from app.routes.auth import role_required # Your custom role decorator
from datetime import datetime

# Initialize the blueprint
moderator_bp = Blueprint('moderator', __name__)

# --- Existing routes (dashboard, quiz_session, record_answer, submit_quiz_completion) ---
# (Copy them from your provided code, they remain unchanged unless noted)

@moderator_bp.route('/dashboard')
@role_required('moderator') # Assuming moderators/admins see this
def dashboard():
    """
    Displays the moderator dashboard with active and upcoming quizzes.
    """
    # Filter for quizzes that are active (or considered upcoming/currently running)
    quizzes_query = Quiz.query.filter(Quiz.is_active == True).order_by(Quiz.quiz_date.asc())

    quizzes_for_display = []
    for quiz in quizzes_query.all(): # Use .all() to execute the query
        contestants = Contestant.query.filter_by(quiz_id=quiz.id).all()
        total_contestants = len(contestants)
        completed_contestants = sum(1 for c in contestants if c.submitted_at)

        # Determine current status based on actual time for upcoming/active
        if quiz.quiz_date > datetime.utcnow():
            quiz_status = 'Upcoming'
            status_badge_class = 'bg-secondary'
        elif quiz.quiz_date <= datetime.utcnow() and completed_contestants < total_contestants:
            quiz_status = 'Active (In Progress)'
            status_badge_class = 'bg-info'
        else: # This case covers active quizzes where all contestants might have completed
            quiz_status = 'Active / Completed' # Or 'Active (All Completed)'
            status_badge_class = 'bg-success'

        quizzes_for_display.append({
            'id': quiz.id,
            'title': quiz.title,
            'description': quiz.description,
            'quiz_date': quiz.quiz_date,
            'total_contestants': total_contestants,
            'completed_contestants': completed_contestants,
            'quiz_status': quiz_status,
            'status_badge_class': status_badge_class
        })

    # Global statistics (adjusted to fit the 'active or upcoming' focus on dashboard)
    total_quizzes_system = Quiz.query.count() # Count all quizzes in the system
    active_dashboard_quizzes = len(quizzes_for_display) # Count quizzes displayed on this dashboard
    total_registered_contestants = Contestant.query.distinct(Contestant.name).count()

    return render_template('moderator/dashboard.html',
                           quizzes=quizzes_for_display, # Pass the filtered and enriched list
                           total_quizzes_system=total_quizzes_system,
                           active_dashboard_quizzes=active_dashboard_quizzes,
                           total_registered_contestants=total_registered_contestants)

@moderator_bp.route('/quiz_session/<int:quiz_id>')
@role_required('moderator')
def quiz_session(quiz_id):
    """
    Manages a live quiz session, displaying questions and contestant progress.
    """
    quiz = Quiz.query.get_or_404(quiz_id)
    contestants = Contestant.query.filter_by(quiz_id=quiz_id).all()
    questions = Question.query.filter_by(quiz_id=quiz_id).order_by(Question.id.asc()).all()

    # Prepare data for the interactive session
    quiz_data = {
        'quiz_id': quiz.id,
        'title': quiz.title,
        'questions': [{'id': q.id, 'text': q.question_text, 'options': {'a': q.option_a, 'b': q.option_b, 'c': q.option_c, 'd': q.option_d}, 'correct_answer': q.correct_answer} for q in questions],
        'contestants': [{'id': c.id, 'name': c.name, 'score': c.score} for c in contestants]
    }
    return render_template('moderator/quiz_session.html', quiz_data=quiz_data)


@moderator_bp.route('/record_answer', methods=['POST'])
@role_required('moderator')
def record_answer():
    """
    AJAX endpoint to record a contestant's answer and update their score.
    """
    data = request.json
    contestant_id = data.get('contestant_id')
    question_id = data.get('question_id')
    selected_option = data.get('selected_option')
    quiz_id = data.get('quiz_id') # This quiz_id might not be strictly needed here if question_id is unique enough

    question = Question.query.get(question_id)
    contestant = Contestant.query.get(contestant_id)

    if not question or not contestant:
        return {'status': 'error', 'message': 'Invalid contestant or question.'}, 400

    is_correct = (selected_option == question.correct_answer)

    contestant_answer = ContestantAnswer.query.filter_by(
        contestant_id=contestant_id,
        question_id=question_id
    ).first()

    if contestant_answer:
        # If the answer changes, adjust the score accordingly
        if contestant_answer.is_correct and not is_correct:
            contestant.score -= 1
        elif not contestant_answer.is_correct and is_correct:
            contestant.score += 1
        contestant_answer.selected_option = selected_option
        contestant_answer.is_correct = is_correct
    else:
        # Create new answer
        new_answer = ContestantAnswer(
            contestant_id=contestant_id,
            question_id=question_id,
            selected_option=selected_option,
            is_correct=is_correct
        )
        db.session.add(new_answer)
        if is_correct:
            contestant.score += 1

    try:
        db.session.commit()
        return {'status': 'success', 'message': 'Answer recorded.', 'new_score': contestant.score}, 200
    except Exception as e:
        db.session.rollback()
        return {'status': 'error', 'message': f'Database error: {str(e)}'}, 500


@moderator_bp.route('/submit_quiz_completion', methods=['POST'])
@role_required('moderator')
def submit_quiz_completion():
    """
    AJAX endpoint to mark a contestant's quiz as complete.
    """
    data = request.json
    contestant_id = data.get('contestant_id')

    contestant = Contestant.query.get(contestant_id)
    if not contestant:
        return {'status': 'error', 'message': 'Invalid contestant.'}, 400

    if not contestant.submitted_at: # Only set if not already submitted
        contestant.submitted_at = datetime.utcnow()

    try:
        db.session.commit()
        flash(f"Quiz for {contestant.name} marked as complete!", 'success')
        # Return the quiz_id to the frontend for redirection
        return {'status': 'success', 'message': 'Quiz marked complete.', 'quiz_id': contestant.quiz_id}, 200
    except Exception as e:
        db.session.rollback()
        return {'status': 'error', 'message': f'Database error: {str(e)}'}, 500


@moderator_bp.route('/quiz_results/<int:quiz_id>')
@role_required('moderator')
def quiz_results(quiz_id):
    """
    Displays the final results for a specific quiz, listing all contestants
    and their scores, along with rank, percentage, and status.
    """
    quiz = Quiz.query.get_or_404(quiz_id)

    # Get all questions for this quiz to count the total possible score
    questions = Question.query.filter_by(quiz_id=quiz_id).all()
    total_questions_count = len(questions)

    # Fetch contestants, ordered by score (descending) for ranking
    contestants = Contestant.query.filter_by(quiz_id=quiz_id).order_by(Contestant.score.desc()).all()

    # Prepare data list to pass to the template with all necessary fields
    results_for_display = []

    # Track previous score for ranking tie-breaking
    previous_score = None
    rank = 0
    tied_rank = 1 # Keep track of the rank for tied scores

    for i, contestant in enumerate(contestants):
        # Calculate rank
        if contestant.score != previous_score:
            rank = i + 1
            tied_rank = rank
        else:
            rank = tied_rank # Maintain rank for ties

        previous_score = contestant.score

        # Determine status
        status = "Completed" if contestant.submitted_at else "In Progress"

        results_for_display.append({
            'rank': rank,
            'name': contestant.name,
            'score': contestant.score,
            'status': status
        })

    return render_template('moderator/quiz_results.html', # This template path remains here as it's for quiz results
                           quiz=quiz,
                           results=results_for_display, # Pass the enriched list here
                           total_questions_count=total_questions_count)

# --- SUPERADMIN PANEL ROUTES START ---

@moderator_bp.route('/manage_admins')
@role_required('superadmin')
def manage_admins():
    """
    Superadmin dashboard to list and manage admin/moderator accounts.
    """
    admins_and_moderators = User.query.join(Role).filter(Role.name.in_(['admin', 'moderator', 'superadmin'])).all()
    all_roles = Role.query.all()

    # --- UPDATED TEMPLATE PATH ---
    return render_template('admin/manage_admins.html',
                           users=admins_and_moderators,
                           all_roles=all_roles)


@moderator_bp.route('/admin/create', methods=['GET', 'POST'])
@role_required('superadmin')
def create_admin():
    """
    Superadmin route to create a new admin/moderator user account.
    """
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role_name = request.form.get('role') # Get role from form
        is_active = request.form.get('is_active') == 'on' # Checkbox value

        # Basic validation
        if not username or not email or not password or not role_name:
            flash('All fields are required.', 'danger')
            return redirect(url_for('moderator.create_admin'))

        # Check for existing username/email
        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'danger')
            return redirect(url_for('moderator.create_admin'))
        if User.query.filter_by(email=email).first():
            flash('Email already exists.', 'danger')
            return redirect(url_for('moderator.create_admin'))

        # Find the role object
        role = Role.query.filter_by(name=role_name).first()
        if not role:
            flash(f"Role '{role_name}' not found. Please create it first.", 'danger')
            return redirect(url_for('moderator.create_admin'))

        new_user = User(username=username, email=email, role=role, is_active=is_active)
        new_user.set_password(password) # Use the hashing method
        db.session.add(new_user)
        db.session.commit()
        flash(f'User "{username}" created successfully with role "{role_name}".', 'success')
        return redirect(url_for('moderator.manage_admins'))

    all_roles = Role.query.all() # Fetch roles to populate a dropdown
    # --- UPDATED TEMPLATE PATH ---
    return render_template('admin/admin_forms/create_admin.html', all_roles=all_roles)


@moderator_bp.route('/admin/<int:user_id>/edit', methods=['GET', 'POST'])
@role_required('superadmin')
def edit_admin(user_id):
    """
    Superadmin route to edit an existing admin/moderator user account.
    """
    user_to_edit = User.query.get_or_404(user_id)

    # Prevent a superadmin from editing their own critical details (role, status) via this panel
    if user_to_edit.id == current_user.id and current_user.has_role('superadmin'):
        flash("You cannot edit your own superadmin account's critical details or disable yourself via this interface.", 'warning')
        return redirect(url_for('moderator.manage_admins'))


    if request.method == 'POST':
        new_username = request.form.get('username')
        new_email = request.form.get('email')
        new_role_name = request.form.get('role')
        new_is_active = request.form.get('is_active') == 'on'

        # Basic validation
        if not new_username or not new_email or not new_role_name:
            flash('Username, email, and role are required.', 'danger')
            return redirect(url_for('moderator.edit_admin', user_id=user_id))

        # Check for username/email uniqueness (excluding current user)
        if User.query.filter(User.username == new_username, User.id != user_id).first():
            flash('Username already exists for another user.', 'danger')
            return redirect(url_for('moderator.edit_admin', user_id=user_id))
        if User.query.filter(User.email == new_email, User.id != user_id).first():
            flash('Email already exists for another user.', 'danger')
            return redirect(url_for('moderator.edit_admin', user_id=user_id))

        # Find the role object
        role = Role.query.filter_by(name=new_role_name).first()
        if not role:
            flash(f"Role '{new_role_name}' not found.", 'danger')
            return redirect(url_for('moderator.edit_admin', user_id=user_id))

        user_to_edit.username = new_username
        user_to_edit.email = new_email
        user_to_edit.role = role # Assign the role object
        user_to_edit.is_active = new_is_active

        db.session.commit()
        flash(f'User "{user_to_edit.username}" updated successfully.', 'success')
        return redirect(url_for('moderator.manage_admins'))

    all_roles = Role.query.all()
    # --- UPDATED TEMPLATE PATH ---
    return render_template('admin/admin_forms/edit_admin.html', user=user_to_edit, all_roles=all_roles)


@moderator_bp.route('/admin/<int:user_id>/toggle_status', methods=['POST'])
@role_required('superadmin')
def toggle_admin_status(user_id):
    """
    Superadmin route to toggle the active status of an admin/moderator user.
    """
    user_to_toggle = User.query.get_or_404(user_id)

    if user_to_toggle.id == current_user.id:
        flash("You cannot toggle your own account's active status.", 'danger')
        return redirect(url_for('moderator.manage_admins'))

    # Prevent disabling the last superadmin if only one exists (optional but good practice)
    if user_to_toggle.has_role('superadmin') and User.query.join(Role).filter(Role.name == 'superadmin', User.is_active == True, User.id != user_to_toggle.id).count() == 0:
        flash("Cannot disable the last active superadmin account.", 'danger')
        return redirect(url_for('moderator.manage_admins'))

    user_to_toggle.is_active = not user_to_toggle.is_active
    db.session.commit()
    status_msg = "enabled" if user_to_toggle.is_active else "disabled"
    flash(f'User "{user_to_toggle.username}" has been {status_msg}.', 'info')
    return redirect(url_for('moderator.manage_admins'))


@moderator_bp.route('/admin/<int:user_id>/change_password', methods=['GET', 'POST'])
@role_required('superadmin')
def change_admin_password(user_id):
    """
    Superadmin route to change the password of an admin/moderator user.
    """
    user_to_change_pw = User.query.get_or_404(user_id)

    if request.method == 'POST':
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        if not new_password or not confirm_password:
            flash('Both new password fields are required.', 'danger')
            return redirect(url_for('moderator.change_admin_password', user_id=user_id))

        if new_password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('moderator.change_admin_password', user_id=user_id))

        if len(new_password) < 6: # Basic password length check
            flash('Password must be at least 6 characters long.', 'danger')
            return redirect(url_for('moderator.change_admin_password', user_id=user_id))

        user_to_change_pw.set_password(new_password) # Use the hashing method
        db.session.commit()
        flash(f'Password for user "{user_to_change_pw.username}" has been changed.', 'success')
        return redirect(url_for('moderator.manage_admins'))

    # --- UPDATED TEMPLATE PATH ---
    return render_template('admin/admin_forms/change_admin_password.html', user=user_to_change_pw)


@moderator_bp.route('/admin/<int:user_id>/delete', methods=['POST'])
@role_required('superadmin')
def delete_admin(user_id):
    """
    Superadmin route to delete an admin/moderator user account.
    """
    user_to_delete = User.query.get_or_404(user_id)

    if user_to_delete.id == current_user.id:
        flash("You cannot delete your own account!", 'danger')
        return redirect(url_for('moderator.manage_admins'))

    # Prevent deleting another superadmin directly (you might want a stricter process for this)
    if user_to_delete.has_role('superadmin'):
        flash("Cannot delete another superadmin account directly. Consider disabling or demoting instead.", 'danger')
        return redirect(url_for('moderator.manage_admins'))

    db.session.delete(user_to_delete)
    db.session.commit()
    flash(f'User "{user_to_delete.username}" deleted successfully.', 'success')
    return redirect(url_for('moderator.manage_admins'))

# --- SUPERADMIN PANEL ROUTES END ---
