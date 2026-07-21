from django.contrib import admin
from .models import Video, VideoAccessLog
from .tasks import transcode_video_task


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display  = ('title', 'uploaded_by', 'status', 'duration_seconds', 'created_at')
    list_filter   = ('status',)
    search_fields = ('title',)
    readonly_fields = ('status', 'error_message', 'hls_path', 'aes_key_id',
                        'duration_seconds', 'file_size_bytes', 'thumbnails')
    fields = ('title', 'uploaded_by', 'raw_file', 'status', 'error_message',
              'hls_path', 'aes_key_id', 'duration_seconds', 'file_size_bytes', 'thumbnails')

    def save_model(self, request, obj, form, change):
        queue_transcode = 'raw_file' in form.changed_data and bool(obj.raw_file)
        super().save_model(request, obj, form, change)
        if queue_transcode:
            transcode_video_task.delay(obj.pk)


@admin.register(VideoAccessLog)
class VideoAccessLogAdmin(admin.ModelAdmin):
    list_display  = ('user', 'lesson', 'ip_address', 'token_issued', 'denial_reason', 'timestamp')
    list_filter   = ('token_issued',)
    search_fields = ('user__phone',)
