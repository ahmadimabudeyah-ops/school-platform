#!/usr/bin/env python3
"""
نقطة الدخول الرئيسية لتشغيل التطبيق
"""
import os
import sys

# إضافة المسار الحالي إلى sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, socketio
from models import db # استيراد كائن db

if __name__ == '__main__':
    print("Starting School Platform with MySQL...")
    print(f"Database URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
    
    # ✅ تم نقل إنشاء الجداول إلى ملف app.py ليكون في مكان مركزي
    # يرجى التأكد من أن قاعدة البيانات 'school_platform' موجودة يدوياً
    
    # تشغيل التطبيق مع SocketIO
    socketio.run(
        app, 
        debug=True, 
        host='0.0.0.0', 
        port=5000,
        use_reloader=True,
        log_output=True
    )