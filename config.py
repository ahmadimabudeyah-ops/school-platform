# config.py
import os
import re

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'A_VERY_SECRET_AND_COMPLEX_KEY_THAT_NO_ONE_CAN_GUESS_EASILY'

    # استخدام PostgreSQL بدلاً من MySQL
    DATABASE_URL = os.environ.get('DATABASE_URL') or \
        'postgresql://school_platform_db_user:bHoBASYJNXezYvDFmQOUuhXWuM266TX0@dpg-d36sddemcj7s73dustb0-a/school_platform_db'
    
    # تحويل postgres:// إلى postgresql:// إذا لزم الأمر
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    
    # استخدام المحرك بشكل صريح
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    
    # إجبار SQLAlchemy على استخدام psycopg2
    if 'postgresql' in SQLALCHEMY_DATABASE_URI:
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace('postgresql://', 'postgresql+psycopg2://', 1)
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_recycle': 300,
        'pool_pre_ping': True,
    }
    
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    ASSIGNMENTS_UPLOAD_FOLDER = os.path.join(UPLOAD_FOLDER, 'assignments')
    
    # إعدادات إضافية للبث المباشر
    SOCKETIO_ASYNC_MODE = 'eventlet'
    
    # إضافة هذه الإعدادات الجديدة
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png', 'zip'}