from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class AuditLog(models.Model):
    ACTIONS = [
        ('created', 'إنشاء'),
        ('updated', 'تعديل'),
        ('deleted', 'حذف'),
        ('overridden', 'تجاوز'),
        ('refunded', 'استرداد'),
        ('discount_granted', 'منح خصم'),
        ('discount_revoked', 'سحب خصم'),
        ('attendance_changed', 'تعديل حضور'),
        ('csv_imported', 'استيراد CSV'),
        ('access_granted', 'منح صلاحية'),
        ('access_revoked', 'سحب صلاحية'),
        ('debited', 'خصم من المحفظة'),
        ('credited', 'إيداع في المحفظة'),
    ]

    actor        = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs')
    action       = models.CharField(choices=ACTIONS, max_length=30)
    content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True, blank=True)
    object_id    = models.PositiveIntegerField(null=True, blank=True)
    target       = GenericForeignKey('content_type', 'object_id')
    before       = models.JSONField(default=dict, blank=True)
    after        = models.JSONField(default=dict, blank=True)
    note         = models.TextField(blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['actor', 'action', 'created_at'])]
        verbose_name = 'سجل عملية'
        verbose_name_plural = 'سجل العمليات'

    def __str__(self):
        return f'{self.get_action_display()} — {self.actor} ({self.created_at:%Y-%m-%d %H:%M})'

    def delete(self, *args, **kwargs):
        # append-only ledger: never delete
        raise NotImplementedError('AuditLog is append-only and cannot be deleted.')
