from django.urls import path

from .views import (AESKeyView, LessonProgressView, RequestVideoTokenView,
                     ManifestView, SegmentView)

urlpatterns = [
    path('lesson/<int:lesson_id>/token/',    RequestVideoTokenView.as_view(), name='video_token'),
    path('key/<uuid:token>/',                AESKeyView.as_view(),            name='video_key'),
    path('manifest/<uuid:token>/',           ManifestView.as_view(),          name='video_manifest'),
    path('segment/<uuid:token>/<str:filename>/', SegmentView.as_view(),       name='video_segment'),
    path('lesson/<int:lesson_id>/progress/', LessonProgressView.as_view(),   name='lesson_progress'),
]
