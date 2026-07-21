from django.urls import path
from .views import (QuizDetailView, StartAttemptView, SubmitAttemptView, AttemptResultView,
                     QuizExportView, MyAttemptsView)

urlpatterns = [
    path('my-attempts/',                      MyAttemptsView.as_view(),   name='my_attempts'),
    path('<int:quiz_id>/',                    QuizDetailView.as_view(),   name='quiz_detail'),
    path('<int:quiz_id>/start/',              StartAttemptView.as_view(), name='quiz_start'),
    path('attempts/<int:attempt_id>/submit/', SubmitAttemptView.as_view(), name='quiz_submit'),
    path('attempts/<int:attempt_id>/',        AttemptResultView.as_view(), name='quiz_attempt'),
    path('<int:quiz_id>/export/',             QuizExportView.as_view(),    name='quiz_export'),
]
