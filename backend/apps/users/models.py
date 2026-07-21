import secrets
from decimal import Decimal
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils.timezone import now
from .managers import UserManager


class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ('student', 'طالب'),
        ('instructor', 'مدرس'),
        ('admin', 'مدير'),
        ('staff', 'موظف'),
        ('assistant', 'مساعد'),
    ]
    STUDENT_TYPE_CHOICES = [
        ('center', 'سنتر'),
        ('online', 'أونلاين'),
    ]
    ACADEMIC_YEAR_CHOICES = [
        ('1st', 'الصف الأول الثانوي'),
        ('2nd', 'الصف الثاني الثانوي'),
        ('3rd', 'الصف الثالث الثانوي'),
    ]

    phone          = models.CharField(max_length=15, unique=True)
    first_name     = models.CharField(max_length=100)
    last_name      = models.CharField(max_length=100)
    guardian_phone = models.CharField(max_length=15, blank=True)
    email          = models.EmailField(blank=True)
    student_type   = models.CharField(choices=STUDENT_TYPE_CHOICES, max_length=10, blank=True)
    academic_year  = models.CharField(choices=ACADEMIC_YEAR_CHOICES, max_length=5, blank=True)
    wallet_balance = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    role           = models.CharField(choices=ROLE_CHOICES, max_length=15, default='student')
    is_active      = models.BooleanField(default=True)
    is_staff       = models.BooleanField(default=False)
    must_change_password = models.BooleanField(default=False)
    date_joined    = models.DateTimeField(default=now)
    wp_user_id     = models.IntegerField(null=True, unique=True, db_index=True)
    group          = models.ForeignKey('attendance.CenterGroup', null=True, blank=True,
                                        on_delete=models.SET_NULL, related_name='students')
    attendance_token = models.CharField(max_length=16, unique=True, null=True, blank=True, db_index=True)

    USERNAME_FIELD  = 'phone'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    objects = UserManager()

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'

    def __str__(self):
        return f'{self.full_name} ({self.phone})'


@receiver(pre_save, sender=User)
def assign_attendance_token(sender, instance, **kwargs):
    """Every user (self-registered or CSV-imported) gets an opaque QR identity —
    never the phone/user id, so a lost card can't be used to guess either.
    # ponytail: no collision retry — 8 random url-safe bytes is far too large
    # a space to realistically collide; add a retry loop if this ever fires."""
    if not instance.attendance_token:
        instance.attendance_token = secrets.token_urlsafe(8)


class PhoneOTP(models.Model):
    PURPOSE_CHOICES = [
        ('register', 'تسجيل'),
        ('login', 'دخول'),
        ('reset', 'استعادة كلمة المرور'),
    ]

    phone      = models.CharField(max_length=15)
    code       = models.CharField(max_length=6)
    purpose    = models.CharField(choices=PURPOSE_CHOICES, max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used       = models.BooleanField(default=False)
    attempts   = models.PositiveSmallIntegerField(default=0)

    class Meta:
        indexes = [models.Index(fields=['phone', 'purpose', 'used'])]

    def is_valid(self):
        return not self.used and self.attempts < 3 and self.expires_at > now()


class ShippingAddress(models.Model):
    GOVERNORATES = [
        ('القاهرة','القاهرة'),('الجيزة','الجيزة'),('الإسكندرية','الإسكندرية'),
        ('الدقهلية','الدقهلية'),('البحيرة','البحيرة'),('الشرقية','الشرقية'),
        ('المنوفية','المنوفية'),('الغربية','الغربية'),('القليوبية','القليوبية'),
        ('أخرى','أخرى'),
    ]
    user        = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    label       = models.CharField(max_length=50, default='المنزل')
    governorate = models.CharField(max_length=50, choices=GOVERNORATES)
    city        = models.CharField(max_length=100)
    street      = models.TextField()
    is_default  = models.BooleanField(default=False)

    class Meta:
        ordering = ['-is_default', 'label']
        verbose_name = 'عنوان'
        verbose_name_plural = 'العناوين'

    def __str__(self):
        return f'{self.user.phone} — {self.label}'


class ImportBatch(models.Model):
    STATUS_CHOICES = [
        ('pending', 'قيد الانتظار'),
        ('processing', 'قيد المعالجة'),
        ('done', 'مكتمل'),
        ('failed', 'فشل'),
    ]

    file           = models.FileField(upload_to='imports/csv/')
    uploaded_by    = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='import_batches')
    status         = models.CharField(choices=STATUS_CHOICES, max_length=10, default='pending')
    total_rows     = models.PositiveIntegerField(default=0)
    imported_count = models.PositiveIntegerField(default=0)
    failed_count   = models.PositiveIntegerField(default=0)
    row_results    = models.JSONField(default=list)
    created_at     = models.DateTimeField(auto_now_add=True)
    completed_at   = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'دفعة استيراد'
        verbose_name_plural = 'دفعات الاستيراد'

    def __str__(self):
        return f'دفعة استيراد #{self.pk} ({self.status})'
