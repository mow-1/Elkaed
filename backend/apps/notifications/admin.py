from django.contrib import admin
from django.http import HttpResponseRedirect
from django.urls import reverse
from .models import (HomepageBanner, NotificationTemplate, Campaign,
                     NotificationPreference, EmailCampaign,
                     LandingHero, LandingFeature, LandingTestimonial,
                     LandingDarkBand, LandingCTA)


@admin.register(HomepageBanner)
class HomepageBannerAdmin(admin.ModelAdmin):
    list_display = ('title_ar', 'is_active', 'order', 'starts_at', 'ends_at')
    list_filter  = ('is_active',)
    list_editable = ('is_active', 'order')


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ('trigger', 'is_active')
    list_filter  = ('is_active',)


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display    = ('title', 'segment', 'status', 'sent_count', 'created_at', 'sent_at')
    list_filter     = ('status', 'segment')
    search_fields   = ('title',)
    readonly_fields = ('sent_count', 'sent_at', 'status')
    actions         = ['send_campaign']

    @admin.action(description='إرسال الحملة للشريحة المحددة')
    def send_campaign(self, request, queryset):
        from .tasks import send_campaign_task
        for campaign in queryset.filter(status='draft'):
            campaign.status = 'sending'
            campaign.save(update_fields=['status'])
            send_campaign_task.delay(campaign.pk)
        self.message_user(request, 'بدأ إرسال الحملات.')


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display  = ('user', 'notif_type', 'enabled')
    list_filter   = ('notif_type', 'enabled')
    search_fields = ('user__phone',)
    list_editable = ('enabled',)


@admin.register(EmailCampaign)
class EmailCampaignAdmin(admin.ModelAdmin):
    list_display    = ('subject', 'segment', 'status', 'sent_count', 'created_at')
    list_filter     = ('status', 'segment')
    search_fields   = ('subject',)
    readonly_fields = ('sent_count', 'sent_at', 'status')
    actions         = ['send_email_campaign']

    @admin.action(description='إرسال الحملة بالبريد الإلكتروني')
    def send_email_campaign(self, request, queryset):
        from .tasks import send_email_campaign_task
        for campaign in queryset.filter(status='draft'):
            campaign.status = 'sending'
            campaign.save(update_fields=['status'])
            send_email_campaign_task.delay(campaign.pk)
        self.message_user(request, 'بدأ إرسال حملات الإيميل.')


class SingletonAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return not self.model.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        obj, _ = self.model.objects.get_or_create(pk=1)
        return HttpResponseRedirect(
            reverse(f'admin:{self.model._meta.app_label}_{self.model._meta.model_name}_change', args=[1])
        )


@admin.register(LandingHero)
class LandingHeroAdmin(SingletonAdmin):
    fieldsets = (
        ('النص الرئيسي', {'fields': ('eyebrow', 'heading', 'heading_white', 'para')}),
        ('أزرار الدعوة', {'fields': ('cta1_text', 'cta1_link', 'cta2_text', 'cta2_link')}),
        ('الإحصائيات', {'fields': (
            ('stat1_num', 'stat1_label'),
            ('stat2_num', 'stat2_label'),
            ('stat3_num', 'stat3_label'),
        )}),
    )


@admin.register(LandingFeature)
class LandingFeatureAdmin(admin.ModelAdmin):
    list_display  = ('title', 'glyph', 'order')
    list_editable = ('order',)
    ordering      = ('order',)


@admin.register(LandingTestimonial)
class LandingTestimonialAdmin(admin.ModelAdmin):
    list_display  = ('author_name', 'grade', 'order')
    list_editable = ('order',)
    ordering      = ('order',)


@admin.register(LandingDarkBand)
class LandingDarkBandAdmin(SingletonAdmin):
    fieldsets = (
        ('النص', {'fields': ('heading', 'body')}),
        ('قائمة المميزات', {'fields': ('check1', 'check2', 'check3', 'check4')}),
        ('زر الدعوة', {'fields': ('cta_text', 'cta_link')}),
    )


@admin.register(LandingCTA)
class LandingCTAAdmin(SingletonAdmin):
    fieldsets = (
        (None, {'fields': ('glyph', 'heading', 'body', 'cta_text', 'cta_link')}),
    )
