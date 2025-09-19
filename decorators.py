from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user

def role_required(role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated or current_user.role != role:
                flash(f'هذه الصفحة مخصصة للمستخدمين ذوي دور {role} فقط.', 'warning')
                if current_user.role == 'admin':
                    return redirect(url_for('admin.dashboard'))
                elif current_user.role == 'teacher':
                    return redirect(url_for('teacher.dashboard'))
                elif current_user.role == 'student':
                    return redirect(url_for('student.dashboard'))
                else:
                    return redirect(url_for('auth.login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator