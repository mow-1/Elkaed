from django.urls import path

from .views import AESKeyView, LessonProgressView, RequestVideoTokenView

urlpatterns = [
    path('lesson/<int:lesson_id>/token/',    RequestVideoTokenView.as_view(), name='video_token'),
    path('key/<uuid:token>/',                AESKeyView.as_view(),            name='video_key'),
    path('lesson/<int:lesson_id>/progress/', LessonProgressView.as_view(),   name='lesson_progress'),
]
