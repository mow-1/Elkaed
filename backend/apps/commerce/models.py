from decimal import Decimal
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.timezone import now


class Order(models.Model):
    STATUSES = [
        ('pending', 'قيد الانتظار'),
        ('completed', 'مكتمل'),
        ('cancelled', 'ملغي'),
        ('refunded', 'مسترد'),
        ('failed', 'فشل'),
    ]
    PAYMENT_METHODS = [('kanga_pay', 'كانجا باي'), ('wallet', 'محفظة')]

    user           = models.ForeignKey('users.User', on_delete=models.PROTECT)
    status         = models.CharField(choices=STATUSES, max_length=15, default='pending')
    payment_method = models.CharField(choices=PAYMENT_METHODS, max_length=15)
    transaction_id = models.CharField(max_length=255, blank=True)
    total_price    = models.DecimalField(max_digits=10, decimal_places=2)
    coupon_code    = models.CharField(max_length=50, blank=True)
    coupon_amount  = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'))
    created_at     = models.DateTimeField(auto_now_add=True)
    wp_order_id    = models.IntegerField(null=True, unique=True, db_index=True)

    class Meta:
        verbose_name = 'طلب'
        verbose_name_plural = 'الطلبات'

    def __str__(self):
        return f'Order #{self.pk} — {self.user} ({self.status})'


class OrderItem(models.Model):
    order  = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    course = models.ForeignKey('courses.Course', on_delete=models.PROTECT)
    price  = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = 'عنصر طلب'


class Coupon(models.Model):
    TYPES = [('wallet_recharge', 'شحن محفظة'), ('course_discount', 'خصم كورس')]

    code         = models.CharField(max_length=50, unique=True)
    coupon_type  = models.CharField(choices=TYPES, max_length=20, default='wallet_recharge')
    amount       = models.DecimalField(max_digits=10, decimal_places=2)
    usage_limit  = models.PositiveIntegerField(default=1)
    usage_count  = models.PositiveIntegerField(default=0)
    expires_at   = models.DateTimeField(null=True, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)
    created_by   = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True)
    is_active    = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'كوبون'
        verbose_name_plural = 'الكوبونات'

    def __str__(self):
        return self.code

    def is_valid(self):
        if not self.is_active:
            return False
        if self.usage_count >= self.usage_limit:
            return False
        if self.expires_at and self.expires_at < now():
            return False
        return True


class CouponRedemption(models.Model):
    user        = models.ForeignKey('users.User', on_delete=models.CASCADE)
    coupon      = models.ForeignKey(Coupon, on_delete=models.CASCADE)
    amount      = models.DecimalField(max_digits=10, decimal_places=2)
    redeemed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('user', 'coupon')]
        verbose_name = 'استخدام كوبون'


class WalletTransaction(models.Model):
    TYPES = [('credit', 'إيداع'), ('debit', 'خصم')]
    REASON_CODES = [
        ('purchase', 'شراء كورس'),
        ('refund', 'استرداد'),
        ('csv_import', 'استيراد CSV'),
        ('attendance_present', 'حضور حصة'),
        ('attendance_absent', 'غياب عن حصة'),
        ('discount_adjustment', 'تعديل خصم'),
        ('package_credit', 'إيداع باقة'),
        ('admin_credit', 'إيداع إداري'),
        ('admin_debit', 'خصم إداري'),
        ('coupon', 'كوبون'),
        ('kanga_topup', 'شحن كانجا باي'),
        ('reversal', 'عكس معاملة'),
        ('bundle', 'شراء باقة كورسات'),
    ]

    user          = models.ForeignKey('users.User', related_name='wallet_transactions', on_delete=models.CASCADE)
    amount        = models.DecimalField(max_digits=10, decimal_places=2)
    type          = models.CharField(choices=TYPES, max_length=6)
    balance_after = models.DecimalField(max_digits=10, decimal_places=2)
    reference     = models.CharField(max_length=100)
    note          = models.CharField(max_length=255, blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)

    reason_code     = models.CharField(choices=REASON_CODES, max_length=30, blank=True)
    content_type    = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True, blank=True)
    object_id       = models.PositiveIntegerField(null=True, blank=True)
    related_object  = GenericForeignKey('content_type', 'object_id')
    created_by      = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, blank=True,
                                         related_name='wallet_txns_created')
    original_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    discount        = models.ForeignKey('attendance.StudentDiscount', on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'معاملة محفظة'
        verbose_name_plural = 'معاملات المحفظة'

    def __str__(self):
        return f'{self.type} {self.amount} EGP — {self.user}'


class FlashSale(models.Model):
    course       = models.ForeignKey('courses.Course', on_delete=models.CASCADE, related_name='flash_sales')
    discount_pct = models.DecimalField(max_digits=5, decimal_places=2, help_text='نسبة الخصم 0-100')
    starts_at    = models.DateTimeField()
    ends_at      = models.DateTimeField()
    is_active    = models.BooleanField(default=True)
    created_by   = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True)

    class Meta:
        verbose_name = 'عرض مؤقت'
        verbose_name_plural = 'العروض المؤقتة'
        indexes = [models.Index(fields=['course', 'starts_at', 'ends_at'])]

    def __str__(self):
        return f'{self.course.title} — {self.discount_pct}%'

    def effective_price(self):
        discount = self.course.price * (self.discount_pct / Decimal('100'))
        return (self.course.price - discount).quantize(Decimal('0.01'))


class Bundle(models.Model):
    title      = models.CharField(max_length=300)
    title_en   = models.CharField(max_length=300, blank=True)
    courses    = models.ManyToManyField('courses.Course', related_name='bundles')
    price      = models.DecimalField(max_digits=10, decimal_places=2)
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True)

    class Meta:
        verbose_name = 'باقة'
        verbose_name_plural = 'الباقات'

    def __str__(self):
        return self.title


from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender=Order)
def order_status_changed(sender, instance, created, **kwargs):
    """Send WhatsApp when order status changes to completed or cancelled."""
    if created:
        return
    if instance.status not in ('completed', 'cancelled'):
        return
    # Check notification preference
    from apps.notifications.models import user_wants
    if not user_wants(instance.user, 'order_status'):
        return
    from apps.notifications.tasks import send_whatsapp_task
    status_ar = dict(Order.STATUSES).get(instance.status, instance.status)
    msg = f'طلبك #{instance.pk} — الحالة: {status_ar}'
    send_whatsapp_task.delay(instance.user.phone, msg)
    if instance.user.email:
        from django.core.mail import send_mail
        send_mail(
            subject=f'تحديث حالة طلبك #{instance.pk} — القائد',
            message=msg,
            from_email=None,
            recipient_list=[instance.user.email],
            fail_silently=True,
        )
