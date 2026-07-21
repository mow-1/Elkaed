from datetime import timedelta

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

        # Revoke any live token for this user+video before issuing a new one
        VideoAccessToken.objects.filter(
            user=request.user, video=lesson.video, used=False
        ).update(used=True)

        token = VideoAccessToken.objects.create(
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

        cloudfront = getattr(settings, 'CLOUDFRONT_DOMAIN', '')
        hls_url = (
            f'https://{cloudfront}/{lesson.video.hls_path}'
            if cloudfront
            else lesson.video.hls_path
        )

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
