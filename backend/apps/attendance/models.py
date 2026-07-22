from decimal import Decimal
from django.db import models


class PricingSettings(models.Model):
    """Singleton — attendance/lesson pricing config, admin-editable."""
    single_lesson_price       = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('80'))
    monthly_package_price     = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('280'))
    package_lesson_count      = models.PositiveIntegerField(default=4)
    allow_negative_balance    = models.BooleanField(default=False)
    notify_guardian_on_absence = models.BooleanField(default=False)
    show_governorate_field    = models.BooleanField(default=True)
    show_school_field         = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'إعدادات التسعير'

    def __str__(self):
        return 'إعدادات التسعير'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class StudentDiscount(models.Model):
    TYPES = [
        ('percentage', 'نسبة مئوية'),
        ('fixed_amount', 'مبلغ ثابت'),
        ('free', 'مجاني'),
    ]
    SCOPES = [
        ('physical_only', 'حضوري فقط'),
        ('online_only', 'أونلاين فقط'),
        ('both', 'الاثنين'),
    ]

    student       = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='discounts')
    discount_type = models.CharField(choices=TYPES, max_length=15)
    value         = models.DecimalField(max_digits=10, decimal_places=2)
    scope         = models.CharField(choices=SCOPES, max_length=15)
    reason        = models.TextField()
    active        = models.BooleanField(default=True)
    starts_at     = models.DateTimeField(null=True, blank=True)
    ends_at       = models.DateTimeField(null=True, blank=True)
    created_by    = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, related_name='discounts_granted')
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'خصم طالب'
        verbose_name_plural = 'خصومات الطلاب'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.student} — {self.get_discount_type_display()} ({self.scope})'


class CenterGroup(models.Model):
    ACADEMIC_YEAR_CHOICES = [
        ('1st', 'الصف الأول الثانوي'),
        ('2nd', 'الصف الثاني الثانوي'),
        ('3rd', 'الصف الثالث الثانوي'),
    ]

    name_ar               = models.CharField(max_length=200)
    academic_year          = models.CharField(choices=ACADEMIC_YEAR_CHOICES, max_length=5)
    schedule_description   = models.CharField(max_length=255, blank=True)
    lesson_price_override  = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    class Meta:
        verbose_name = 'مجموعة سنتر'
        verbose_name_plural = 'مجموعات السنتر'

    def __str__(self):
        return self.name_ar


class LessonPackage(models.Model):
    """A named, admin-defined price tier (e.g. "8 lessons — 400 EGP") a center student
    can be sold — deducts `price` from their wallet and credits `lesson_count` onto
    User.prepaid_lessons_remaining, which attendance marking consumes before falling
    back to a per-lesson wallet debit."""
    name         = models.CharField(max_length=100)
    lesson_count = models.PositiveIntegerField()
    price        = models.DecimalField(max_digits=10, decimal_places=2)
    is_active    = models.BooleanField(default=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'باقة حصص'
        verbose_name_plural = 'باقات الحصص'

    def __str__(self):
        return f'{self.name} ({self.lesson_count} حصة — {self.price} ج)'


class PhysicalSession(models.Model):
    group         = models.ForeignKey(CenterGroup, related_name='sessions', on_delete=models.CASCADE)
    date          = models.DateField()
    title_ar      = models.CharField(max_length=200)
    linked_lesson = models.ForeignKey('courses.Lesson', null=True, blank=True, on_delete=models.SET_NULL)
    lesson_price  = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ['-date']
        verbose_name = 'حصة حضورية'
        verbose_name_plural = 'الحصص الحضورية'

    def save(self, *args, **kwargs):
        if self.lesson_price is None:
            self.lesson_price = self.group.lesson_price_override or PricingSettings.get_solo().single_lesson_price
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.group.name_ar} — {self.title_ar} ({self.date})'


class AttendanceRecord(models.Model):
    STATUS_CHOICES = [
        ('present', 'حاضر'),
        ('absent', 'غائب'),
        ('absent_excused', 'غائب بعذر'),
        ('makeup', 'تعويض'),
    ]

    session        = models.ForeignKey(PhysicalSession, related_name='attendance_records', on_delete=models.CASCADE)
    student        = models.ForeignKey('users.User', on_delete=models.CASCADE)
    status         = models.CharField(choices=STATUS_CHOICES, max_length=15)
    deducted       = models.BooleanField(default=False)
    paid_via_package = models.BooleanField(default=False)
    whatsapp_sent  = models.BooleanField(default=False)
    overridden_by  = models.ForeignKey('users.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    notes          = models.TextField(blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [('session', 'student')]
        verbose_name = 'سجل حضور'
        verbose_name_plural = 'سجلات الحضور'

    def __str__(self):
        return f'{self.student} — {self.session} — {self.get_status_display()}'
