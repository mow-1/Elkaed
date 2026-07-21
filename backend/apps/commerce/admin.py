from django.contrib import admin
from apps.notifications.tasks import send_whatsapp_task
from .models import Order, OrderItem, Coupon, CouponRedemption, WalletTransaction


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display  = ('pk', 'user', 'status', 'payment_method', 'total_price', 'created_at')
    list_filter   = ('status', 'payment_method')
    search_fields = ('user__phone', 'transaction_id')
    inlines       = [OrderItemInline]
    actions       = ['notify_order_status']

    @admin.action(description='إرسال إشعار تغيير حالة الطلب واتساب')
    def notify_order_status(self, request, queryset):
        status_map = dict(Order.STATUSES)
        count = 0
        for order in queryset.select_related('user'):
            status_ar = status_map.get(order.status, order.status)
            msg = f'طلبك #{order.pk} — الحالة الحالية: {status_ar}'
            send_whatsapp_task.delay(order.user.phone, msg)
            count += 1
        self.message_user(request, f'تم إرسال {count} إشعار.')


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'coupon_type', 'amount', 'usage_count', 'usage_limit', 'is_active')
    list_filter  = ('coupon_type', 'is_active')
    search_fields = ('code',)


@admin.register(CouponRedemption)
class CouponRedemptionAdmin(admin.ModelAdmin):
    list_display  = ('user', 'coupon', 'amount', 'redeemed_at')
    search_fields = ('user__phone', 'coupon__code')


@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display  = ('user', 'type', 'amount', 'balance_after', 'reference', 'created_at')
    list_filter   = ('type',)
    search_fields = ('user__phone', 'reference')


from .models import FlashSale, Bundle


@admin.register(FlashSale)
class FlashSaleAdmin(admin.ModelAdmin):
    list_display  = ('course', 'discount_pct', 'starts_at', 'ends_at', 'is_active')
    list_filter   = ('is_active',)
    list_editable = ('is_active',)
    search_fields = ('course__title',)


@admin.register(Bundle)
class BundleAdmin(admin.ModelAdmin):
    list_display      = ('title', 'price', 'is_active', 'created_at')
    list_filter       = ('is_active',)
    filter_horizontal = ('courses',)
    search_fields     = ('title',)
