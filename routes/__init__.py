from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user
from models import db, User, Class
from forms import LoginForm, StudentRegistrationForm, TeacherRegistrationForm

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        
        if user and user.check_password(form.password.data):
            if user.role == 'student' and user.class_id is None:
                flash('حساب الطالب غير مكتمل. يرجى التواصل مع المدير.', 'warning')
                return render_template('auth/login.html', form=form)
            if user.role == 'teacher' and user.class_id is not None:
                flash('حساب المعلم يحتوي على بيانات غير صحيحة. يرجى التواصل مع المدير.', 'warning')
                return render_template('auth/login.html', form=form)
            
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('البريد الإلكتروني أو كلمة المرور غير صحيحة', 'danger')
    
    return render_template('auth/login.html', form=form)

@auth_bp.route('/student/register', methods=['GET', 'POST'])
def student_register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = StudentRegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            role='student',
            class_id=form.class_id.data  
        )
        user.set_password(form.password.data)
        db.session.add(user)
        try:
            db.session.commit()
            flash('تم تسجيل الطالب بنجاح. يمكنك الآن تسجيل الدخول.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            flash(f'خطأ في التسجيل: {str(e)}', 'danger')
    
    return render_template('auth/student_register.html', form=form)

@auth_bp.route('/teacher/register', methods=['GET', 'POST'])
def teacher_register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = TeacherRegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            role='teacher',
            class_id=None 
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('تم تسجيل المعلم بنجاح. يمكنك الآن تسجيل الدخول.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/teacher_register.html', form=form)

@auth_bp.route('/logout')
def logout():
    logout_user()
    flash('تم تسجيل الخروج بنجاح.', 'info')
    return redirect(url_for('auth.login'))