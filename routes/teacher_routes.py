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
from sqlalchemy.orm import joinedload  

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
    exams = Exam.query.filter_by(teacher_id=current_user.id).all()
    assignments = Assignment.query.filter_by(teacher_id=current_user.id).all()

    teacher_assignment_ids = [assignment.id for assignment in assignments]
    total_submissions_count = (
        AssignmentSubmission.query.filter(
            AssignmentSubmission.assignment_id.in_(teacher_assignment_ids)
        ).count() if teacher_assignment_ids else 0
    )

    dashboard_alerts = []

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
    if request.method == 'POST' and form.validate():
        new_question = Question(
            exam_id=exam.id,
            question_type=form.question_type.data,
            text=form.text.data,
            correct_answer=form.correct_answer.data if form.question_type.data in ['short_answer', 'true_false'] else None,
            points=form.points.data
        )
        db.session.add(new_question)
        db.session.commit()

        if form.question_type.data == 'multiple_choice':
            choices_data = [
                (form.choice1.data, form.is_correct1.data),
                (form.choice2.data, form.is_correct2.data),
                (form.choice3.data, form.is_correct3.data),
                (form.choice4.data, form.is_correct4.data)
            ]
            for text, is_correct in choices_data:
                if text:
                    choice = Choice(
                        question_id=new_question.id,
                        text=text,
                        is_correct=is_correct
                    )
                    db.session.add(choice)
            db.session.commit()

        # Update total points for the exam
        exam.total_points = sum(q.points for q in exam.questions)
        db.session.commit()

        flash('Question added successfully.', 'success')
        return redirect(url_for('teacher.add_question', exam_id=exam.id))

    questions = Question.query.filter_by(exam_id=exam.id).all()
    return render_template('teacher/add_question.html', form=form, exam=exam, questions=questions)

@teacher_bp.route('/edit_question/<int:question_id>', methods=['GET', 'POST'])
def edit_question(question_id):
    question = Question.query.get_or_404(question_id)
    exam = question.exam
    if exam.teacher_id != current_user.id:
        flash('You are not authorized to edit this question.', 'danger')
        return redirect(url_for('teacher.dashboard'))

    form = QuestionForm()

    if request.method == 'GET':
        # تعبئة البيانات الحالية في النموذج
        form.question_type.data = question.question_type
        form.text.data = question.text
        form.points.data = question.points
        form.correct_answer.data = question.correct_answer

        # تعبئة الخيارات إذا كان سؤال اختيار من متعدد
        if question.question_type == 'multiple_choice':
            choices = question.choices
            for i, choice in enumerate(choices):
                if i == 0:
                    form.choice1.data = choice.text
                    form.is_correct1.data = choice.is_correct
                elif i == 1:
                    form.choice2.data = choice.text
                    form.is_correct2.data = choice.is_correct
                elif i == 2:
                    form.choice3.data = choice.text
                    form.is_correct3.data = choice.is_correct
                elif i == 3:
                    form.choice4.data = choice.text
                    form.is_correct4.data = choice.is_correct

    if form.validate_on_submit():
        try:
            # حفظ التغييرات الأساسية
            question.question_type = form.question_type.data
            question.text = form.text.data
            question.points = form.points.data

            # معالجة الإجابة الصحيحة بناءً على نوع السؤال
            if question.question_type == 'multiple_choice':
                question.correct_answer = None  # لا يوجد إجابة نصية للاختيار من متعدد
                
                # حذف الخيارات القديمة
                Choice.query.filter_by(question_id=question.id).delete()
                
                # إضافة الخيارات الجديدة
                choices_data = [
                    (form.choice1.data, form.is_correct1.data),
                    (form.choice2.data, form.is_correct2.data),
                    (form.choice3.data, form.is_correct3.data),
                    (form.choice4.data, form.is_correct4.data)
                ]
                
                for text, is_correct in choices_data:
                    if text:  # فقط إذا كان النص غير فارغ
                        choice = Choice(
                            question_id=question.id,
                            text=text,
                            is_correct=is_correct
                        )
                        db.session.add(choice)
            else:
                # للأسئلة النصية وصح/خطأ، حفظ الإجابة الصحيحة وحذف الخيارات
                question.correct_answer = form.correct_answer.data
                Choice.query.filter_by(question_id=question.id).delete()

            # تحديث النقاط الكلية للاختبار
            exam.total_points = sum(q.points for q in exam.questions)
            db.session.commit()
            
            flash('تم تحديث السؤال بنجاح!', 'success')
            return redirect(url_for('teacher.add_question', exam_id=exam.id))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error editing question: {e}")
            flash('حدث خطأ غير متوقع أثناء حفظ التعديلات. يرجى المحاولة مرة أخرى.', 'danger')

    return render_template('teacher/edit_question.html', form=form, question=question, exam=exam)
    
@teacher_bp.route('/delete_question/<int:question_id>', methods=['POST'])
def delete_question(question_id):
    """
    Route to delete a question from an exam.
    """
    question = Question.query.get_or_404(question_id)
    exam = Exam.query.get_or_404(question.exam_id)

    if exam.teacher_id != current_user.id:
        flash('You are not authorized to delete this question.', 'danger')
        return redirect(url_for('teacher.dashboard'))

    db.session.delete(question)
    db.session.commit()
    # Recalculate total points for the exam
    exam.total_points = sum(q.points for q in exam.questions)
    db.session.commit()

    flash('Question deleted successfully.', 'success')
    return redirect(url_for('teacher.add_question', exam_id=exam.id))

# --- Assignment Management ---
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
            due_date=form.due_date.data,
                        class_id=form.class_id.data

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
        assignment.due_date = form.due_date.data
        assignment.class_id = form.class_id.data
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

# --- Assignment Task Management ---
@teacher_bp.route('/add_task/<int:assignment_id>', methods=['GET', 'POST'])
def add_task(assignment_id):
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
            task_type=form.task_type.data,
            instructions=form.instructions.data
        )
        db.session.add(new_task)
        db.session.commit()
        flash('Task added successfully.', 'success')
        return redirect(url_for('teacher.add_task', assignment_id=assignment.id))

    tasks = AssignmentTask.query.filter_by(assignment_id=assignment.id).all()
    return render_template('teacher/add_task.html', form=form, assignment=assignment, tasks=tasks)

@teacher_bp.route('/edit_task/<int:task_id>', methods=['GET', 'POST'])
def edit_task(task_id):
    """
    Route to edit an existing task.
    """
    task = AssignmentTask.query.get_or_404(task_id)
    assignment = Assignment.query.get_or_404(task.assignment_id)

    if assignment.teacher_id != current_user.id:
        flash('You are not authorized to edit this task.', 'danger')
        return redirect(url_for('teacher.dashboard'))

    form = AssignmentTaskForm(obj=task)
    if form.validate_on_submit():
        task.task_type = form.task_type.data
        task.instructions = form.instructions.data
        db.session.commit()
        flash('Task updated successfully.', 'success')
        return redirect(url_for('teacher.add_task', assignment_id=assignment.id))

    return render_template('teacher/edit_task.html', form=form, assignment=assignment, task=task)

@teacher_bp.route('/delete_task/<int:task_id>', methods=['POST'])
def delete_task(task_id):
    """
    Route to delete a task from an assignment.
    """
    task = AssignmentTask.query.get_or_404(task_id)
    assignment = Assignment.query.get_or_404(task.assignment_id)

    if assignment.teacher_id != current_user.id:
        flash('You are not authorized to delete this task.', 'danger')
        return redirect(url_for('teacher.dashboard'))

    db.session.delete(task)
    db.session.commit()
    flash('Task deleted successfully.', 'success')
    return redirect(url_for('teacher.add_task', assignment_id=assignment.id))

# --- View and Grade Assignment Submissions ---
@teacher_bp.route('/view_assignment_submissions/<int:assignment_id>')
def view_assignment_submissions(assignment_id):
    """
    Route to view all submissions for a specific assignment.
    """
    assignment = Assignment.query.get_or_404(assignment_id)
    if assignment.teacher_id != current_user.id:
        flash('You are not authorized to view submissions for this assignment.', 'danger')
        return redirect(url_for('teacher.dashboard'))

    submissions = (
        AssignmentSubmission.query
        .options(joinedload(AssignmentSubmission.student))
        .filter_by(assignment_id=assignment.id)
        .all()
    )
    tasks = AssignmentTask.query.filter_by(assignment_id=assignment.id).all()

    return render_template(
        'teacher/view_assignment_submissions.html',
        assignment=assignment,
        submissions=submissions,
        tasks=tasks
    )

@teacher_bp.route('/grade_submission/<int:submission_id>', methods=['GET', 'POST'])
def grade_submission(submission_id):
    """
    Route to grade a specific assignment submission.
    """
    submission = AssignmentSubmission.query.get_or_404(submission_id)

    if submission.assignment.teacher_id != current_user.id:
        flash('You are not authorized to grade this submission.', 'danger')
        return redirect(url_for('teacher.dashboard'))

    form = GradingForm(obj=submission)
    if form.validate_on_submit():
        submission.grade = form.grade.data
        submission.feedback = form.feedback.data
        submission.graded_at = datetime.utcnow()
        db.session.commit()
        flash('Grading saved successfully.', 'success')
        return redirect(url_for('teacher.view_assignment_submissions', assignment_id=submission.assignment.id))

    uploaded_file_url = None
    if submission.uploaded_filename:
        try:
            uploaded_file_url = url_for('student.uploaded_file', filename=submission.uploaded_filename)
        except Exception:
            uploaded_file_url = None

    return render_template(
        'teacher/grade_submission.html',
        form=form,
        submission=submission,
        assignment=submission.assignment,
        uploaded_file_url=uploaded_file_url
    )

@teacher_bp.route('/delete_submission/<int:submission_id>', methods=['POST'])
def delete_submission(submission_id):
    """
    Route to delete an assignment submission.
    """
    submission = AssignmentSubmission.query.get_or_404(submission_id)

    if submission.assignment.teacher_id != current_user.id:
        flash('You are not authorized to delete this submission.', 'danger')
        return redirect(url_for('teacher.dashboard'))

    if submission.uploaded_filename:
        file_path = os.path.join(
            current_app.config['ASSIGNMENTS_UPLOAD_FOLDER'],
            str(submission.assignment_id),
            str(submission.student_id),
            submission.uploaded_filename
        )
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                flash('Uploaded file deleted successfully.', 'info')
        except Exception as e:
            current_app.logger.error(f"Error deleting file {file_path}: {str(e)}")

    db.session.delete(submission)
    db.session.commit()
    flash('Submission deleted successfully.', 'success')
    return redirect(url_for('teacher.view_assignment_submissions', assignment_id=submission.assignment_id))

@teacher_bp.route('/subject_results/<int:subject_id>')
def view_subject_results(subject_id):
    """
    View student results for all exams in a specific subject.
    """
    subject = Subject.query.get_or_404(subject_id)
    exams = Exam.query.filter_by(subject_id=subject.id, teacher_id=current_user.id).all()

    exam_results_by_exam = {}

    for exam in exams:
        # eager-load الطالب مع النتائج
        results = (
            ExamResult.query
            .filter_by(exam_id=exam.id)
            .options(joinedload(ExamResult.student))
            .all()
        )
        # لضمان التوافق مع أي استخدام لاحق:
        for result in results:
            if not getattr(result, "student", None):
                result.student = User.query.get(result.student_id)
        exam_results_by_exam[exam] = results

    return render_template(
        'teacher/subject_results.html',
        title=f"Student Results for {subject.name}",
        subject=subject,
        exam_results_by_exam=exam_results_by_exam
    )

# --- Live Sessions Management ---
@teacher_bp.route('/live_sessions')
def live_sessions():
    """View live broadcast sessions."""
    sessions = LiveSession.query.filter_by(teacher_id=current_user.id).order_by(LiveSession.start_time.desc()).all()
    return render_template('teacher/live_sessions.html', sessions=sessions)

@teacher_bp.route('/start_live_session', methods=['GET', 'POST'])
def start_live_session():
    """Start a new live broadcast session."""
    # Prevent multiple active sessions for the same teacher
    if LiveSession.query.filter_by(teacher_id=current_user.id, is_active=True).first():
        flash('لديك بالفعل جلسة بث نشطة. يرجى إنهاؤها قبل بدء جلسة جديدة.', 'warning')
        return redirect(url_for('teacher.live_sessions'))

    try:
        form = LiveSessionForm()
        if form.validate_on_submit():
            timestamp = int(datetime.now().timestamp())
            stream_url = f"teacher_{current_user.id}_{timestamp}"

            new_session = LiveSession(
                teacher_id=current_user.id,
                subject_id=form.subject_id.data,
                title=form.title.data,
                description=form.description.data,
                stream_url=stream_url,
                is_active=True,
                start_time=datetime.utcnow()
            )

            if getattr(form, "is_private", None) and form.is_private.data:
                new_session.set_password(form.password.data)
                flash('تم إنشاء جلسة خاصة بكلمة مرور.', 'info')

            db.session.add(new_session)
            db.session.commit()

            flash('تم بدء جلسة البث المباشر بنجاح!', 'success')
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

    flash('Live session ended successfully.', 'success')
    # ✅ توجيه إلى قائمة الجلسات بدل صفحة البث غير النشطة
    return redirect(url_for('teacher.live_sessions'))
