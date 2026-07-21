from django.contrib import admin
from .models import Video, VideoAccessLog


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display  = ('title', 'uploaded_by', 'status', 'duration_seconds', 'created_at')
    list_filter   = ('status',)
    search_fields = ('title',)


@admin.register(VideoAccessLog)
class VideoAccessLogAdmin(admin.ModelAdmin):
    list_display  = ('user', 'lesson', 'ip_address', 'token_issued', 'denial_reason', 'timestamp')
    list_filter   = ('token_issued',)
    search_fields = ('user__phone',)
