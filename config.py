# config.py
import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'A_VERY_SECRET_AND_COMPLEX_KEY_THAT_NO_ONE_CAN_GUESS_EASILY'

    # استخدام MySQL مع بيانات الاتصال الصحيحة
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
    'postgresql+psycopg2://user:password@localhost/mydatabase'
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_recycle': 300,
        'pool_pre_ping': True,
    }
    
    # إضافة الإعدادات المطلوبة للمسارات
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    ASSIGNMENTS_UPLOAD_FOLDER = os.path.join(UPLOAD_FOLDER, 'assignments')
    
    # إعدادات إضافية للبث المباشر
    SOCKETIO_ASYNC_MODE = 'eventlet'
    
    # إضافة هذه الإعدادات الجديدة
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png', 'zip'}