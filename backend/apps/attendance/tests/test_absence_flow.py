from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase

from apps.attendance.models import CenterGroup, PhysicalSession, AttendanceRecord
from apps.attendance.services import mark_absent, mark_present, set_attendance_status
from apps.commerce.models import WalletTransaction
from apps.courses.models import Category, Course, LessonAccessGrant, Topic, Lesson
from apps.users.models import User


class AbsenceFlowTests(TestCase):
    def setUp(self):
        self.group = CenterGroup.objects.create(name_ar='G1', academic_year='2nd')
        self.student = User.objects.create_user(
            phone='201099999991', first_name='Absent', last_name='Test',
            academic_year='2nd', student_type='center', role='student',
            password='x', group=self.group,
        )
        self.student.wallet_balance = Decimal('200')
        self.student.save(update_fields=['wallet_balance'])

        cat = Category.objects.create(name='C', slug='cat-absence-test')
        course = Course.objects.create(
            title='Course', slug='course-absence-test', description='d',
            instructor=self.student, category=cat, price=Decimal('0'),
        )
        topic = Topic.objects.create(course=course, title='T', order=1)
        self.lesson = Lesson.objects.create(topic=topic, title='L', order=1)
        self.session = PhysicalSession.objects.create(
            group=self.group, date='2026-07-21', title_ar='S1', linked_lesson=self.lesson,
        )

    @patch('apps.notifications.tasks.send_whatsapp_task.delay')
    def test_absence_deducts_wallet_grants_lesson_and_sends_whatsapp(self, mock_delay):
        record = mark_absent(self.session, self.student, actor=None)
        self.student.refresh_from_db()

        self.assertEqual(self.student.wallet_balance, Decimal('120'))
        self.assertTrue(record.deducted)
        self.assertTrue(record.whatsapp_sent)
        self.assertTrue(
            LessonAccessGrant.objects.filter(
                student=self.student, lesson=self.lesson, revoked=False,
            ).exists()
        )
        mock_delay.assert_called_once()
        self.assertEqual(mock_delay.call_args[0][0], self.student.phone)

        self.assertEqual(
            WalletTransaction.objects.filter(
                user=self.student, reason_code='attendance_absent',
            ).count(),
            1,
        )

    @patch('apps.notifications.tasks.send_whatsapp_task.delay')
    def test_video_access_gate_now_allows_the_granted_lesson(self, mock_delay):
        from rest_framework_simplejwt.tokens import RefreshToken
        from apps.videos.models import Video

        # lesson currently has no Video attached (RequestVideoTokenView 400s before the
        # enrollment/grant check without one) — attach a minimal one so the grant check
        # is actually what's being exercised.
        video = Video.objects.create(
            title='V', uploaded_by=self.student, original_path='x',
            aes_key=b'0' * 16, aes_key_id='k1',
        )
        self.lesson.video = video
        self.lesson.video_source = 'self_hosted'
        self.lesson.save(update_fields=['video', 'video_source'])

        mark_absent(self.session, self.student, actor=None)

        access = str(RefreshToken.for_user(self.student).access_token)
        response = self.client.post(
            f'/api/videos/lesson/{self.lesson.id}/token/',
            HTTP_AUTHORIZATION=f'Bearer {access}',
        )
        self.assertEqual(response.status_code, 200)

    @patch('apps.notifications.tasks.send_whatsapp_task.delay')
    def test_override_to_excused_reverses_deduction_and_revokes_grant(self, mock_delay):
        record = mark_absent(self.session, self.student, actor=None)
        set_attendance_status(record, 'absent_excused', actor=None)
        self.student.refresh_from_db()

        self.assertEqual(self.student.wallet_balance, Decimal('200'))
        self.assertTrue(
            LessonAccessGrant.objects.filter(
                student=self.student, lesson=self.lesson, revoked=True,
            ).exists()
        )
        self.assertTrue(
            WalletTransaction.objects.filter(user=self.student, reason_code='reversal').exists()
        )

    def test_marking_present_twice_is_idempotent_no_double_deduction(self):
        mark_present(self.session, self.student, actor=None)
        mark_present(self.session, self.student, actor=None)
        self.student.refresh_from_db()

        self.assertEqual(self.student.wallet_balance, Decimal('120'))
        self.assertEqual(
            AttendanceRecord.objects.filter(session=self.session, student=self.student).count(),
            1,
        )
        self.assertEqual(
            WalletTransaction.objects.filter(
                user=self.student, reason_code='attendance_present',
            ).count(),
            1,
        )
