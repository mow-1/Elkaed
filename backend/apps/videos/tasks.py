import os
import secrets
from pathlib import Path

from celery import shared_task
from django.conf import settings

from .services import TranscodeError, transcode_to_hls


@shared_task
def transcode_video_task(video_id):
    from .models import Video

    try:
        video = Video.objects.get(pk=video_id)
    except Video.DoesNotExist:
        return

    if not video.raw_file:
        video.status = 'failed'
        video.error_message = 'لا يوجد ملف فيديو مرفوع'
        video.save(update_fields=['status', 'error_message'])
        return

    video.status = 'processing'
    video.save(update_fields=['status'])

    input_path = video.raw_file.path
    output_dir = Path(settings.MEDIA_ROOT) / 'videos' / 'hls' / str(video.id)

    try:
        result = transcode_to_hls(input_path, output_dir)
    except TranscodeError as exc:
        video.status = 'failed'
        video.error_message = str(exc)
        video.save(update_fields=['status', 'error_message'])
        return

    video.aes_key = result['aes_key']
    video.aes_key_id = secrets.token_hex(4)
    video.hls_path = result['hls_relpath']
    video.original_path = video.raw_file.name
    video.duration_seconds = result['duration_seconds']
    video.file_size_bytes = os.path.getsize(input_path)
    video.thumbnails = [result['thumbnail_relpath']] if result['thumbnail_relpath'] else []
    video.status = 'ready'
    video.error_message = ''
    video.save()
