import re
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.db.models import F
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.timezone import now
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.courses.models import Enrollment, Lesson, LessonProgress
from .models import VideoAccessLog, VideoAccessToken
from .serializers import LessonProgressUpdateSerializer, VideoTokenSerializer
from .services import KEY_URI_PLACEHOLDER


def _get_ip(request):
    return (
        request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', ''))
        .split(',')[0]
        .strip()
    )


class RequestVideoTokenView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, lesson_id):
        lesson = get_object_or_404(Lesson, pk=lesson_id)

        if lesson.video_source != 'self_hosted' or lesson.video is None:
            return Response(
                {'detail': 'هذا الدرس لا يحتوي على فيديو مستضاف'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not lesson.is_free_preview:
            from apps.courses.models import LessonAccessGrant
            has_access = Enrollment.objects.filter(
                student=request.user,
                course=lesson.topic.course,
                status='active',
            ).exists() or LessonAccessGrant.objects.filter(
                student=request.user, lesson=lesson, revoked=False,
            ).exists()
            if not has_access:
                return Response(
                    {'detail': 'يجب الاشتراك في الكورس للوصول إلى هذا الدرس'},
                    status=status.HTTP_403_FORBIDDEN,
                )
        else:
            # free-preview lessons normally bypass enrollment entirely — but a revision
            # video (a Material linking to this lesson) may target one academic year,
            # so a free-preview lesson used that way still needs the year check.
            from apps.courses.models import Material
            revision = Material.objects.filter(lesson=lesson, academic_year__gt='').first()
            if revision and revision.academic_year != request.user.academic_year:
                return Response(
                    {'detail': 'هذا الدرس غير متاح لصفك الدراسي'},
                    status=status.HTTP_403_FORBIDDEN,
                )

        if lesson.view_limit > 0:
            progress, _ = LessonProgress.objects.get_or_create(
                student=request.user, lesson=lesson
            )
            if progress.view_count >= lesson.view_limit:
                return Response(
                    {'detail': 'تجاوزت عدد مرات المشاهدة المسموح'},
                    status=status.HTTP_403_FORBIDDEN,
                )

        ip = _get_ip(request)

        # Idempotent: reuse an existing still-valid token for this user+video instead
        # of revoking it — a request for "the" token isn't destructive by itself.
        # Revoking-on-every-request broke playback under React StrictMode's
        # double-invoked effects (and would equally break a double-click or two open
        # tabs in production): the first token would die the instant the second
        # request revoked it, so the player that actually started using it got a
        # 403 on the key/segment fetch moments later.
        existing = VideoAccessToken.objects.filter(
            user=request.user, video=lesson.video, used=False,
            expires_at__gt=now(), ip_address=ip,
        ).order_by('-issued_at').first()

        token = existing or VideoAccessToken.objects.create(
            user=request.user,
            video=lesson.video,
            lesson=lesson,
            expires_at=now() + timedelta(minutes=20),
            ip_address=ip,
        )

        VideoAccessLog.objects.create(
            user=request.user,
            lesson=lesson,
            ip_address=ip,
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
            token_issued=True,
        )

        hls_url = request.build_absolute_uri(f'/api/videos/manifest/{token.token}/')

        progress = LessonProgress.objects.filter(student=request.user, lesson=lesson).first()
        view_count = progress.view_count if progress else 0
        views_remaining = (
            max(0, lesson.view_limit - view_count) if lesson.view_limit > 0 else None
        )

        return Response(
            VideoTokenSerializer({
                'token': token.token,
                'hls_url': hls_url,
                'expires_at': token.expires_at,
                'views_remaining': views_remaining,
            }).data
        )


class AESKeyView(APIView):
    # ponytail: no auth middleware — key access is validated by token + IP
    permission_classes = []

    def get(self, request, token):
        token_obj = get_object_or_404(VideoAccessToken, token=token)
        ip = _get_ip(request)

        if not token_obj.is_valid(ip):
            VideoAccessLog.objects.create(
                user=token_obj.user,
                lesson=token_obj.lesson,
                ip_address=ip,
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
                token_issued=False,
                denial_reason='invalid_token',
            )
            return HttpResponse(status=403)

        VideoAccessToken.objects.filter(pk=token_obj.pk).update(used=True)

        VideoAccessLog.objects.create(
            user=token_obj.user,
            lesson=token_obj.lesson,
            ip_address=ip,
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
            token_issued=False,
        )

        LessonProgress.objects.get_or_create(
            student=token_obj.user, lesson=token_obj.lesson
        )
        LessonProgress.objects.filter(
            student=token_obj.user, lesson=token_obj.lesson
        ).update(view_count=F('view_count') + 1, last_watched=now())

        return HttpResponse(bytes(token_obj.video.aes_key), content_type='application/octet-stream')


class ManifestView(APIView):
    """Serves the HLS manifest for a viewing session, rewriting the placeholder key
    URI and every segment filename to token-scoped URLs — segments and the key are
    validated the same way as this manifest, one per-viewing token gates all three."""
    permission_classes = []

    def get(self, request, token):
        token_obj = get_object_or_404(VideoAccessToken, token=token)
        ip = _get_ip(request)
        if not token_obj.is_valid_for_playback(ip):
            return HttpResponse(status=403)

        manifest_path = Path(settings.MEDIA_ROOT) / token_obj.video.hls_path
        if not manifest_path.exists():
            return HttpResponse(status=404)

        key_url = request.build_absolute_uri(f'/api/videos/key/{token}/')
        segment_base = request.build_absolute_uri(f'/api/videos/segment/{token}/')

        lines_out = []
        for line in manifest_path.read_text().splitlines():
            if line.startswith('#EXT-X-KEY'):
                line = line.replace(KEY_URI_PLACEHOLDER, key_url)
            elif line and not line.startswith('#'):
                line = segment_base + line
            lines_out.append(line)

        return HttpResponse('\n'.join(lines_out), content_type='application/vnd.apple.mpegurl')


class SegmentView(APIView):
    """Serves one encrypted .ts segment, gated by the same viewing token as the
    manifest and key. The segment bytes are already AES-128 ciphertext — this view
    adds nothing beyond access control, no per-request decryption happens here."""
    permission_classes = []

    def get(self, request, token, filename):
        if not re.fullmatch(r'seg_\d{3}\.ts', filename):
            return HttpResponse(status=400)

        token_obj = get_object_or_404(VideoAccessToken, token=token)
        ip = _get_ip(request)
        if not token_obj.is_valid_for_playback(ip):
            return HttpResponse(status=403)

        segment_path = Path(settings.MEDIA_ROOT) / Path(token_obj.video.hls_path).parent / filename
        if not segment_path.exists():
            return HttpResponse(status=404)

        return HttpResponse(segment_path.read_bytes(), content_type='video/mp2t')


class LessonProgressView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, lesson_id):
        lesson = get_object_or_404(Lesson, pk=lesson_id)
        ser = LessonProgressUpdateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        progress, _ = LessonProgress.objects.get_or_create(student=request.user, lesson=lesson)
        progress.last_position_seconds = ser.validated_data['position_seconds']
        if ser.validated_data.get('completed'):
            progress.completed = True
        progress.save(update_fields=['last_position_seconds', 'completed', 'last_watched'])
        return Response({'detail': 'تم حفظ التقدم.'})
