from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import current_user, login_required
from models import db, User, Subject, Exam, Assignment, Class, ExamResult, AssignmentSubmission
from forms import RegistrationForm, SubjectForm, ClassForm
from decorators import role_required
from datetime import datetime

# إنشاء Blueprint لمسارات المدير
admin_bp = Blueprint('admin', __name__)

### -------- لوحة تحكم المشرف -------- ###

@admin_bp.route('/dashboard')
@login_required
@role_required('admin')
def dashboard():
    """
    صفحة لوحة تحكم المدير تعرض قائمة بالمستخدمين والمواد الدراسية.
    """
    users = User.query.all()
    subjects = Subject.query.all()
    classes = Class.query.all()
    return render_template('admin/dashboard.html', 
                         users=users, 
                         subjects=subjects, 
                         classes=classes)

@admin_bp.route('/create_user', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def create_user():
    """
    مسار لإنشاء مستخدم جديد (معلم أو طالب) بواسطة المدير.
    """
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            role=form.role.data,
            password=form.password.data
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash(f'تم إنشاء المستخدم {user.username} بنجاح.', 'success')
        return redirect(url_for('admin.dashboard'))
    return render_template('admin/create_user.html', form=form)

@admin_bp.route('/delete_user/<int:user_id>', methods=['POST'])
@login_required
@role_required('admin')
def delete_user(user_id):
    """
    مسار لحذف مستخدم بواسطة المدير.
    """
    if user_id == current_user.id:
        flash('لا يمكنك حذف حسابك الخاص.', 'danger')
        return redirect(url_for('admin.dashboard'))

    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash(f'تم حذف المستخدم {user.username} بنجاح.', 'success')
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/add_subject', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def add_subject():
    """
    مسار لإضافة مادة دراسية جديدة بواسطة المدير.
    """
    form = SubjectForm()
    if form.validate_on_submit():
        subject = Subject(
            name=form.name.data, 
            description=form.description.data,
            class_id=form.class_id.data
        )
        db.session.add(subject)
        db.session.commit()
        flash(f'تمت إضافة المادة "{subject.name}" بنجاح.', 'success')
        return redirect(url_for('admin.dashboard'))
    return render_template('admin/add_subject.html', form=form)

@admin_bp.route('/delete_subject/<int:subject_id>', methods=['POST'])
@login_required
@role_required('admin')
def delete_subject(subject_id):
    """
    مسار لحذف مادة دراسية بواسطة المدير.
    """
    subject = Subject.query.get_or_404(subject_id)
    db.session.delete(subject)
    db.session.commit()
    flash(f'تم حذف المادة "{subject.name}" بنجاح.', 'success')
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/review_exams')
@login_required
@role_required('admin')
def review_exams():
    """
    مسار لمراجعة جميع الاختبارات في النظام.
    """
    exams = Exam.query.all()
    return render_template('admin/review_exams.html', exams=exams)

@admin_bp.route('/review_assignments')
@login_required
@role_required('admin')
def review_assignments():
    """
    مسار لمراجعة جميع الواجبات في النظام.
    """
    assignments = Assignment.query.all()
    return render_template('admin/review_assignments.html', assignments=assignments)

### -------- إدارة الصفوف -------- ###

@admin_bp.route('/classes')
@login_required
@role_required('admin')
def classes_list():
    classes = Class.query.all()
    return render_template('admin/classes_list.html', classes=classes)

@admin_bp.route('/class/add', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def add_class():
    form = ClassForm()
    if form.validate_on_submit():
        class_ = Class(name=form.name.data, description=form.description.data)
        db.session.add(class_)
        db.session.commit()
        flash('تم إضافة الصف بنجاح.', 'success')
        return redirect(url_for('admin.classes_list'))
    
    return render_template('admin/add_class.html', form=form)

@admin_bp.route('/class/delete/<int:class_id>', methods=['POST'])
@login_required
@role_required('admin')
def delete_class(class_id):
    """
    مسار لحذف صف دراسي بواسطة المدير.
    """
    class_ = Class.query.get_or_404(class_id)
    
    if class_.students or class_.subjects:
        flash('لا يمكن حذف الصف لأنه يحتوي على طلاب أو مواد مرتبطة به.', 'danger')
        return redirect(url_for('admin.classes_list'))
    
    db.session.delete(class_)
    db.session.commit()
    flash(f'تم حذف الصف "{class_.name}" بنجاح.', 'success')
    return redirect(url_for('admin.classes_list'))

### -------- التقارير والإحصائيات -------- ###

@admin_bp.route('/reports')
@login_required
@role_required('admin')
def reports():
    """
    صفحة التقارير والإحصائيات للمدير.
    """
    students = User.query.filter_by(role='student').all()
    teachers = User.query.filter_by(role='teacher').all()
    classes = Class.query.all()
    exam_results = ExamResult.query.all()
    
    return render_template('admin/reports.html', 
                         students=students,
                         teachers=teachers,
                         classes=classes,
                         exam_results=exam_results)

@admin_bp.route('/assignments_report')
@login_required
@role_required('admin')
def assignments_report():
    """
    تقرير شامل لتسليم الواجبات وتقييمها.
    """
    # جلب جميع الواجبات مع معلوماتها - التصحيح هنا
    assignments = Assignment.query.options(
        db.joinedload(Assignment.subject),
        db.joinedload(Assignment.creator),
        db.joinedload(Assignment.class_rel)  # تم التغيير إلى class_rel
    ).all()
    
    # جلب جميع التقديمات مع معلومات الطلاب
    submissions = AssignmentSubmission.query.options(
        db.joinedload(AssignmentSubmission.student),
        db.joinedload(AssignmentSubmission.assignment),
        db.joinedload(AssignmentSubmission.assignment_task)
    ).all()
    
    # جلب جميع الطلاب
    students = User.query.filter_by(role='student').all()
    
    # تنظيم البيانات للتقرير
    report_data = []
    for assignment in assignments:
        assignment_info = {
            'id': assignment.id,
            'title': assignment.title,
            'subject': assignment.subject.name if assignment.subject else 'غير محدد',
            'teacher': assignment.creator.username,
            'class': assignment.class_rel.name if assignment.class_rel else 'غير محدد',  # تم التغيير إلى class_rel
            'due_date': assignment.due_date,
            'submissions': [],
            'not_submitted': []
        }
        
        # إيجاد التقديمات لهذا الواجب
        for submission in submissions:
            if submission.assignment_id == assignment.id:
                submission_info = {
                    'student_name': submission.student.username,
                    'student_class': submission.student.class_rel.name if submission.student.class_rel else 'غير محدد',  # تم التغيير إلى class_rel
                    'submission_time': submission.submission_time,
                    'grade': submission.grade,
                    'feedback': submission.feedback,
                    'graded_at': submission.graded_at,
                    'status': 'مسلم ومقيم' if submission.grade is not None else 'مسلم بانتظار التقييم'
                }
                assignment_info['submissions'].append(submission_info)
        
        # إيجاد الطلاب الذين لم يسلموا الواجب
        for student in students:
            if student.class_id == assignment.class_id:
                submitted = any(s['student_name'] == student.username for s in assignment_info['submissions'])
                if not submitted:
                    assignment_info['not_submitted'].append({
                        'student_name': student.username,
                        'student_class': student.class_rel.name if student.class_rel else 'غير محدد'  # تم التغيير إلى class_rel
                    })
        
        report_data.append(assignment_info)
    
    return render_template('admin/assignments_report.html', 
                         report_data=report_data,
                         datetime=datetime)

@admin_bp.route('/users_management')
@login_required
@role_required('admin')
def users_management():
    """
    صفحة إدارة المستخدمين مع عرض كلمات المرور (لأغراض إدارية فقط)
    """
    users = User.query.all()
    
    # تجهيز بيانات المستخدمين مع معلومات إضافية
    users_data = []
    for user in users:
        user_info = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': user.role,
            'class_name': user.class_rel.name if user.class_rel else 'غير محدد',
            'created_exams': len(user.exams_created),
            'created_assignments': len(user.assignments_created),
            'exam_results': len(user.exam_results),
            'is_active': True  # يمكن إضافة حقل نشط في النموذج لاحقاً
        }
        users_data.append(user_info)
    
    return render_template('admin/users_management.html', 
                         users=users_data,
                         users_count=len(users_data))

@admin_bp.route('/reset_user_password', methods=['POST'])
@login_required
@role_required('admin')
def reset_user_password():
    """
    إعادة تعيين كلمة مرور مستخدم - النسخة المحسنة
    """
    try:
        user_id = request.form.get('user_id')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # التحقق من البيانات المطلوبة
        if not user_id or not new_password:
            flash('بيانات غير مكتملة.', 'danger')
            return redirect(url_for('admin.users_management'))
        
        # التحقق من تطابق كلمات المرور
        if new_password != confirm_password:
            flash('كلمتا المرور غير متطابقتين!', 'danger')
            return redirect(url_for('admin.users_management'))
        
        # التحقق من طول كلمة المرور
        if len(new_password) < 6:
            flash('كلمة المرور يجب أن تكون 6 أحرف على الأقل!', 'danger')
            return redirect(url_for('admin.users_management'))
        
        # البحث عن المستخدم
        user = User.query.get_or_404(user_id)
        
        # منع المستخدم من تغيير كلمة مروره الخاصة (اختياري)
        if user.id == current_user.id:
            flash('لا يمكنك تغيير كلمة مرور حسابك من هنا. استخدم صفحة الملف الشخصي.', 'warning')
            return redirect(url_for('admin.users_management'))
        
        # إعادة تعيين كلمة المرور
        user.set_password(new_password)
        db.session.commit()
        
        flash(f'تم إعادة تعيين كلمة مرور المستخدم {user.username} بنجاح.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'حدث خطأ أثناء إعادة تعيين كلمة المرور: {str(e)}', 'danger')
    
    return redirect(url_for('admin.users_management'))