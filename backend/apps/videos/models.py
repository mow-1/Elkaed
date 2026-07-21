import uuid
from django.db import models
from django.utils.timezone import now


class Video(models.Model):
    STATUS = [
        ('uploading', 'جاري الرفع'),
        ('processing', 'جاري المعالجة'),
        ('ready', 'جاهز'),
        ('failed', 'فشل'),
    ]

    title            = models.CharField(max_length=300)
    uploaded_by      = models.ForeignKey('users.User', on_delete=models.PROTECT)
    original_path    = models.CharField(max_length=500)
    hls_path         = models.CharField(max_length=500, blank=True)
    aes_key          = models.BinaryField(max_length=16)
    aes_key_id       = models.CharField(max_length=50)
    duration_seconds = models.PositiveIntegerField(default=0)
    file_size_bytes  = models.BigIntegerField(default=0)
    status           = models.CharField(choices=STATUS, max_length=15, default='uploading')
    created_at       = models.DateTimeField(auto_now_add=True)
    thumbnails       = models.JSONField(default=list)

    class Meta:
        verbose_name = 'فيديو'
        verbose_name_plural = 'الفيديوهات'

    def __str__(self):
        return f'{self.title} ({self.status})'


class VideoAccessToken(models.Model):
    """Short-lived token granting one user access to one video for 20 minutes."""
    token      = models.UUIDField(default=uuid.uuid4, unique=True)
    user       = models.ForeignKey('users.User', on_delete=models.CASCADE)
    video      = models.ForeignKey(Video, on_delete=models.CASCADE)
    lesson     = models.ForeignKey('courses.Lesson', on_delete=models.CASCADE)
    issued_at  = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    ip_address = models.GenericIPAddressField()
    used       = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'رمز وصول فيديو'

    def is_valid(self, ip):
        return not self.used and self.expires_at > now() and self.ip_address == ip


class VideoAccessLog(models.Model):
    user          = models.ForeignKey('users.User', on_delete=models.CASCADE)
    lesson        = models.ForeignKey('courses.Lesson', on_delete=models.CASCADE)
    ip_address    = models.GenericIPAddressField()
    user_agent    = models.CharField(max_length=500)
    timestamp     = models.DateTimeField(auto_now_add=True)
    token_issued  = models.BooleanField(default=True)
    denial_reason = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name = 'سجل وصول فيديو'
