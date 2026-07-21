from django.db import models


class HomepageBanner(models.Model):
    image      = models.ImageField(upload_to='banners/')
    title_ar   = models.CharField(max_length=200)
    title_en   = models.CharField(max_length=200, blank=True)
    link_url   = models.URLField(blank=True)
    is_active  = models.BooleanField(default=True)
    order      = models.PositiveIntegerField(default=0)
    starts_at  = models.DateTimeField(null=True, blank=True)
    ends_at    = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['order']
        verbose_name = 'بانر'
        verbose_name_plural = 'البانرات'

    def __str__(self):
        return self.title_ar


class NotificationTemplate(models.Model):
    TRIGGERS = [
        ('quiz_result', 'نتيجة الاختبار'),
        ('enrollment_confirmed', 'تأكيد التسجيل'),
        ('low_wallet', 'رصيد منخفض'),
        ('payment_success', 'نجاح الدفع'),
        ('new_lesson', 'درس جديد'),
        ('otp', 'رمز التحقق'),
    ]

    trigger   = models.CharField(choices=TRIGGERS, max_length=30, unique=True)
    body_ar   = models.TextField()
    body_en   = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'قالب إشعار'
        verbose_name_plural = 'قوالب الإشعارات'

    def __str__(self):
        return self.get_trigger_display()


class Campaign(models.Model):
    STATUSES = [('draft', 'مسودة'), ('sending', 'جاري الإرسال'), ('done', 'مكتمل')]
    SEGMENTS = [
        ('all', 'الكل'),
        ('students', 'الطلاب فقط'),
        ('center', 'طلاب السنتر'),
        ('online', 'طلاب الأونلاين'),
        ('1st', 'الصف الأول'),
        ('2nd', 'الصف الثاني'),
        ('3rd', 'الصف الثالث'),
    ]

    title      = models.CharField(max_length=200)
    message    = models.TextField()
    segment    = models.CharField(choices=SEGMENTS, max_length=20, default='all')
    status     = models.CharField(choices=STATUSES, max_length=10, default='draft')
    created_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_count = models.PositiveIntegerField(default=0)
    sent_at    = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'حملة واتساب'
        verbose_name_plural = 'حملات واتساب'
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class NotificationPreference(models.Model):
    """User opt-in/out per notification type."""
    TYPES = [
        ('quiz_result',          'نتيجة الاختبار'),
        ('enrollment_confirmed', 'تأكيد التسجيل'),
        ('order_status',         'تغيير حالة الطلب'),
        ('campaign',             'رسائل تسويقية'),
    ]

    user        = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='notification_prefs')
    notif_type  = models.CharField(choices=TYPES, max_length=30)
    enabled     = models.BooleanField(default=True)

    class Meta:
        unique_together = [('user', 'notif_type')]
        verbose_name = 'تفضيل الإشعارات'
        verbose_name_plural = 'تفضيلات الإشعارات'

    def __str__(self):
        return f'{self.user.phone} — {self.notif_type} — {"مفعّل" if self.enabled else "معطّل"}'


def user_wants(user, notif_type: str) -> bool:
    """Returns True if user has not explicitly disabled this notification type."""
    pref = NotificationPreference.objects.filter(user=user, notif_type=notif_type).first()
    return pref.enabled if pref else True  # default = enabled


class EmailCampaign(models.Model):
    STATUSES = [('draft', 'مسودة'), ('sending', 'جاري الإرسال'), ('done', 'مكتمل')]
    SEGMENTS = Campaign.SEGMENTS  # reuse same segment choices

    subject    = models.CharField(max_length=200)
    body_html  = models.TextField()
    segment    = models.CharField(choices=SEGMENTS, max_length=20, default='all')
    status     = models.CharField(choices=STATUSES, max_length=10, default='draft')
    created_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_count = models.PositiveIntegerField(default=0)
    sent_at    = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'حملة إيميل'
        verbose_name_plural = 'حملات الإيميل'
        ordering = ['-created_at']

    def __str__(self):
        return self.subject


class LandingHero(models.Model):
    eyebrow       = models.CharField(max_length=200, default='منصة تعليم التاريخ للثانوية العامة')
    heading       = models.CharField(max_length=300, default='اتعلّم التاريخ مع القائد..')
    heading_white = models.CharField(max_length=200, default='ومن أي مكان')
    para          = models.TextField(default='مع أ/ مصطفى عرفة — تجربة تعليمية مرنة وسهلة الوصول.')
    cta1_text     = models.CharField(max_length=100, default='تصفح الكورسات')
    cta1_link     = models.CharField(max_length=200, default='#courses')
    cta2_text     = models.CharField(max_length=100, default='حسابي', blank=True)
    cta2_link     = models.CharField(max_length=200, default='#register', blank=True)
    stat1_num     = models.CharField(max_length=20, default='+12,000')
    stat1_label   = models.CharField(max_length=100, default='طالب وطالبة')
    stat2_num     = models.CharField(max_length=20, default='+340')
    stat2_label   = models.CharField(max_length=100, default='حصة مسجلة')
    stat3_num     = models.CharField(max_length=20, default='%94')
    stat3_label   = models.CharField(max_length=100, default='نسبة نجاح +85')

    class Meta:
        verbose_name = 'هيرو الصفحة الرئيسية'

    def __str__(self):
        return 'هيرو الصفحة الرئيسية'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass


class LandingFeature(models.Model):
    glyph = models.CharField(max_length=10, default='𓉐')
    title = models.CharField(max_length=200)
    body  = models.TextField()
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['order']
        verbose_name = 'ميزة'
        verbose_name_plural = 'ميزات القائد'

    def __str__(self):
        return self.title


class LandingTestimonial(models.Model):
    author_name = models.CharField(max_length=100)
    grade       = models.CharField(max_length=100)
    text        = models.TextField()
    order       = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['order']
        verbose_name = 'شهادة طالب'
        verbose_name_plural = 'شهادات الطلاب'

    def __str__(self):
        return self.author_name


class LandingDarkBand(models.Model):
    heading  = models.CharField(max_length=300, default='طوّر مستواك، واتعلم التاريخ من أي مكان')
    body     = models.TextField(default='حصص مسجلة تقدر ترجعلها في أي وقت.')
    check1   = models.CharField(max_length=200, default='حصص مسجلة ترجعلها في أي وقت')
    check2   = models.CharField(max_length=200, default='مجموعات متابعة على التليجرام')
    check3   = models.CharField(max_length=200, default='مراجعات نهائية قبل الامتحان')
    check4   = models.CharField(max_length=200, default='بنك أسئلة بآلاف الأسئلة', blank=True)
    cta_text = models.CharField(max_length=100, default='شوف كل الكورسات')
    cta_link = models.CharField(max_length=200, default='#courses')

    class Meta:
        verbose_name = 'قسم الميزات الداكن'

    def __str__(self):
        return 'قسم الميزات الداكن'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass


class LandingCTA(models.Model):
    glyph    = models.CharField(max_length=10, default='𓂀')
    heading  = models.CharField(max_length=300, default='هتحس إنك قاعد في الفصل بالظبط!')
    body     = models.TextField(default='اعمل حسابك في دقيقة واحدة، واختار كورس صفّك، وابدأ أول حصة النهاردة.')
    cta_text = models.CharField(max_length=100, default='إنشاء حساب جديد')
    cta_link = models.CharField(max_length=200, default='/register')

    class Meta:
        verbose_name = 'قسم دعوة التسجيل'

    def __str__(self):
        return 'قسم دعوة التسجيل'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass
