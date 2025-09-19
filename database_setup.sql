-- إنشاء قاعدة البيانات
CREATE DATABASE IF NOT EXISTS school_platform 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

-- إنشاء مستخدم للقاعدة البيانات
CREATE USER IF NOT EXISTS 'school_user'@'localhost' IDENTIFIED BY 'school_password';
GRANT ALL PRIVILEGES ON school_platform.* TO 'school_user'@'localhost';
FLUSH PRIVILEGES;

-- استخدام قاعدة البيانات
USE school_platform;

-- تأكد من إعدادات المحرف
SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;
SET COLLATION_CONNECTION = 'utf8mb4_unicode_ci';