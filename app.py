# app.py
import os
import logging
from datetime import datetime

from flask import Flask, redirect, url_for, request
from flask_login import LoginManager, current_user
from flask_wtf.csrf import CSRFProtect
from flask_socketio import SocketIO, emit, join_room, leave_room

from models import db, User
from config import Config

# Blueprints
from routes.auth_routes import auth_bp
from routes.admin_routes import admin_bp
from routes.teacher_routes import teacher_bp
from routes.student_routes import student_bp

# =========================
# إعداد Flask-Login
# =========================
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = "الرجاء تسجيل الدخول للوصول إلى هذه الصفحة."
login_manager.login_message_category = "info"


@login_manager.user_loader
def load_user(user_id):
    try:
        return User.query.get(int(user_id))
    except Exception:
        return None


# =========================
# إنشاء تطبيق Flask
# =========================
def create_app():
    app = Flask(__name__)

    # تحميل الإعدادات من الفئة Config
    app.config.from_object(Config)

    # تحميل متغيرات البيئة من ملف .env إذا كان موجوداً
    try:
        from dotenv import load_dotenv
        load_dotenv()
        # إذا كان هناك متغير بيئة لرابط قاعدة البيانات، استخدمه
        if os.environ.get('DATABASE_URL'):
            app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
            # تحويل postgres:// إلى postgresql:// إذا لزم الأمر
            if app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgres://'):
                app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace('postgres://', 'postgresql://', 1)
    except ImportError:
        pass

    # DB + Login + CSRF
    db.init_app(app)
    login_manager.init_app(app)
    CSRFProtect(app)

    # Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(teacher_bp, url_prefix='/teacher')
    app.register_blueprint(student_bp, url_prefix='/student')

    # صفحة البداية
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            if getattr(current_user, "role", None) == 'admin':
                return redirect(url_for('admin.dashboard'))
            elif current_user.role == 'teacher':
                return redirect(url_for('teacher.dashboard'))
            elif current_user.role == 'student':
                return redirect(url_for('student.dashboard'))
        return redirect(url_for('auth.login'))

    # تمرير datetime للقوالب
    @app.context_processor
    def inject_datetime():
        return dict(datetime=datetime)

    # إنشاء مجلدات الرفع إن لم تكن موجودة
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['ASSIGNMENTS_UPLOAD_FOLDER'], exist_ok=True)

    # تهيئة قاعدة البيانات وإنشاء مدير افتراضي
    with app.app_context():
        try:
            db.create_all()
            print("✅ تم إنشاء الجداول بنجاح")
            
            # إنشاء مدير افتراضي إذا لم يكن موجوداً
            admin_user = User.query.filter_by(role='admin').first()
            if not admin_user:
                admin_user = User(
                    username='admin',
                    email='admin@school.com',
                    role='admin',
                    password='admin123'
                )
                db.session.add(admin_user)
                db.session.commit()
                print("✅ تم إنشاء المستخدم المدير الافتراضي")
                
        except Exception as e:
            print(f"❌ خطأ في تهيئة قاعدة البيانات: {str(e)}")
            # في حالة الخطأ، لا توقف التطبيق ولكن سجل الخطأ فقط

    return app


app = create_app()

# =========================
# تهيئة Socket.IO
# =========================
async_mode = 'threading'

socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    manage_session=True,
    async_mode=async_mode,
    logger=True,
    engineio_logger=True
)

# =========================
# إدارة جلسات البث
# =========================
sessions_map = {}


# =========================
# Socket.IO Events
# =========================
@socketio.on('connect')
def handle_connect():
    print(f"User connected: {request.sid}")


@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    print(f"User disconnected: {sid}")

    for session_id, info in list(sessions_map.items()):
        teacher_sid = info["teacher_sid"]
        viewers = info["active_viewers"]

        if sid == teacher_sid:
            emit('teacher_left', {}, room=session_id, include_self=False)
            info["teacher_sid"] = None
            continue

        if sid in viewers:
            viewers.discard(sid)
            if teacher_sid:
                emit('peer_left', {'student_sid': sid}, room=teacher_sid, include_self=False)

        # تنظيف الجلسة إذا أصبحت فارغة
        if not info["teacher_sid"] and len(info["active_viewers"]) == 0:
            sessions_map.pop(session_id, None)


@socketio.on('join_live_session')
def handle_join_live_session(data):
    session_id = str(data.get('session_id'))
    user_type = data.get('user_type')

    if not session_id or not user_type:
        return

    # إنشاء الجلسة إذا لم تكن موجودة
    info = sessions_map.setdefault(session_id, {
        "teacher_sid": None,
        "active_viewers": set(),
        "start_time": datetime.utcnow()
    })

    join_room(session_id)

    if user_type == 'teacher':
        info["teacher_sid"] = request.sid
        emit('teacher_live', {'status': 'Teacher is live'}, room=session_id, include_self=False)
        print(f"Teacher {request.sid} joined session {session_id}")

    elif user_type == 'student':
        if not info["teacher_sid"]:
            emit('no_teacher', {'message': 'لا يوجد معلم في الجلسة حاليًا.'}, room=request.sid)
            return

        info["active_viewers"].add(request.sid)
        emit('teacher_joined', {'teacher_sid': info["teacher_sid"]}, room=request.sid)
        print(f"Student {request.sid} joined session {session_id}")


@socketio.on('leave_live_session')
def handle_leave_live_session(data):
    session_id = str(data.get('session_id'))
    user_type = data.get('user_type')

    if not session_id or not user_type:
        return

    info = sessions_map.get(session_id)
    if not info:
        return

    leave_room(session_id)

    if user_type == 'teacher' and info["teacher_sid"] == request.sid:
        info["teacher_sid"] = None
        emit('teacher_left', {}, room=session_id, include_self=False)

    elif user_type == 'student':
        if request.sid in info["active_viewers"]:
            info["active_viewers"].discard(request.sid)
            if info["teacher_sid"]:
                emit('peer_left', {'student_sid': request.sid}, room=info["teacher_sid"], include_self=False)


# ============ Signaling Events ============
@socketio.on('viewer_offer')
def handle_viewer_offer(data):
    """Server receives a viewer Offer and routes it to the teacher."""
    teacher_sid = data.get('teacher_sid')
    sdp = data.get('sdp')

    if not teacher_sid or not sdp:
        return

    emit('viewer_offer', {
        'from_sid': request.sid,
        'sdp': sdp
    }, room=teacher_sid)


@socketio.on('viewer_answer')
def handle_viewer_answer(data):
    """Server receives an Answer from the teacher and routes it to the specified student."""
    to_sid = data.get('to_sid')
    sdp = data.get('sdp')

    if not to_sid or not sdp:
        return

    emit('viewer_answer', {'sdp': sdp}, room=to_sid)


@socketio.on('ice_candidate')
def handle_ice_candidate(data):
    """All peers send {to: <sid>, candidate: {...}} to be routed to the other peer."""
    to_sid = data.get('to')
    candidate = data.get('candidate')

    if not to_sid or not candidate:
        return

    emit('ice_candidate', {'candidate': candidate, 'from': request.sid}, room=to_sid)


# ============ Chat Messaging ============
@socketio.on('send_message')
def handle_send_message(data):
    session_id = str(data.get('session_id'))
    if not session_id:
        return

    emit('new_message', {
        'user': getattr(current_user, "username", "Anonymous"),
        'message': data.get('message'),
        'user_type': data.get('user_type'),
        'timestamp': datetime.utcnow().isoformat()
    }, room=session_id)


if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)