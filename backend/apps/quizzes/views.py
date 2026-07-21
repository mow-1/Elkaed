import csv
import random
from decimal import Decimal
from django.http import HttpResponse
from django.utils import timezone
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from apps.courses.models import Enrollment
from apps.notifications.tasks import send_whatsapp_task
from .models import Quiz, QuizAttempt, AttemptAnswer
from .serializers import (
    QuizDetailSerializer, SubmitAttemptSerializer, AttemptResultSerializer, MyAttemptSerializer
)


def _check_enrollment(user, course):
    if not Enrollment.objects.filter(student=user, course=course, status='active').exists():
        return False
    return True


class QuizDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, quiz_id):
        quiz = get_object_or_404(Quiz.objects.prefetch_related('questions__choices'), pk=quiz_id)
        if not _check_enrollment(request.user, quiz.topic.course):
            return Response({'detail': 'غير مشترك في هذا الكورس'}, status=status.HTTP_403_FORBIDDEN)

        data = QuizDetailSerializer(quiz).data

        if quiz.shuffle_questions:
            random.shuffle(data['questions'])

        if quiz.shuffle_answers:
            for q in data['questions']:
                random.shuffle(q['choices'])

        return Response(data)


class StartAttemptView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, quiz_id):
        quiz = get_object_or_404(Quiz.objects.prefetch_related('questions'), pk=quiz_id)
        course = quiz.topic.course

        if not _check_enrollment(request.user, course):
            return Response({'detail': 'غير مشترك في هذا الكورس'}, status=status.HTTP_403_FORBIDDEN)

        if quiz.is_locked:
            return Response({'detail': 'الاختبار مقفول حالياً'}, status=status.HTTP_403_FORBIDDEN)

        if quiz.attempts_allowed > 0:
            used = QuizAttempt.objects.filter(
                student=request.user, quiz=quiz, status__in=['submitted', 'timed_out']
            ).count()
            if used >= quiz.attempts_allowed:
                return Response({'detail': 'تجاوزت عدد المحاولات المسموح به'}, status=status.HTTP_400_BAD_REQUEST)

        existing = QuizAttempt.objects.filter(student=request.user, quiz=quiz, status='in_progress').first()
        if existing:
            return Response({'attempt_id': existing.id, 'started_at': existing.started_at, 'time_limit': quiz.time_limit})

        total = sum(q.mark for q in quiz.questions.all())
        attempt = QuizAttempt.objects.create(
            student=request.user,
            quiz=quiz,
            course=course,
            total_marks=total,
        )
        return Response({'attempt_id': attempt.id, 'started_at': attempt.started_at, 'time_limit': quiz.time_limit})


class SubmitAttemptView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, attempt_id):
        attempt = get_object_or_404(QuizAttempt.objects.select_related('quiz', 'student'), pk=attempt_id)

        if attempt.student != request.user:
            return Response({'detail': 'غير مصرح'}, status=status.HTTP_403_FORBIDDEN)

        if attempt.status != 'in_progress':
            return Response({'detail': 'تم تسليم الاختبار مسبقاً'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = SubmitAttemptSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        quiz = attempt.quiz
        questions_map = {q.id: q for q in quiz.questions.prefetch_related('choices').all()}
        valid_question_ids = set(questions_map.keys())

        with transaction.atomic():
            earned = Decimal('0')
            for ans in serializer.validated_data['answers']:
                qid = ans['question_id']
                if qid not in valid_question_ids:
                    continue

                question = questions_map[qid]
                given    = ans['given_answer'].strip()
                is_correct    = None
                marks_achieved = Decimal('0')

                if question.question_type == 'mcq':
                    try:
                        choice = question.choices.get(pk=int(given))
                        is_correct = choice.is_correct
                        if is_correct:
                            marks_achieved = question.mark
                    except (question.choices.model.DoesNotExist, ValueError):
                        is_correct = False

                elif question.question_type == 'tf':
                    try:
                        # ponytail: assumes tf questions have choices with text "true"/"false"
                        choice = question.choices.get(is_correct=True)
                        is_correct = choice.text.lower() == given.lower()
                        if is_correct:
                            marks_achieved = question.mark
                    except question.choices.model.DoesNotExist:
                        is_correct = False

                # fill/open/ordering: needs manual review
                AttemptAnswer.objects.create(
                    attempt=attempt,
                    question=question,
                    given_answer=given,
                    is_correct=is_correct,
                    marks_achieved=marks_achieved,
                )
                if marks_achieved:
                    earned += marks_achieved

            pass_threshold = attempt.total_marks * (quiz.pass_mark / Decimal('100'))
            result = 'pass' if earned >= pass_threshold else 'fail'

            attempt.earned_marks = earned
            attempt.status       = 'submitted'
            attempt.result       = result
            attempt.ended_at     = timezone.now()
            attempt.save(update_fields=['earned_marks', 'status', 'result', 'ended_at'])

        student = attempt.student
        msg = (
            f"نتيجة الاختبار: {quiz.title}\n"
            f"الدرجة: {earned} / {attempt.total_marks}\n"
            f"النتيجة: {'ناجح' if result == 'pass' else 'راسب'}"
        )
        if student.phone:
            send_whatsapp_task.delay(student.phone, msg)
        if student.guardian_phone:
            send_whatsapp_task.delay(student.guardian_phone, msg)

        return Response(AttemptResultSerializer(attempt).data)


class AttemptResultView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, attempt_id):
        attempt = get_object_or_404(
            QuizAttempt.objects.select_related('quiz').prefetch_related('answers__question'),
            pk=attempt_id
        )
        if attempt.student != request.user:
            return Response({'detail': 'غير مصرح'}, status=status.HTTP_403_FORBIDDEN)

        data = AttemptResultSerializer(attempt).data
        if attempt.quiz.hide_results:
            data.pop('answers', None)

        return Response(data)


class MyAttemptsView(APIView):
    """Portal Results tab: all of the current student's submitted attempts, newest first."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        attempts = (
            QuizAttempt.objects
            .filter(student=request.user, status='submitted')
            .select_related('quiz', 'course')
            .order_by('-started_at')
        )
        return Response(MyAttemptSerializer(attempts, many=True).data)


class QuizExportView(APIView):
    """CSV export of all attempts for a quiz. Instructor/admin only."""
    permission_classes = [IsAuthenticated]

    def get(self, request, quiz_id):
        quiz = get_object_or_404(Quiz, pk=quiz_id)

        # quiz.topic.course confirmed valid from models.py: Quiz→Topic→Course
        is_owner = quiz.topic.course.instructor == request.user
        if request.user.role not in ('admin', 'staff') and not is_owner:
            return Response({'detail': 'غير مصرح.'}, status=status.HTTP_403_FORBIDDEN)

        attempts = (
            QuizAttempt.objects
            .filter(quiz=quiz)
            .select_related('student')
            .order_by('student__phone', '-started_at')
        )

        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = f'attachment; filename="quiz_{quiz_id}_results.csv"'
        w = csv.writer(response)
        w.writerow(['رقم الهاتف', 'الاسم', 'الحالة', 'النتيجة', 'الدرجة', 'من', 'تاريخ البدء'])
        for a in attempts:
            w.writerow([
                a.student.phone,
                a.student.full_name,
                a.status,
                a.result,
                a.earned_marks,
                a.total_marks,
                a.started_at.strftime('%Y-%m-%d %H:%M'),
            ])
        return response
