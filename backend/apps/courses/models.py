from django.db import models
from django.db.models import F


class Category(models.Model):
    name          = models.CharField(max_length=200)
    name_en       = models.CharField(max_length=200, blank=True)
    slug          = models.SlugField(unique=True)
    student_type  = models.CharField(max_length=10, blank=True)
    academic_year = models.CharField(max_length=5, blank=True)
    parent        = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL)
    order         = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']
        verbose_name = 'فئة'
        verbose_name_plural = 'الفئات'

    def __str__(self):
        return self.name


class Course(models.Model):
    title         = models.CharField(max_length=300)
    title_en      = models.CharField(max_length=300, blank=True)
    slug          = models.SlugField(unique=True)
    description   = models.TextField()
    description_en = models.TextField(blank=True)
    instructor    = models.ForeignKey('users.User', related_name='courses', on_delete=models.PROTECT)
    category      = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    price         = models.DecimalField(max_digits=10, decimal_places=2)
    thumbnail     = models.ImageField(upload_to='courses/thumbnails/', blank=True)
    is_published  = models.BooleanField(default=False)
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)
    wp_post_id    = models.IntegerField(null=True, unique=True, db_index=True)
    max_students  = models.PositiveIntegerField(default=0)  # 0 = unlimited

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'كورس'
        verbose_name_plural = 'الكورسات'

    def __str__(self):
        return self.title


class Topic(models.Model):
    course     = models.ForeignKey(Course, related_name='topics', on_delete=models.CASCADE)
    title      = models.CharField(max_length=300)
    title_en   = models.CharField(max_length=300, blank=True)
    order      = models.PositiveIntegerField()
    wp_post_id = models.IntegerField(null=True, db_index=True)

    class Meta:
        ordering = ['order']
        verbose_name = 'موضوع'
        verbose_name_plural = 'الموضوعات'

    def __str__(self):
        return f'{self.course.title} — {self.title}'


class Lesson(models.Model):
    VIDEO_SOURCES = [('self_hosted', 'مستضاف ذاتياً'), ('youtube', 'يوتيوب')]

    topic            = models.ForeignKey(Topic, related_name='lessons', on_delete=models.CASCADE)
    title            = models.CharField(max_length=300)
    title_en         = models.CharField(max_length=300, blank=True)
    video            = models.ForeignKey('videos.Video', null=True, blank=True, on_delete=models.SET_NULL)
    video_source     = models.CharField(choices=VIDEO_SOURCES, max_length=15, default='self_hosted')
    youtube_id       = models.CharField(max_length=50, blank=True)
    order            = models.PositiveIntegerField()
    view_limit       = models.PositiveIntegerField(default=10)
    is_free_preview  = models.BooleanField(default=False)
    duration_seconds = models.PositiveIntegerField(default=0)
    wp_post_id       = models.IntegerField(null=True, db_index=True)

    class Meta:
        ordering = ['order']
        verbose_name = 'درس'
        verbose_name_plural = 'الدروس'

    def __str__(self):
        return self.title


class Enrollment(models.Model):
    STATUS_CHOICES = [
        ('active', 'نشط'),
        ('expired', 'منتهي'),
        ('cancelled', 'ملغي'),
    ]
    PAYMENT_METHOD_CHOICES = [
        ('kanga_pay', 'كانجا باي'),
        ('wallet', 'محفظة'),
        ('free', 'مجاني'),
        ('manual', 'يدوي'),
    ]

    student        = models.ForeignKey('users.User', related_name='enrollments', on_delete=models.PROTECT)
    course         = models.ForeignKey(Course, on_delete=models.PROTECT)
    status         = models.CharField(choices=STATUS_CHOICES, max_length=15, default='active')
    payment_method = models.CharField(choices=PAYMENT_METHOD_CHOICES, max_length=15)
    order          = models.ForeignKey('commerce.Order', null=True, blank=True, on_delete=models.SET_NULL)
    enrolled_at    = models.DateTimeField(auto_now_add=True)
    expires_at     = models.DateTimeField(null=True, blank=True)
    enrolled_by    = models.ForeignKey(
        'users.User', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='enrollments_created'
    )

    class Meta:
        unique_together = [('student', 'course')]
        verbose_name = 'اشتراك'
        verbose_name_plural = 'الاشتراكات'

    def __str__(self):
        return f'{self.student} → {self.course}'


class LessonProgress(models.Model):
    student               = models.ForeignKey('users.User', on_delete=models.CASCADE)
    lesson                = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    view_count            = models.PositiveIntegerField(default=0)
    last_position_seconds = models.PositiveIntegerField(default=0)
    completed             = models.BooleanField(default=False)
    last_watched          = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [('student', 'lesson')]
        verbose_name = 'تقدم الدرس'


class LessonAccessGrant(models.Model):
    """Lesson-scoped access grant (e.g. makeup video for an absence). Deliberately NOT an
    Enrollment — granting a full course Enrollment for one missed lesson would silently
    unlock every other paid lesson in that course."""
    VIA_CHOICES = [('absence', 'غياب'), ('manual', 'يدوي')]

    student     = models.ForeignKey('users.User', related_name='lesson_access_grants', on_delete=models.CASCADE)
    lesson      = models.ForeignKey(Lesson, related_name='access_grants', on_delete=models.CASCADE)
    granted_via = models.CharField(choices=VIA_CHOICES, max_length=10, default='manual')
    session     = models.ForeignKey('attendance.PhysicalSession', null=True, blank=True, on_delete=models.SET_NULL)
    granted_by  = models.ForeignKey('users.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    revoked     = models.BooleanField(default=False)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('student', 'lesson')]
        verbose_name = 'منح وصول لدرس'
        verbose_name_plural = 'منح الوصول للدروس'

    def __str__(self):
        return f'{self.student} → {self.lesson} ({self.granted_via})'


class LessonWatchlist(models.Model):
    """Student bookmarks a lesson to watch later."""
    user      = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='watchlist')
    lesson    = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='watchlisted_by')
    added_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('user', 'lesson')]
        verbose_name = 'مفضلة'
        verbose_name_plural = 'المفضلات'

    def __str__(self):
        return f'{self.user.phone} → {self.lesson.title}'


class Material(models.Model):
    """Downloadable file/PDF or a revision (video revisions link to a real Lesson with
    is_free_preview=True, so the existing HLS/4-view pipeline plays them unmodified —
    a flag on existing content, not a duplicate video pipeline)."""
    KIND_CHOICES = [('material', 'ملف'), ('revision', 'مراجعة')]
    STUDENT_TYPE_CHOICES = [('', 'الاثنين'), ('center', 'سنتر'), ('online', 'أونلاين')]

    title_ar     = models.CharField(max_length=300)
    title_en     = models.CharField(max_length=300, blank=True)
    kind         = models.CharField(choices=KIND_CHOICES, max_length=10, default='material')
    file         = models.FileField(upload_to='materials/', null=True, blank=True)
    lesson       = models.ForeignKey(Lesson, null=True, blank=True, on_delete=models.SET_NULL,
                                      related_name='materials')
    course       = models.ForeignKey(Course, null=True, blank=True, on_delete=models.SET_NULL,
                                      related_name='materials')
    academic_year = models.CharField(choices=[
        ('', 'كل السنوات'), ('1st', 'الصف الأول الثانوي'),
        ('2nd', 'الصف الثاني الثانوي'), ('3rd', 'الصف الثالث الثانوي'),
    ], max_length=5, blank=True)
    visibility_student_type = models.CharField(choices=STUDENT_TYPE_CHOICES, max_length=10, blank=True)
    uploaded_by  = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True)
    is_published = models.BooleanField(default=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'مادة تعليمية'
        verbose_name_plural = 'المواد التعليمية'

    def __str__(self):
        return self.title_ar


class Assignment(models.Model):
    """Homework — deliberately minimal: instructions + optional attachment,
    one student submission, no grading/rubric workflow."""
    topic        = models.ForeignKey(Topic, related_name='assignments', on_delete=models.CASCADE)
    title_ar     = models.CharField(max_length=300)
    title_en     = models.CharField(max_length=300, blank=True)
    instructions = models.TextField(blank=True)
    attachment   = models.FileField(upload_to='assignments/', null=True, blank=True)
    due_at       = models.DateTimeField(null=True, blank=True)
    order        = models.PositiveIntegerField(default=0)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order']
        verbose_name = 'واجب'
        verbose_name_plural = 'الواجبات'

    def __str__(self):
        return self.title_ar


class AssignmentSubmission(models.Model):
    assignment    = models.ForeignKey(Assignment, related_name='submissions', on_delete=models.CASCADE)
    student       = models.ForeignKey('users.User', on_delete=models.CASCADE)
    file          = models.FileField(upload_to='assignments/submissions/')
    submitted_at  = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [('assignment', 'student')]
        verbose_name = 'تسليم واجب'
        verbose_name_plural = 'تسليمات الواجبات'

    def __str__(self):
        return f'{self.student} — {self.assignment}'
