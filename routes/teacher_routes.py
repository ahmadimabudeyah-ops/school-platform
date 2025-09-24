from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import current_user, login_required
from models import (
    db, Exam, Subject, Question, Choice, Assignment, AssignmentTask,
    AssignmentSubmission, ExamResult, User, LiveSession
)
from forms import ExamForm, QuestionForm, AssignmentForm, AssignmentTaskForm, GradingForm, LiveSessionForm
from datetime import datetime, timedelta
import os
from sqlalchemy import func
from sqlalchemy.orm import joinedload  # تحسين تحميل العلاقات

# Create Blueprint for teacher routes
teacher_bp = Blueprint('teacher', __name__)

@teacher_bp.before_request
@login_required
def restrict_to_teachers():
    """
    Ensure the current user has the 'teacher' role before accessing any route in this Blueprint.
    """
    if getattr(current_user, "role", None) != 'teacher':
        flash('This page is for teachers only.', 'warning')
        if getattr(current_user, "role", None) == 'admin':
            return redirect(url_for('admin.dashboard'))
        elif getattr(current_user, "role", None) == 'student':
            return redirect(url_for('student.dashboard'))
        else:
            return redirect(url_for('auth.login'))

# --- Teacher Dashboard ---
@teacher_bp.route('/dashboard')
def dashboard():
    """
    Teacher dashboard page showing exams, assignments, and alerts.
    """
    # Get exams and assignments created by the current teacher
    exams = Exam.query.filter_by(teacher_id=current_user.id).all()
    assignments = Assignment.query.filter_by(teacher_id=current_user.id).all()

    # Calculate total submissions for the teacher's assignments
    teacher_assignment_ids = [assignment.id for assignment in assignments]
    total_submissions_count = (
        AssignmentSubmission.query.filter(
            AssignmentSubmission.assignment_id.in_(teacher_assignment_ids)
        ).count() if teacher_assignment_ids else 0
    )

    dashboard_alerts = []

    # Check for an active live session
    active_session = LiveSession.query.filter_by(
        teacher_id=current_user.id,
        is_active=True
    ).first()

    if active_session:
        dashboard_alerts.append({
            'type': 'success',
            'message': f"You have an active live session: {active_session.title}",
            'link': url_for('teacher.live_broadcast', session_id=active_session.id),
            'link_text': 'Continue Broadcast'
        })

    # Get recent submissions (last 5) with student and assignment eager-loaded
    recent_submissions = (
        AssignmentSubmission.query
        .join(Assignment)
        .options(joinedload(AssignmentSubmission.assignment), joinedload(AssignmentSubmission.student))
        .filter(Assignment.teacher_id == current_user.id)
        .order_by(AssignmentSubmission.submission_time.desc())
        .limit(5)
        .all()
    )

    for submission in recent_submissions:
        dashboard_alerts.append({
            'type': 'info',
            'message': f"Assignment '{submission.assignment.title}' submitted by {submission.student.username}.",
            'link': url_for('teacher.grade_submission', submission_id=submission.id),
            'link_text': 'View Submission'
        })

    # Get overdue assignments that are not yet graded / with no submissions
    overdue_assignments = Assignment.query.filter(
        Assignment.teacher_id == current_user.id,
        Assignment.due_date < datetime.utcnow(),
        ~Assignment.submissions.any()
    ).all()

    for assignment in overdue_assignments:
        dashboard_alerts.append({
            'type': 'danger',
            'message': f"Assignment '{assignment.title}' is overdue and has no submissions.",
            'link': url_for('teacher.view_assignment_submissions', assignment_id=assignment.id),
            'link_text': 'View Submissions'
        })

    # Get upcoming assignments (due within 7 days)
    upcoming_assignments = Assignment.query.filter(
        Assignment.teacher_id == current_user.id,
        Assignment.due_date > datetime.utcnow(),
        Assignment.due_date <= datetime.utcnow() + timedelta(days=7)
    ).all()

    for assignment in upcoming_assignments:
        dashboard_alerts.append({
            'type': 'warning',
            'message': f"Assignment '{assignment.title}' is due soon on {assignment.due_date.strftime('%Y-%m-%d %H:%M')}.",
            'link': url_for('teacher.view_assignment_submissions', assignment_id=assignment.id),
            'link_text': 'View Submissions'
        })

    return render_template(
        'teacher/dashboard.html',
        exams=exams,
        assignments=assignments,
        total_submissions_count=total_submissions_count,
        dashboard_alerts=dashboard_alerts,
        active_session=active_session
    )

# --- Exam Management ---
@teacher_bp.route('/exams_list')
def exams_list():
    """
    Page showing a list of all exams created by the teacher.
    """
    exams = Exam.query.filter_by(teacher_id=current_user.id).all()
    return render_template('teacher/exams_list.html', exams=exams)

@teacher_bp.route('/create_exam', methods=['GET', 'POST'])
def create_exam():
    """
    Route to create a new exam.
    """
    form = ExamForm()
    if form.validate_on_submit():
        new_exam = Exam(
            title=form.title.data,
            description=form.description.data,
            subject_id=form.subject.data,
            teacher_id=current_user.id,
            start_time=form.start_time.data,
            end_time=form.end_time.data,
            is_active=form.is_active.data,
            total_points=0.0,
            class_id=form.class_id.data
        )
        db.session.add(new_exam)
        db.session.commit()
        flash('Exam created successfully!', 'success')
        return redirect(url_for('teacher.exams_list'))
    return render_template('teacher/create_exam.html', form=form)

@teacher_bp.route('/edit_exam/<int:exam_id>', methods=['GET', 'POST'])
def edit_exam(exam_id):
    """
    Route to edit an existing exam.
    """
    exam = Exam.query.get_or_404(exam_id)
    if exam.teacher_id != current_user.id:
        flash('You are not authorized to edit this exam.', 'danger')
        return redirect(url_for('teacher.dashboard'))
    form = ExamForm(obj=exam)
    if form.validate_on_submit():
        exam.title = form.title.data
        exam.description = form.description.data
        exam.subject_id = form.subject.data
        exam.start_time = form.start_time.data
        exam.end_time = form.end_time.data
        exam.is_active = form.is_active.data
        exam.class_id = form.class_id.data
        db.session.commit()
        flash('Exam updated successfully.', 'success')
        return redirect(url_for('teacher.exams_list'))
    return render_template('teacher/create_exam.html', form=form, exam=exam)

@teacher_bp.route('/delete_exam/<int:exam_id>', methods=['POST'])
def delete_exam(exam_id):
    """
    Route to delete an exam.
    """
    exam = Exam.query.get_or_404(exam_id)
    if exam.teacher_id != current_user.id:
        flash('You are not authorized to delete this exam.', 'danger')
        return redirect(url_for('teacher.dashboard'))
    db.session.delete(exam)
    db.session.commit()
    flash('Exam deleted successfully.', 'success')
    return redirect(url_for('teacher.exams_list'))

# --- Exam Question Management ---
@teacher_bp.route('/add_question/<int:exam_id>', methods=['GET', 'POST'])
def add_question(exam_id):
    """
    Route to add a new question to a specific exam.
    """
    exam = Exam.query.get_or_404(exam_id)
    if exam.teacher_id != current_user.id:
        flash('You are not authorized to add questions to this exam.', 'danger')
        return redirect(url_for('teacher.dashboard'))
    form = QuestionForm()
    if form.validate_on_submit():
        try:
            new_question = Question(
                text=form.text.data,
                question_type=form.question_type.data,
                points=form.points.data,
                exam_id=exam.id
            )
            db.session.add(new_question)

            if new_question.question_type == 'multiple_choice':
                correct_choices = request.form.getlist('correct_choices')
                choices = [form.choice1.data, form.choice2.data, form.choice3.data, form.choice4.data]
                is_correct = [
                    'choice1' in correct_choices,
                    'choice2' in correct_choices,
                    'choice3' in correct_choices,
                    'choice4' in correct_choices
                ]

                # Update exam's total points
                exam.total_points += new_question.points
                db.session.add(exam)

                for i, choice_text in enumerate(choices):
                    new_choice = Choice(
                        text=choice_text,
                        is_correct=is_correct[i],
                        question=new_question
                    )
                    db.session.add(new_choice)
            else: # short_answer and true_false
                # Update exam's total points
                exam.total_points += new_question.points
                db.session.add(exam)

                correct_answer_text = form.correct_answer.data
                new_choice = Choice(
                    text=correct_answer_text,
                    is_correct=True,
                    question=new_question
                )
                db.session.add(new_choice)
            
            db.session.commit()
            flash('Question added successfully!', 'success')
            return redirect(url_for('teacher.add_question', exam_id=exam.id))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error adding question: {str(e)}")
            flash(f'An error occurred: {str(e)}', 'danger')
            return redirect(url_for('teacher.add_question', exam_id=exam.id))
    
    return render_template('teacher/add_question.html', form=form, exam=exam)

@teacher_bp.route('/edit_question/<int:question_id>', methods=['GET', 'POST'])
def edit_question(question_id):
    """
    Route to edit an existing question.
    """
    question = Question.query.get_or_404(question_id)
    if question.exam.teacher_id != current_user.id:
        flash('You are not authorized to edit this question.', 'danger')
        return redirect(url_for('teacher.dashboard'))

    form = QuestionForm(obj=question)

    if form.validate_on_submit():
        try:
            # Update question attributes
            question.text = form.text.data
            question.question_type = form.question_type.data
            question.points = form.points.data

            # Delete existing choices and create new ones
            for choice in question.choices:
                db.session.delete(choice)

            if question.question_type == 'multiple_choice':
                correct_choices_form = request.form.getlist('correct_choices')
                
                choice_data = {
                    'choice1': form.choice1.data,
                    'choice2': form.choice2.data,
                    'choice3': form.choice3.data,
                    'choice4': form.choice4.data
                }
                
                for choice_field_name, choice_text in choice_data.items():
                    is_correct = choice_field_name in correct_choices_form
                    new_choice = Choice(
                        text=choice_text,
                        is_correct=is_correct,
                        question=question
                    )
                    db.session.add(new_choice)
            
            else: # short_answer and true_false
                correct_answer_text = form.correct_answer.data
                new_choice = Choice(
                    text=correct_answer_text,
                    is_correct=True,
                    question=question
                )
                db.session.add(new_choice)
            
            db.session.commit()
            flash('Question updated successfully!', 'success')
            return redirect(url_for('teacher.view_exam_details', exam_id=question.exam_id))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error editing question: {str(e)}")
            flash(f'An error occurred: {str(e)}', 'danger')
            return redirect(url_for('teacher.edit_question', question_id=question.id))
    
    # Pre-populate form on GET request
    if request.method == 'GET':
        form.text.data = question.text
        form.question_type.data = question.question_type
        form.points.data = question.points

        if question.question_type == 'multiple_choice':
            choices = question.choices
            if len(choices) >= 1:
                form.choice1.data = choices[0].text
                form.is_correct1.data = choices[0].is_correct
            if len(choices) >= 2:
                form.choice2.data = choices[1].text
                form.is_correct2.data = choices[1].is_correct
            if len(choices) >= 3:
                form.choice3.data = choices[2].text
                form.is_correct3.data = choices[2].is_correct
            if len(choices) >= 4:
                form.choice4.data = choices[3].text
                form.is_correct4.data = choices[3].is_correct
        else:
            correct_choice = next((c for c in question.choices if c.is_correct), None)
            if correct_choice:
                form.correct_answer.data = correct_choice.text

    return render_template('teacher/edit_question.html', form=form, question=question)

@teacher_bp.route('/delete_question/<int:question_id>', methods=['POST'])
def delete_question(question_id):
    """
    Route to delete a question.
    """
    question = Question.query.get_or_404(question_id)
    if question.exam.teacher_id != current_user.id:
        flash('You are not authorized to delete this question.', 'danger')
        return redirect(url_for('teacher.dashboard'))

    exam_id = question.exam_id
    db.session.delete(question)
    db.session.commit()
    flash('Question deleted successfully.', 'success')
    return redirect(url_for('teacher.view_exam_details', exam_id=exam_id))

@teacher_bp.route('/view_exam_details/<int:exam_id>')
def view_exam_details(exam_id):
    """
    Page showing a list of questions for a specific exam.
    """
    exam = Exam.query.options(joinedload(Exam.questions).joinedload(Question.choices)).get_or_404(exam_id)
    if exam.teacher_id != current_user.id:
        flash('You are not authorized to view this exam.', 'danger')
        return redirect(url_for('teacher.dashboard'))
    return render_template('teacher/view_exam_details.html', exam=exam)

# --- Assignments Management ---
@teacher_bp.route('/assignments_list')
def assignments_list():
    """
    Page showing a list of all assignments created by the teacher.
    """
    assignments = Assignment.query.filter_by(teacher_id=current_user.id).all()
    return render_template('teacher/assignments_list.html', assignments=assignments)


@teacher_bp.route('/create_assignment', methods=['GET', 'POST'])
def create_assignment():
    """
    Route to create a new assignment.
    """
    form = AssignmentForm()
    if form.validate_on_submit():
        new_assignment = Assignment(
            title=form.title.data,
            description=form.description.data,
            subject_id=form.subject.data,
            teacher_id=current_user.id,
            class_id=form.class_id.data,
            due_date=form.due_date.data,
            is_active=form.is_active.data
        )
        db.session.add(new_assignment)
        db.session.commit()
        flash('Assignment created successfully!', 'success')
        return redirect(url_for('teacher.assignments_list'))
    
    return render_template('teacher/create_assignment.html', form=form)

@teacher_bp.route('/edit_assignment/<int:assignment_id>', methods=['GET', 'POST'])
def edit_assignment(assignment_id):
    """
    Route to edit an existing assignment.
    """
    assignment = Assignment.query.get_or_404(assignment_id)
    if assignment.teacher_id != current_user.id:
        flash('You are not authorized to edit this assignment.', 'danger')
        return redirect(url_for('teacher.dashboard'))
    
    form = AssignmentForm(obj=assignment)
    if form.validate_on_submit():
        assignment.title = form.title.data
        assignment.description = form.description.data
        assignment.subject_id = form.subject.data
        assignment.class_id = form.class_id.data
        assignment.due_date = form.due_date.data
        assignment.is_active = form.is_active.data
        
        db.session.commit()
        flash('Assignment updated successfully.', 'success')
        return redirect(url_for('teacher.assignments_list'))

    return render_template('teacher/create_assignment.html', form=form, assignment=assignment)

@teacher_bp.route('/delete_assignment/<int:assignment_id>', methods=['POST'])
def delete_assignment(assignment_id):
    """
    Route to delete an assignment.
    """
    assignment = Assignment.query.get_or_404(assignment_id)
    if assignment.teacher_id != current_user.id:
        flash('You are not authorized to delete this assignment.', 'danger')
        return redirect(url_for('teacher.dashboard'))
    db.session.delete(assignment)
    db.session.commit()
    flash('Assignment deleted successfully.', 'success')
    return redirect(url_for('teacher.assignments_list'))

# --- Assignment Tasks Management ---
@teacher_bp.route('/add_assignment_task/<int:assignment_id>', methods=['GET', 'POST'])
def add_assignment_task(assignment_id):
    """
    Route to add a new task to a specific assignment.
    """
    assignment = Assignment.query.get_or_404(assignment_id)
    if assignment.teacher_id != current_user.id:
        flash('You are not authorized to add tasks to this assignment.', 'danger')
        return redirect(url_for('teacher.dashboard'))
    
    form = AssignmentTaskForm()
    if form.validate_on_submit():
        new_task = AssignmentTask(
            assignment_id=assignment.id,
            description=form.description.data,
            file_url=form.file_url.data
        )
        db.session.add(new_task)
        db.session.commit()
        flash('Task added successfully!', 'success')
        return redirect(url_for('teacher.view_assignment_details', assignment_id=assignment.id))
    
    return render_template('teacher/add_assignment_task.html', form=form, assignment=assignment)

@teacher_bp.route('/edit_assignment_task/<int:task_id>', methods=['GET', 'POST'])
def edit_assignment_task(task_id):
    """
    Route to edit an existing assignment task.
    """
    task = AssignmentTask.query.get_or_404(task_id)
    if task.assignment.teacher_id != current_user.id:
        flash('You are not authorized to edit this task.', 'danger')
        return redirect(url_for('teacher.dashboard'))
    
    form = AssignmentTaskForm(obj=task)
    if form.validate_on_submit():
        task.description = form.description.data
        task.file_url = form.file_url.data
        db.session.commit()
        flash('Task updated successfully.', 'success')
        return redirect(url_for('teacher.view_assignment_details', assignment_id=task.assignment_id))

    return render_template('teacher/edit_assignment_task.html', form=form, task=task)

@teacher_bp.route('/delete_assignment_task/<int:task_id>', methods=['POST'])
def delete_assignment_task(task_id):
    """
    Route to delete an assignment task.
    """
    task = AssignmentTask.query.get_or_404(task_id)
    if task.assignment.teacher_id != current_user.id:
        flash('You are not authorized to delete this task.', 'danger')
        return redirect(url_for('teacher.dashboard'))
    
    assignment_id = task.assignment_id
    db.session.delete(task)
    db.session.commit()
    flash('Task deleted successfully.', 'success')
    return redirect(url_for('teacher.view_assignment_details', assignment_id=assignment_id))

@teacher_bp.route('/view_assignment_details/<int:assignment_id>')
def view_assignment_details(assignment_id):
    """
    Page showing a list of tasks for a specific assignment.
    """
    assignment = Assignment.query.options(joinedload(Assignment.tasks)).get_or_404(assignment_id)
    if assignment.teacher_id != current_user.id:
        flash('You are not authorized to view this assignment.', 'danger')
        return redirect(url_for('teacher.dashboard'))
    
    return render_template('teacher/view_assignment_details.html', assignment=assignment)

@teacher_bp.route('/view_assignment_submissions/<int:assignment_id>')
def view_assignment_submissions(assignment_id):
    """
    Page for teachers to see submissions for an assignment.
    """
    assignment = Assignment.query.get_or_404(assignment_id)
    if assignment.teacher_id != current_user.id:
        flash('You are not authorized to view submissions for this assignment.', 'danger')
        return redirect(url_for('teacher.dashboard'))
    
    submissions = AssignmentSubmission.query.filter_by(assignment_id=assignment_id).options(joinedload(AssignmentSubmission.student)).all()
    
    return render_template('teacher/view_assignment_submissions.html', assignment=assignment, submissions=submissions)

@teacher_bp.route('/grade_submission/<int:submission_id>', methods=['GET', 'POST'])
def grade_submission(submission_id):
    """
    Route for teachers to grade an assignment submission.
    """
    submission = AssignmentSubmission.query.get_or_404(submission_id)
    if submission.assignment.teacher_id != current_user.id:
        flash('You are not authorized to grade this submission.', 'danger')
        return redirect(url_for('teacher.dashboard'))
    
    form = GradingForm()
    if form.validate_on_submit():
        submission.grade = form.grade.data
        submission.feedback = form.feedback.data
        submission.graded_at = datetime.utcnow()
        db.session.commit()
        flash('Submission graded successfully!', 'success')
        return redirect(url_for('teacher.view_assignment_submissions', assignment_id=submission.assignment_id))
    
    # Pre-populate form on GET
    form.grade.data = submission.grade
    form.feedback.data = submission.feedback
    
    return render_template('teacher/grade_submission.html', form=form, submission=submission)

# --- Live Sessions Management ---
@teacher_bp.route('/live_sessions')
def live_sessions():
    """
    Page showing a list of live sessions created by the teacher.
    """
    sessions = LiveSession.query.filter_by(teacher_id=current_user.id).order_by(LiveSession.start_time.desc()).all()
    return render_template('teacher/live_sessions.html', sessions=sessions)


@teacher_bp.route('/start_live_session', methods=['GET', 'POST'])
def start_live_session():
    """
    Route to create and start a new live session.
    """
    form = LiveSessionForm()
    
    try:
        if form.validate_on_submit():
            new_session = LiveSession(
                title=form.title.data,
                description=form.description.data,
                subject_id=form.subject_id.data,
                teacher_id=current_user.id,
                is_private=form.is_private.data
            )
            if form.is_private.data and form.password.data:
                new_session.set_password(form.password.data)
            
            db.session.add(new_session)
            db.session.commit()
            
            flash('Live session created and started successfully!', 'success')
            return redirect(url_for('teacher.live_broadcast', session_id=new_session.id))
        
        return render_template('teacher/start_live_session.html', form=form)

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in start_live_session: {str(e)}")
        flash('حدث خطأ أثناء بدء الجلسة. يرجى المحاولة مرة أخرى.', 'danger')
        return redirect(url_for('teacher.live_sessions'))

@teacher_bp.route('/live_broadcast/<int:session_id>')
def live_broadcast(session_id):
    """Live broadcast page for the teacher."""
    session = LiveSession.query.get_or_404(session_id)
    # Check if the teacher is the owner of the session and it is active
    if session.teacher_id != current_user.id or not session.is_active:
        flash('ليس لديك صلاحية الوصول إلى هذه الجلسة أو أنها غير نشطة.', 'danger')
        return redirect(url_for('teacher.dashboard'))
    return render_template('teacher/live_broadcast.html', session=session)

@teacher_bp.route('/end_live_session/<int:session_id>', methods=['POST'])
def end_live_session(session_id):
    """End a live broadcast session."""
    session = LiveSession.query.get_or_404(session_id)
    if session.teacher_id != current_user.id:
        flash('You are not authorized to end this session.', 'danger')
        return redirect(url_for('teacher.dashboard'))

    session.is_active = False
    session.end_time = datetime.utcnow()
    db.session.commit()
    flash('Live session has been successfully ended.', 'success')
    return redirect(url_for('teacher.live_sessions'))
