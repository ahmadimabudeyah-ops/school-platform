# models.py
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# تهيئة كائن قاعدة البيانات
db = SQLAlchemy()

class Class(db.Model):
    """
    نموذج الصفوف الدراسية.
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)  # مثال: "الصف الأول الابتدائي"
    description = db.Column(db.Text, nullable=True)

    # علاقات
    students = db.relationship('User', backref='class_rel', lazy=True, foreign_keys='User.class_id')
    subjects = db.relationship('Subject', backref='class_rel', lazy=True)
    exams = db.relationship('Exam', backref='class_rel', lazy=True)
    assignments = db.relationship('Assignment', backref='class_rel', lazy=True)

    def __repr__(self):
        return f"<Class {self.name}>"

class User(db.Model, UserMixin):
    """
    نموذج المستخدمين (طلاب، معلمين، مديرين).
    """
    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(10), nullable=False)  # 'admin', 'teacher', 'student'
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    # إضافة حقل الصف للمستخدمين
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=True)  # للطلاب فقط

    # علاقات:
    exams_created = db.relationship('Exam', backref='creator', lazy=True, foreign_keys='Exam.teacher_id')
    assignments_created = db.relationship('Assignment', backref='creator', lazy=True, foreign_keys='Assignment.teacher_id')
    exam_results = db.relationship('ExamResult', backref='student', lazy=True)
    assignment_submissions = db.relationship('AssignmentSubmission', backref='student', lazy=True)
    live_sessions = db.relationship('LiveSession', backref='teacher', lazy=True)
    
    def __init__(self, username, email, role, password, class_id=None):
        self.username = username
        self.email = email
        self.role = role
        self.class_id = class_id
        self.set_password(password)

    def set_password(self, password):
        """يقوم بتجزئة كلمة المرور وحفظها."""
        try:
            # تأكد من استخدام نفس الطريقة للمدير والمعلمين والطلاب
            self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')
            print(f"✅ تم تجزئة كلمة المرور للمستخدم: {self.username}")
        except Exception as e:
            print(f"❌ خطأ في تجزئة كلمة المرور: {str(e)}")
            raise e

    def check_password(self, password):
        """يتحقق من صحة كلمة المرور."""
        try:
            # تنظيف كلمة المرور من المسافات الزائدة
            cleaned_password = password.strip()
            
            # استخدام check_password_hash مباشرة
            result = check_password_hash(self.password_hash, cleaned_password)
            
            print(f"🔐 التحقق من كلمة المرور للمستخدم {self.username}: {result}")
            return result
        except Exception as e:
            print(f"❌ خطأ في التحقق من كلمة المرور: {str(e)}")
            return False

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"


class Subject(db.Model):
    """
    نموذج المواد الدراسية.
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)

    # إضافة حقل الصف للمواد الدراسية
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=False)

    # علاقات:
    exams = db.relationship('Exam', backref='subject', lazy=True)
    assignments = db.relationship('Assignment', backref='subject', lazy=True)
    live_sessions = db.relationship('LiveSession', backref='subject', lazy=True)

    def __repr__(self):
        return f"<Subject {self.name}>"


class Exam(db.Model):
    """
    نموذج الاختبارات التي ينشئها المعلمون.
    """
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    total_points = db.Column(db.Float, default=0.0, nullable=False)

    # إضافة حقل الصف للاختبارات
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=False)

    # علاقات:
    questions = db.relationship('Question', backref='exam', lazy=True, cascade='all, delete-orphan')
    exam_results = db.relationship('ExamResult', backref='exam', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Exam {self.title}>"


class Question(db.Model):
    """
    نموذج الأسئلة داخل الاختبارات.
    """
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exam.id'), nullable=False)
    question_type = db.Column(db.String(50), nullable=False)  # 'multiple_choice', 'short_answer', 'true_false'
    text = db.Column(db.Text, nullable=False)
    correct_answer = db.Column(db.Text, nullable=True)
    points = db.Column(db.Float, nullable=False, default=1.0)

    # علاقات:
    choices = db.relationship('Choice', backref='question', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Question {self.id} ({self.question_type})>"


class Choice(db.Model):
    """
    نموذج خيارات الإجابة لأسئلة الاختيار من متعدد.
    """
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    text = db.Column(db.String(500), nullable=False)
    is_correct = db.Column(db.Boolean, default=False, nullable=False)

    def __repr__(self):
        return f"<Choice {self.text} (Correct: {self.is_correct})>"


class ExamResult(db.Model):
    """
    نموذج نتائج الطلاب في الاختبارات.
    """
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exam.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    score = db.Column(db.Float, nullable=False, default=0.0)
    submission_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('exam_id', 'student_id', name='_student_exam_uc'),)

    def __repr__(self):
        return f"<ExamResult Student: {self.student_id}, Exam: {self.exam_id}, Score: {self.score}>"


class Assignment(db.Model):
    """
    نموذج الواجبات التي ينشئها المعلمون.
    """
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    due_date = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # إضافة حقل الصف للواجبات
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=False)

    # علاقات:
    tasks = db.relationship('AssignmentTask', backref='assignment', lazy=True, cascade='all, delete-orphan')
    submissions = db.relationship('AssignmentSubmission', backref='assignment', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Assignment {self.title}>"


class AssignmentTask(db.Model):
    """
    نموذج المهام داخل الواجب.
    """
    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignment.id'), nullable=False)
    task_type = db.Column(db.String(20), nullable=False)  # 'short_answer', 'file_upload'
    instructions = db.Column(db.Text, nullable=False)

    def __repr__(self):
        return f"<AssignmentTask {self.task_type} for Assignment {self.assignment_id}>"


class AssignmentSubmission(db.Model):
    """
    نموذج تقديمات الطلاب للواجبات.
    """
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('assignment_task.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignment.id'), nullable=False)

    answer_text = db.Column(db.Text, nullable=True)
    uploaded_filename = db.Column(db.String(255), nullable=True)
    submission_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    grade = db.Column(db.Float, nullable=True)
    feedback = db.Column(db.Text, nullable=True)
    graded_at = db.Column(db.DateTime, nullable=True)

    # علاقة ربط المهمة بالتقديم
    assignment_task = db.relationship('AssignmentTask', backref='submissions')

    __table_args__ = (db.UniqueConstraint('assignment_id', 'student_id', name='_student_assignment_uc'),)

    def __repr__(self):
        return f"<AssignmentSubmission Task: {self.task_id}, Student: {self.student_id}>"


class LiveSession(db.Model):
    """
    نموذج لجلسات البث المباشر التي ينشئها المعلمون.
    """
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    start_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    end_time = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    stream_url = db.Column(db.String(500), nullable=True)

    # العلاقة مع المادة
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=True)

    # إضافة كلمة المرور للجلسات الخاصة
    password_hash = db.Column(db.String(128), nullable=True)

    # علاقة مع تسجيلات الجلسة
    recordings = db.relationship('LiveSessionRecording', backref='live_session', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<LiveSession {self.title}>"


class LiveSessionRecording(db.Model):
    """
    نموذج لتسجيلات جلسات البث المباشر.
    """
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('live_session.id'), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    duration = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f"<LiveSessionRecording for session {self.session_id}>"