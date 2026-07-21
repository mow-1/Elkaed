from django.contrib import admin
from .models import PricingSettings


@admin.register(PricingSettings)
class PricingSettingsAdmin(admin.ModelAdmin):
    list_display = ('single_lesson_price', 'monthly_package_price', 'package_lesson_count', 'allow_negative_balance')
