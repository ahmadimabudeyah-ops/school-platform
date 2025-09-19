from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user
from models import db, User, Class
from forms import LoginForm, StudentRegistrationForm, TeacherRegistrationForm

auth_bp = Blueprint('auth', __name__)
# auth_routes.py

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user
from models import db, User
from forms import LoginForm

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        # استخدام strip() لإزالة المسافات الزائدة من البداية والنهاية
        email_input = form.email.data.strip()
        password_input = form.password.data.strip()
        
        print(f"البريد المدخل: '{email_input}'")
        print(f"كلمة المرور المدخلة (بعد التنظيف): '{password_input}'")
        
        user = User.query.filter_by(email=email_input).first()
        
        if user:
            print(f"تم العثور على المستخدم: {user.username}")
            print(f"دور المستخدم: {user.role}")
            
            # تحقق من كلمة المرور الصحيحة
            password_correct = user.check_password(password_input)
            print(f"نتيجة التحقق من كلمة المرور: {password_correct}")
            
            if password_correct:
                print("كلمة المرور صحيحة")
                login_user(user)
                
                # توجيه المستخدم بعد تسجيل الدخول
                next_page = request.args.get('next')
                return redirect(next_page) if next_page else redirect(url_for('index'))
            else:
                print("كلمة المرور غير صحيحة")
                flash('البريد الإلكتروني أو كلمة المرور غير صحيحة', 'danger')
        else:
            print("لم يتم العثور على مستخدم بهذا البريد الإلكتروني")
            flash('البريد الإلكتروني أو كلمة المرور غير صحيحة', 'danger')
    
    return render_template('auth/login.html', form=form)

#auth_routes.py

@auth_bp.route('/student/register', methods=['GET', 'POST'])
def student_register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = StudentRegistrationForm()
    if form.validate_on_submit():
        print(f"البريد المدخل: '{form.email.data}'")
        print(f"كلمة المرور المدخلة: '{form.password.data}'")
        user = User(
            username=form.username.data,
            email=form.email.data,
            role='student',
            class_id=form.class_id.data,
            password=form.password.data,  

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

#auth_routes.py

@auth_bp.route('/teacher/register', methods=['GET', 'POST'])
def teacher_register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = TeacherRegistrationForm()
    if form.validate_on_submit():
        print(f"البريد المدخل: '{form.email.data}'")
        print(f"كلمة المرور المدخلة: '{form.password.data}'")
        user = User(
            username=form.username.data,
            email=form.email.data,
            role='teacher',
            password=form.password.data,
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


@auth_bp.route('/reset_admin_password')
def reset_admin_password():
    """Route مؤقت لإعادة تعيين كلمة مرور المدير (لأغراض التطوير فقط)"""
    admin_user = User.query.filter_by(role='admin').first()
    if admin_user:
        admin_user.set_password('admin')
        db.session.commit()
        flash('تم إعادة تعيين كلمة مرور المدير إلى "admin"', 'success')
    else:
        flash('لم يتم العثور على مستخدم مدير', 'danger')
    return redirect(url_for('auth.login'))


@auth_bp.route('/debug_password')
def debug_password():
    """Route لفحص مشكلة كلمة المرور"""
    admin_user = User.query.filter_by(role='admin').first()
    if admin_user:
        print("=== معلومات المدير ===")
        print(f"Username: {admin_user.username}")
        print(f"Email: {admin_user.email}")
        print(f"Password Hash: {admin_user.password_hash}")
        
        # اختبار كلمات مرور مختلفة
        test_passwords = ['admin', 'adminpassword', 'password', '123456']
        for pwd in test_passwords:
            result = admin_user.check_password(pwd)
            print(f"كلمة المرور '{pwd}': {result}")
        
        return "تم فحص كلمة المرور - راجع console للنتائج"
    return "لم يتم العثور على المدير"
@auth_bp.route('/reset_ali_password')
def reset_ali_password():
    ali_user = User.query.filter_by(email='ali@gmail.com').first()
    if ali_user:
        ali_user.set_password('123456')
        db.session.commit()
        flash('تم إعادة تعيين كلمة مرور المستخدم ali إلى "123456"', 'success')
    else:
        flash('لم يتم العثور على المستخدم', 'danger')
    return redirect(url_for('auth.login'))