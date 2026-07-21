import csv
import datetime

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.db.models import Q, Sum
from django.contrib import messages
from django.http import HttpResponse, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path
from django.utils.timezone import now

from apps.courses.models import Enrollment
from apps.commerce.models import Order
from apps.notifications.tasks import send_whatsapp_task
from apps.quizzes.models import QuizAttempt
from .models import User, PhoneOTP


class EnrollmentInline(admin.TabularInline):
    model = Enrollment
    extra = 0
    readonly_fields = ('course', 'status', 'payment_method', 'enrolled_at')
    can_delete = False
    show_change_link = True
    fk_name = 'student'


class OrderInline(admin.TabularInline):
    model = Order
    extra = 0
    readonly_fields = ('status', 'payment_method', 'total_price', 'created_at')
    can_delete = False
    show_change_link = True
    fk_name = 'user'


class QuizAttemptInline(admin.TabularInline):
    model = QuizAttempt
    extra = 0
    readonly_fields = ('quiz', 'status', 'result', 'earned_marks', 'total_marks', 'started_at')
    can_delete = False
    fk_name = 'student'


class SegmentFilter(admin.SimpleListFilter):
    title = 'الشريحة'
    parameter_name = 'segment'

    def lookups(self, request, model_admin):
        return [
            ('center_1st', 'سنتر — الصف الأول'),
            ('center_2nd', 'سنتر — الصف الثاني'),
            ('center_3rd', 'سنتر — الصف الثالث'),
            ('online_1st', 'أونلاين — الصف الأول'),
            ('online_2nd', 'أونلاين — الصف الثاني'),
            ('online_3rd', 'أونلاين — الصف الثالث'),
        ]

    def queryset(self, request, queryset):
        if self.value():
            stype, year = self.value().split('_', 1)
            return queryset.filter(student_type=stype, academic_year=year)
        return queryset


class ChurnFilter(admin.SimpleListFilter):
    title = 'النشاط'
    parameter_name = 'churn'

    def lookups(self, request, model_admin):
        return [('inactive_30', 'لم يدخل منذ 30 يوم'), ('inactive_90', 'لم يدخل منذ 90 يوم')]

    def queryset(self, request, queryset):
        if self.value() == 'inactive_30':
            cutoff = now() - datetime.timedelta(days=30)
            return queryset.filter(Q(last_login__lt=cutoff) | Q(last_login__isnull=True))
        if self.value() == 'inactive_90':
            cutoff = now() - datetime.timedelta(days=90)
            return queryset.filter(Q(last_login__lt=cutoff) | Q(last_login__isnull=True))
        return queryset


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display  = ('phone', 'full_name', 'role', 'student_type', 'academic_year',
                     'wallet_balance', 'lifetime_value', 'is_active')
    list_filter   = ('role', 'student_type', 'academic_year', 'is_active', SegmentFilter, ChurnFilter)
    search_fields = ('phone', 'first_name', 'last_name')
    ordering      = ('-date_joined',)
    readonly_fields = ('wp_user_id', 'date_joined', 'last_login')
    actions       = ['export_csv', 'send_welcome_whatsapp', 'send_whatsapp_to_selected']
    inlines       = [EnrollmentInline, OrderInline, QuizAttemptInline]
    fieldsets = (
        (None, {'fields': ('phone', 'password')}),
        ('معلومات شخصية', {'fields': ('first_name', 'last_name', 'guardian_phone')}),
        ('بيانات الطالب', {'fields': ('student_type', 'academic_year', 'wallet_balance')}),
        ('صلاحيات', {'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('نقل بيانات', {'fields': ('wp_user_id',)}),
    )
    add_fieldsets = (
        (None, {'fields': ('phone', 'first_name', 'last_name', 'password1', 'password2', 'role')}),
    )

    def lifetime_value(self, obj):
        total = Order.objects.filter(user=obj, status='completed').aggregate(t=Sum('total_price'))['t'] or 0
        return f'{total:.2f} ج.م'
    lifetime_value.short_description = 'قيمة العميل'

    @admin.action(description='تصدير CSV')
    def export_csv(self, request, queryset):
        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = 'attachment; filename="students.csv"'
        w = csv.writer(response)
        w.writerow(['رقم الهاتف', 'الاسم', 'نوع الطالب', 'السنة الدراسية', 'الرصيد'])
        for u in queryset.values_list('phone', 'first_name', 'last_name', 'student_type', 'academic_year', 'wallet_balance'):
            w.writerow([u[0], f'{u[1]} {u[2]}', u[3], u[4], u[5]])
        return response

    @admin.action(description='إرسال رسالة ترحيبية واتساب')
    def send_welcome_whatsapp(self, request, queryset):
        count = 0
        for user in queryset.filter(phone__isnull=False):
            send_whatsapp_task.delay(user.phone, f'أهلاً {user.first_name}، مرحباً بك في منصة القائد!')
            count += 1
        self.message_user(request, f'تم إرسال {count} رسالة.')

    def get_urls(self):
        custom = [
            path(
                'send-whatsapp/',
                self.admin_site.admin_view(self.send_whatsapp_view),
                name='users_user_send_whatsapp',
            )
        ]
        return custom + super().get_urls()

    @admin.action(description='إرسال رسالة واتساب للمنتخبين')
    def send_whatsapp_to_selected(self, request, queryset):
        ids = ','.join(str(u.pk) for u in queryset)
        return HttpResponseRedirect(f'send-whatsapp/?ids={ids}')

    def send_whatsapp_view(self, request):
        ids_str = request.POST.get('ids') or request.GET.get('ids', '')
        if request.method == 'POST':
            msg = request.POST.get('message', '').strip()
            if msg and ids_str:
                from apps.notifications.tasks import send_whatsapp_task
                from .models import User
                pks = [int(x) for x in ids_str.split(',') if x.strip().isdigit()]
                phones = User.objects.filter(pk__in=pks).values_list('phone', flat=True)
                for phone in phones:
                    send_whatsapp_task.delay(phone, msg)
                messages.success(request, f'تم إرسال {len(phones)} رسالة واتساب.')
            return HttpResponseRedirect('../../')
        context = {
            **self.admin_site.each_context(request),
            'title': 'إرسال رسالة واتساب جماعية',
            'ids': ids_str,
            'user_count': len([x for x in ids_str.split(',') if x.strip()]) if ids_str else 0,
        }
        return TemplateResponse(request, 'admin/users/send_whatsapp.html', context)


@admin.register(PhoneOTP)
class PhoneOTPAdmin(admin.ModelAdmin):
    list_display  = ('phone', 'purpose', 'used', 'attempts', 'expires_at')
    list_filter   = ('purpose', 'used')
    search_fields = ('phone',)
