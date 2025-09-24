# forms.py
from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, SubmitField, TextAreaField, SelectField,
    BooleanField, DateTimeField, FileField, FloatField
)
from wtforms.validators import (
    DataRequired, Length, Email, EqualTo, ValidationError,
    Optional, NumberRange
)
from flask_wtf.file import FileAllowed
from datetime import datetime
from flask_login import current_user

# استيراد النماذج من models.py لاستخدامها في التحقق
from models import User, Subject, LiveSession, Class

### -------- نماذج تسجيل الدخول والتسجيل -------- ###

class LoginForm(FlaskForm):
    """نموذج تسجيل دخول المستخدمين."""
    email = StringField('البريد الإلكتروني', validators=[DataRequired(message='حقل البريد الإلكتروني مطلوب'), Email(message='صيغة البريد الإلكتروني غير صحيحة')])
    password = PasswordField('كلمة المرور', validators=[DataRequired(message='حقل كلمة المرور مطلوب')])
    submit = SubmitField('تسجيل الدخول')


class RegistrationForm(FlaskForm):
    """نموذج تسجيل مستخدم جديد (يستخدمه المدير)."""
    username = StringField('اسم المستخدم', validators=[DataRequired(message='حقل اسم المستخدم مطلوب'), Length(min=3, max=50, message='يجب أن يكون اسم المستخدم بين 3 و 50 حرف')])
    email = StringField('البريد الإلكتروني', validators=[DataRequired(message='حقل البريد الإلكتروني مطلوب'), Email(message='صيغة البريد الإلكتروني غير صحيحة')])
    role = SelectField('الدور', choices=[('student', 'طالب'), ('teacher', 'معلم')], validators=[DataRequired(message='حقل الدور مطلوب')])
    password = PasswordField('كلمة المرور', validators=[DataRequired(message='حقل كلمة المرور مطلوب'), Length(min=6, message='يجب أن تكون كلمة المرور 6 أحرف على الأقل')])
    confirm_password = PasswordField(
        'تأكيد كلمة المرور',
        validators=[DataRequired(message='حقل تأكيد كلمة المرور مطلوب'), EqualTo('password', message='كلمتا المرور غير متطابقتين')]
    )
    submit = SubmitField('تسجيل المستخدم')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('اسم المستخدم هذا موجود بالفعل. يرجى اختيار اسم مختلف.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('عنوان البريد الإلكتروني هذا موجود بالفعل. يرجى اختيار بريد مختلف.')
class StudentRegistrationForm(FlaskForm):
    """نموذج تسجيل طالب جديد."""
    username = StringField('اسم المستخدم', validators=[DataRequired(), Length(min=3, max=50)])
    email = StringField('البريد الإلكتروني', validators=[DataRequired(), Email()])
    password = PasswordField('كلمة المرور', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('تأكيد كلمة المرور', validators=[DataRequired(), EqualTo('password')])
    class_id = SelectField('الصف الدراسي', coerce=int, validators=[DataRequired()])
    submit = SubmitField('تسجيل الطالب')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # تحديث الاستعلام للحصول على الصفوف
        self.class_id.choices = [(c.id, c.name) for c in Class.query.order_by(Class.name).all()]

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('اسم المستخدم هذا موجود بالفعل.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('عنوان البريد الإلكتروني هذا موجود بالفعل.')

class TeacherRegistrationForm(FlaskForm):
    """نموذج تسجيل معلم جديد."""
    username = StringField('اسم المستخدم', validators=[DataRequired(), Length(min=3, max=50)])
    email = StringField('البريد الإلكتروني', validators=[DataRequired(), Email()])
    password = PasswordField('كلمة المرور', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('تأكيد كلمة المرور', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('تسجيل المعلم')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('اسم المستخدم هذا موجود بالفعل.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('عنوان البريد الإلكتروني هذا موجود بالفعل.')

### -------- نماذج إدارة المواد الدراسية -------- ###
class SubjectForm(FlaskForm):
    """نموذج إضافة مادة دراسية جديدة."""
    name = StringField('اسم المادة', validators=[DataRequired(message='حقل اسم المادة مطلوب'), Length(min=3, max=100, message='يجب أن يكون اسم المادة بين 3 و 100 حرف')])
    description = TextAreaField('وصف المادة', validators=[Optional()])
    class_id = SelectField('الصف الدراسي', coerce=int, validators=[DataRequired(message='حقل الصف الدراسي مطلوب')])
    submit = SubmitField('إضافة المادة')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.class_id.choices = [(c.id, c.name) for c in Class.query.order_by(Class.name).all()]

    def validate_name(self, name):
        subject = Subject.query.filter_by(name=name.data).first()
        if subject:
            raise ValidationError('هذه المادة موجودة بالفعل.')

### -------- نماذج الاختبارات -------- ###

class ExamForm(FlaskForm):
    """نموذج إنشاء اختبار جديد."""
    title = StringField('عنوان الاختبار', validators=[DataRequired(message='حقل العنوان مطلوب'), Length(min=5, max=200, message='يجب أن يكون العنوان بين 5 و 200 حرف')])
    description = TextAreaField('وصف الاختبار', validators=[Optional()])
    subject = SelectField('المادة', coerce=int, validators=[DataRequired(message='حقل المادة مطلوب')])
    class_id = SelectField('الصف الدراسي', coerce=int, validators=[DataRequired(message='حقل الصف الدراسي مطلوب')])
    start_time = DateTimeField('وقت البدء (YYYY-MM-DD HH:MM)', format='%Y-%m-%d %H:%M', validators=[DataRequired(message='حقل وقت البدء مطلوب')])
    end_time = DateTimeField('وقت الانتهاء (YYYY-MM-DD HH:MM)', format='%Y-%m-%d %H:%M', validators=[DataRequired(message='حقل وقت الانتهاء مطلوب')])
    is_active = BooleanField('نشط (يظهر للطلاب)')
    submit = SubmitField('إنشاء الاختبار')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.subject.choices = [(s.id, s.name) for s in Subject.query.all()]
        self.class_id.choices = [(c.id, c.name) for c in Class.query.order_by(Class.name).all()]

    def validate_end_time(self, field):
        if field.data and self.start_time.data and field.data <= self.start_time.data:
            raise ValidationError('وقت الانتهاء يجب أن يكون بعد وقت البدء.')

    def validate_start_time(self, field):
        if field.data and field.data < datetime.utcnow():
            raise ValidationError('وقت البدء يجب ألا يكون في الماضي.')

### -------- نماذج الأسئلة -------- ###

class QuestionForm(FlaskForm):
    """نموذج لإضافة سؤال جديد."""
    question_type = SelectField('نوع السؤال', choices=[
        ('multiple_choice', 'اختيار من متعدد'),
        ('short_answer', 'إجابة قصيرة'),
        ('true_false', 'صح أو خطأ')
    ], validators=[DataRequired(message='حقل نوع السؤال مطلوب')])
    text = TextAreaField('نص السؤال', validators=[DataRequired(message='حقل نص السؤال مطلوب')])
    correct_answer = StringField('الإجابة الصحيحة (للأسئلة القصيرة وصح/خطأ)', validators=[Optional()])
    points = FloatField('النقاط', default=1.0, validators=[DataRequired(message='حقل النقاط مطلوب'), NumberRange(min=0.1, message="النقاط يجب أن تكون أكبر من 0.")])

    # خيارات سؤال الاختيار من متعدد
    choice1 = StringField('الخيار 1', validators=[Optional()])
    is_correct1 = BooleanField('صحيح', false_values=(False, 'false', '0', ''))
    choice2 = StringField('الخيار 2', validators=[Optional()])
    is_correct2 = BooleanField('صحيح', false_values=(False, 'false', '0', ''))
    choice3 = StringField('الخيار 3', validators=[Optional()])
    is_correct3 = BooleanField('صحيح', false_values=(False, 'false', '0', ''))
    choice4 = StringField('الخيار 4', validators=[Optional()])
    is_correct4 = BooleanField('صحيح', false_values=(False, 'false', '0', ''))

    submit = SubmitField('إضافة السؤال')

    def validate(self):
        # إصلاح: تجاوز التحقق مؤقتاً للتصحيح
        return super().validate()

class ChoiceForm(FlaskForm):
    """نموذج لإضافة أو تعديل خيار لسؤال اختيار من متعدد."""
    text = StringField('نص الخيار', validators=[DataRequired(message='حقل نص الخيار مطلوب')])
    is_correct = BooleanField('صحيح')
    submit = SubmitField('حفظ الخيار')

### -------- نماذج الواجبات والمهام -------- ###

class AssignmentForm(FlaskForm):
    """نموذج إنشاء واجب جديد."""
    title = StringField('عنوان الواجب', validators=[DataRequired(message='حقل العنوان مطلوب'), Length(min=5, max=200, message='يجب أن يكون العنوان بين 5 و 200 حرف')])
    description = TextAreaField('وصف الواجب', validators=[Optional()])
    subject = SelectField('المادة', coerce=int, validators=[DataRequired(message='حقل المادة مطلوب')])
    class_id = SelectField('الصف الدراسي', coerce=int, validators=[DataRequired(message='حقل الصف الدراسي مطلوب')])
    due_date = DateTimeField('تاريخ الاستحقاق (YYYY-MM-DD HH:MM)', format='%Y-%m-%d %H:%M', validators=[DataRequired(message='حقل تاريخ الاستحقاق مطلوب')])
    submit = SubmitField('إنشاء الواجب')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.subject.choices = [(s.id, s.name) for s in Subject.query.all()]
        self.class_id.choices = [(c.id, c.name) for c in Class.query.order_by(Class.name).all()]

    def validate_due_date(self, field):
        if field.data and field.data <= datetime.utcnow():
            raise ValidationError('تاريخ الاستحقاق يجب أن يكون في المستقبل.')

class AssignmentTaskForm(FlaskForm):
    """نموذج إضافة مهمة إلى واجب معين."""
    task_type = SelectField('نوع المهمة', choices=[
        ('short_answer', 'إجابة نصية قصيرة'),
        ('file_upload', 'رفع ملف')
    ], validators=[DataRequired(message='حقل نوع المهمة مطلوب')])
    instructions = TextAreaField('تعليمات المهمة', validators=[DataRequired(message='حقل التعليمات مطلوب')])
    submit = SubmitField('إضافة المهمة')

### -------- نماذج رفع الواجبات والتقييم -------- ###

class SubmissionForm(FlaskForm):
    """نموذج لتقديم إجابة على مهمة واجب."""
    answer_text = TextAreaField('إجابتك النصية (إذا كانت المهمة تتطلب إجابة نصية)', validators=[Optional()])
    file = FileField('ملف الواجب (إذا كانت المهمة تتطلب رفع ملف)', validators=[
        Optional(),
        FileAllowed(['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png', 'zip'],
                    'أنواع الملفات المسموح بها: PDF, DOC, DOCX, JPG, JPEG, PNG, ZIP')
    ])
    submit = SubmitField('تقديم الواجب')

class GradingForm(FlaskForm):
    """نموذج تقييم تقديم واجب."""
    grade = FloatField('الدرجة (من 0 إلى 100)', validators=[DataRequired(message='حقل الدرجة مطلوب'), NumberRange(min=0, max=100, message="الدرجة يجب أن تكون بين 0 و 100.")])
    feedback = TextAreaField('ملاحظات المدرس', validators=[Optional()])
    submit = SubmitField('حفظ التقييم')

### -------- نموذج البث المباشر -------- ###

class LiveSessionForm(FlaskForm):
    """نموذج إنشاء جلسة بث مباشر."""
    title = StringField('عنوان الجلسة', validators=[
        DataRequired(message='حقل العنوان مطلوب'),
        Length(min=5, max=200, message='يجب أن يكون العنوان بين 5 و 200 حرف')
    ])
    description = TextAreaField('وصف الجلسة (اختياري)', validators=[
        Optional(),
        Length(max=500, message='يجب ألا يتجاوز الوصف 500 حرف')
    ])
    stream_url = StringField('رابط البث المباشر', validators=[Optional()])
    
    subject_id = SelectField('المادة الدراسية', coerce=int, validators=[DataRequired(message='حقل المادة مطلوب')])
    
    is_private = BooleanField('جلسة خاصة', default=False)
    password = PasswordField('كلمة المرور (إذا كانت الجلسة خاصة)', validators=[
        Optional(),
        Length(min=4, max=20, message='يجب أن تكون كلمة المرور بين 4 و 20 حرف')
    ])
    submit = SubmitField('بدء الجلسة')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.subject_id.choices = [(s.id, s.name) for s in Subject.query.all()]

    def validate_title(self, title):
        """التحقق من عدم وجود جلسة بنفس الاسم نشطة حالياً."""
        active_session = LiveSession.query.filter_by(
            title=title.data,
            teacher_id=current_user.id,
            is_active=True
        ).first()
        if active_session:
            raise ValidationError('لديك بالفعل جلسة نشطة بنفس الاسم. يرجى اختيار عنوان آخر أو إنهاء الجلسة الحالية.')

    def validate_password(self, password):
        if self.is_private.data and not password.data:
            raise ValidationError('يجب إدخال كلمة مرور للجلسات الخاصة.')

class ClassForm(FlaskForm):
    """نموذج إضافة صف دراسي جديد."""
    name = StringField('اسم الصف', validators=[DataRequired(message='حقل اسم الصف مطلوب'), Length(min=3, max=100)])
    description = TextAreaField('وصف الصف', validators=[Optional()])
    submit = SubmitField('إضافة الصف')

    def validate_name(self, name):
        class_ = Class.query.filter_by(name=name.data).first()
        if class_:
            raise ValidationError('هذا الصف موجود بالفعل.')