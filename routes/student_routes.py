from flask import Blueprint, render_template, redirect, url_for, flash, request, send_from_directory
from flask_login import current_user, login_required
from datetime import datetime
from models import db, Exam, Assignment, Question, ExamResult, AssignmentSubmission, AssignmentTask, Choice, LiveSession
from forms import SubmissionForm
from config import Config
import os
from werkzeug.utils import secure_filename
from flask_wtf import FlaskForm
from decorators import role_required

student_bp = Blueprint('student', __name__)

class ExamForm(FlaskForm):
    pass

def validate_student_data():
    """التحقق من أن بيانات الطالب صحيحة قبل عرض المحتوى"""
    if current_user.role == 'student' and not current_user.class_id:
        flash('⚠ لم يتم تعيين صف دراسي لك. يرجى التواصل مع المدير.', 'warning')
        return False
    return True

@student_bp.route('/dashboard')
@login_required
def dashboard():
    current_time = datetime.utcnow()
    
    # بناء استعلام الاختبارات بشكل صحيح
    exam_query = Exam.query.filter(
        Exam.is_active == True,
    )
    
    # فقط إذا كان للطالب صف محدد، نضيف شرط الصف
    if current_user.class_id:
        exam_query = exam_query.filter(Exam.class_id == current_user.class_id)
    else:
        # إذا لم يكن للطالب صف محدد، لا نعرض أي اختبارات
        flash('⚠ لم يتم تعيين صف دراسي لك. لا يمكن عرض الاختبارات المتاحة.', 'warning')
    
    available_exams = exam_query.all()

    # بناء استعلام الواجبات بشكل صحيح
    assignment_query = Assignment.query.filter(
        Assignment.due_date >= current_time
    )
    
    if current_user.class_id:
        assignment_query = assignment_query.filter(Assignment.class_id == current_user.class_id)
    
    upcoming_assignments = assignment_query.all()

    student_submissions = AssignmentSubmission.query.filter_by(student_id=current_user.id).all()
    submitted_assignment_ids = {sub.assignment_id for sub in student_submissions}
    
    assignments_with_status = []
    for assignment in upcoming_assignments:
        submission = AssignmentSubmission.query.filter_by(
            assignment_id=assignment.id,
            student_id=current_user.id
        ).first()
        assignments_with_status.append({
            'assignment': assignment,
            'is_submitted': submission is not None,
            'submission': submission
        })

    exam_results = ExamResult.query.filter_by(student_id=current_user.id).order_by(ExamResult.submission_time.desc()).limit(5).all()

    return render_template('student/dashboard.html',
                           available_exams=available_exams,
                           assignments_with_status=assignments_with_status,
                           exam_results=exam_results)

@student_bp.route('/take_exam/<int:exam_id>', methods=['GET', 'POST'])
@login_required
def take_exam(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    form = ExamForm()

    # التحقق من أن الاختبار مخصص لصف الطالب
    if current_user.class_id and exam.class_id != current_user.class_id:
        flash('هذا الاختبار غير مخصص لصفك الدراسي.', 'warning')
        return redirect(url_for('student.dashboard'))

    if not exam.is_active:
        flash('الاختبار غير متاح حالياً.', 'warning')
        return redirect(url_for('student.dashboard'))

    questions = Question.query.filter_by(exam_id=exam.id).all()
    existing_result = ExamResult.query.filter_by(student_id=current_user.id, exam_id=exam.id).first()
    
    if existing_result:
        flash('لقد قمت بتقديم هذا الاختبار بالفعل.', 'info')
        return redirect(url_for('student.results'))

    if request.method == 'POST':
        if datetime.utcnow() > exam.end_time:
            flash('انتهى وقت الاختبار.', 'danger')
            return redirect(url_for('student.dashboard'))
        
        total_score = 0
        
        new_result = ExamResult(
            student_id=current_user.id,
            exam_id=exam.id,
            score=total_score,
            submission_time=datetime.utcnow()
        )
        db.session.add(new_result)
        db.session.flush()

        for question in questions:
            student_answer = request.form.get(str(question.id))
            
            if question.question_type == 'multiple_choice':
                selected_choice = Choice.query.filter_by(question_id=question.id, text=student_answer).first()
                if selected_choice and selected_choice.is_correct:
                    total_score += question.points
            elif question.question_type == 'short_answer':
                if student_answer and question.correct_answer and \
                   student_answer.strip().lower() == question.correct_answer.strip().lower():
                    total_score += question.points
            elif question.question_type == 'true_false':
                if student_answer and question.correct_answer and \
                   student_answer.lower() == question.correct_answer.lower():
                    total_score += question.points
        
        new_result.score = total_score
        db.session.commit()
        
        flash('تم تقديم الاختبار بنجاح.', 'success')
        return redirect(url_for('student.results'))
    
    return render_template('student/take_exam.html', exam=exam, questions=questions, form=form)

@student_bp.route('/assignments/submit/<int:assignment_id>', methods=['GET', 'POST'])
@login_required
def submit_assignment(assignment_id):
    assignment = Assignment.query.get_or_404(assignment_id)
    form = SubmissionForm()
    
    # التحقق من أن الواجب مخصص لصف الطالب
    if current_user.class_id and assignment.class_id != current_user.class_id:
        flash('هذا الواجب غير مخصص لصفك الدراسي.', 'warning')
        return redirect(url_for('student.dashboard'))
    
    existing_submission = AssignmentSubmission.query.filter_by(student_id=current_user.id, assignment_id=assignment.id).first()
    if existing_submission:
        flash('لقد قمت بتقديم هذا الواجب بالفعل.', 'info')
        return redirect(url_for('student.dashboard'))

    if request.method == 'POST':
        
        if datetime.utcnow() > assignment.due_date:
            flash('لا يمكن تقديم الواجب، لقد انتهى وقت الاستحقاق.', 'danger')
            return redirect(url_for('student.dashboard'))

        tasks_submitted = False
        task_ids = request.form.getlist('task_ids[]')
        
        upload_folder = os.path.join(Config.ASSIGNMENTS_UPLOAD_FOLDER, str(assignment.id), str(current_user.id))
        os.makedirs(upload_folder, exist_ok=True)
        
        for task_id in task_ids:
            task = AssignmentTask.query.get(task_id)
            if not task:
                continue
            
            answer_text = None
            filename = None
            
            if task.task_type == 'short_answer':
                answer_text = request.form.get(f'answer_text_{task_id}')
                if answer_text:
                    tasks_submitted = True
            elif task.task_type == 'file_upload':
                uploaded_file = request.files.get(f'file_upload_{task_id}')
                if uploaded_file and uploaded_file.filename != '':
                    filename = secure_filename(uploaded_file.filename)
                    file_path = os.path.join(upload_folder, filename)
                    uploaded_file.save(file_path)
                    tasks_submitted = True
            
            if answer_text or filename:
                submission = AssignmentSubmission(
                    student_id=current_user.id,
                    assignment_id=assignment.id,
                    task_id=task.id,
                    answer_text=answer_text,
                    uploaded_filename=filename,
                    submission_time=datetime.utcnow()
                )
                db.session.add(submission)
        
        if tasks_submitted:
            db.session.commit()
            flash('تم تقديم الواجب بنجاح.', 'success')
            return redirect(url_for('student.dashboard'))
        else:
            flash('لم يتم تقديم أي إجابات. يرجى إدخال إجابة واحدة على الأقل.', 'danger')

    tasks = AssignmentTask.query.filter_by(assignment_id=assignment.id).all()
    
    return render_template('student/submit_assignment.html', assignment=assignment, tasks=tasks, form=form)

@student_bp.route('/my_submissions/<int:assignment_id>')
@login_required
def my_submissions(assignment_id):
    assignment = Assignment.query.get_or_404(assignment_id)
    
    # التحقق من أن الواجب مخصص لصف الطالب
    if current_user.class_id and assignment.class_id != current_user.class_id:
        flash('هذا الواجب غير مخصص لصفك الدراسي.', 'warning')
        return redirect(url_for('student.dashboard'))
    
    submissions = AssignmentSubmission.query.filter_by(
        student_id=current_user.id,
        assignment_id=assignment.id
    ).all()
    
    submissions_with_tasks = []
    for sub in submissions:
        task = AssignmentTask.query.get(sub.task_id)
        submissions_with_tasks.append({
            'submission': sub,
            'task': task
        })
    
    return render_template('student/my_submissions.html', 
                            assignment=assignment, 
                            submissions_with_tasks=submissions_with_tasks)

@student_bp.route('/my_results')
@login_required
def results():
    exam_results = ExamResult.query.filter_by(student_id=current_user.id).order_by(ExamResult.submission_time.desc()).all()
    
    assignment_submissions = db.session.query(Assignment).join(AssignmentSubmission).filter(AssignmentSubmission.student_id == current_user.id).group_by(Assignment.id).all()

    results_for_assignments = []
    for assignment in assignment_submissions:
        submissions = AssignmentSubmission.query.filter_by(student_id=current_user.id, assignment_id=assignment.id).all()
        total_grade = sum(sub.grade for sub in submissions if sub.grade is not None)
        results_for_assignments.append({
            'assignment': assignment,
            'grade': total_grade
        })

    return render_template('student/results.html', exam_results=exam_results, results_for_assignments=results_for_assignments)
    
@student_bp.route('/download_submission/<int:submission_id>')
@login_required
def download_submission(submission_id):
    submission = AssignmentSubmission.query.get_or_404(submission_id)

    if submission.student_id != current_user.id:
        flash('ليس لديك صلاحية للوصول لهذا الملف.', 'danger')
        return redirect(url_for('student.dashboard'))
    
    if not submission.uploaded_filename:
        flash('لا يوجد ملف مرفق لهذه الإجابة.', 'warning')
        return redirect(url_for('student.dashboard'))

    base_folder = os.path.join(Config.ASSIGNMENTS_UPLOAD_FOLDER, str(submission.assignment_id), str(submission.student_id))
    
    try:
        return send_from_directory(base_folder, submission.uploaded_filename, as_attachment=True)
    except FileNotFoundError:
        flash('الملف المطلوب غير موجود.', 'danger')
        return redirect(url_for('student.dashboard'))

@student_bp.route('/live_sessions')
@login_required
def live_sessions():
    """عرض جلسات البث المباشر المتاحة"""
    active_sessions = LiveSession.query.filter_by(is_active=True).all()
    return render_template('student/live_sessions.html', sessions=active_sessions)

@student_bp.route('/watch_live/<int:session_id>')
@login_required
def watch_live(session_id):
    """صفحة مشاهدة البث المباشر"""
    session = LiveSession.query.get_or_404(session_id)
    if not session.is_active:
        flash('هذه الجلسة غير نشطة حالياً.', 'warning')
        return redirect(url_for('student.dashboard'))
    return render_template('student/watch_live.html', session=session)