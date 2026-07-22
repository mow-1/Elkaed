from decimal import Decimal
from django.db import models


class Quiz(models.Model):
    topic             = models.ForeignKey('courses.Topic', on_delete=models.CASCADE)
    title             = models.CharField(max_length=300)
    title_en          = models.CharField(max_length=300, blank=True)
    order             = models.PositiveIntegerField(default=0)
    time_limit        = models.PositiveIntegerField(null=True, blank=True, help_text='بالدقائق')
    pass_mark         = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0'))
    attempts_allowed  = models.PositiveIntegerField(default=0)
    is_locked         = models.BooleanField(default=False)
    hide_results      = models.BooleanField(default=False)
    shuffle_questions = models.BooleanField(default=False)
    shuffle_answers   = models.BooleanField(default=False)
    wp_post_id        = models.IntegerField(null=True, unique=True, db_index=True)

    class Meta:
        verbose_name = 'اختبار'
        verbose_name_plural = 'الاختبارات'

    def __str__(self):
        return self.title


class Question(models.Model):
    TYPES = [
        ('mcq', 'اختيار متعدد'),
        ('tf', 'صح أو خطأ'),
        ('fill', 'اكمل الفراغ'),
        ('open', 'سؤال مقالي'),
        ('ordering', 'ترتيب'),
    ]

    quiz           = models.ForeignKey(Quiz, related_name='questions', on_delete=models.CASCADE)
    text           = models.TextField()
    text_en        = models.TextField(blank=True)
    question_type  = models.CharField(choices=TYPES, max_length=10)
    mark           = models.DecimalField(max_digits=8, decimal_places=2)
    order          = models.PositiveIntegerField()
    explanation    = models.TextField(blank=True)
    explanation_en = models.TextField(blank=True)
    image          = models.ImageField(upload_to='quiz/questions/', null=True, blank=True)
    wp_question_id = models.IntegerField(null=True, db_index=True)

    class Meta:
        ordering = ['order']
        verbose_name = 'سؤال'


class AnswerChoice(models.Model):
    question     = models.ForeignKey(Question, related_name='choices', on_delete=models.CASCADE)
    text         = models.TextField()
    text_en      = models.TextField(blank=True)
    is_correct   = models.BooleanField(default=False)
    order        = models.PositiveIntegerField()
    image        = models.ImageField(upload_to='quiz/answers/', null=True, blank=True)
    wp_answer_id = models.IntegerField(null=True, db_index=True)

    class Meta:
        ordering = ['order']
        verbose_name = 'إجابة'


class QuizAttempt(models.Model):
    STATUS = [
        ('in_progress', 'جاري'),
        ('submitted', 'مكتمل'),
        ('timed_out', 'انتهى الوقت'),
    ]
    RESULT = [('pass', 'ناجح'), ('fail', 'راسب')]

    student       = models.ForeignKey('users.User', on_delete=models.CASCADE)
    quiz          = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    course        = models.ForeignKey('courses.Course', on_delete=models.CASCADE)
    total_marks   = models.DecimalField(max_digits=9, decimal_places=2)
    earned_marks  = models.DecimalField(max_digits=9, decimal_places=2, default=Decimal('0'))
    status        = models.CharField(choices=STATUS, max_length=15, default='in_progress')
    result        = models.CharField(choices=RESULT, max_length=5, null=True, blank=True)
    started_at    = models.DateTimeField(auto_now_add=True)
    ended_at      = models.DateTimeField(null=True, blank=True)
    is_reviewed   = models.BooleanField(default=False)
    wp_attempt_id = models.IntegerField(null=True, unique=True, db_index=True)

    class Meta:
        indexes = [models.Index(fields=['student', 'quiz', 'status'])]
        verbose_name = 'محاولة اختبار'

    def __str__(self):
        return f'{self.student} — {self.quiz} ({self.status})'


class AttemptAnswer(models.Model):
    attempt        = models.ForeignKey(QuizAttempt, related_name='answers', on_delete=models.CASCADE)
    question       = models.ForeignKey(Question, on_delete=models.CASCADE)
    given_answer   = models.TextField()
    is_correct     = models.BooleanField(null=True)
    marks_achieved = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0'))
    wp_answer_id   = models.IntegerField(null=True, db_index=True)

    class Meta:
        verbose_name = 'إجابة محاولة'
