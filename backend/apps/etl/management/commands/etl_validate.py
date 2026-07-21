"""Quick post-ETL validation — prints counts vs. expected ranges."""
from django.core.management.base import BaseCommand

from apps.commerce.models import Coupon, CouponRedemption, Order
from apps.courses.models import Course, Enrollment, Lesson, Topic
from apps.quizzes.models import AttemptAnswer, Question, Quiz, QuizAttempt
from apps.users.models import User

EXPECTED = {
    'Users':          (5400, 5600),
    'Courses':        (1, 9999),
    'Topics':         (1, 99999),
    'Lessons':        (1, 99999),
    'Quizzes':        (1, 99999),
    'Questions':      (12000, 13500),
    'QuizAttempts':   (9500, 10000),
    'AttemptAnswers': (240000, 255000),
    'Enrollments':    (1, 99999),
    'Orders':         (1, 99999),
}


class Command(BaseCommand):
    help = 'Validate ETL output counts'

    def handle(self, *args, **options):
        checks = [
            ('Users',          User.objects.count()),
            ('Instructors',    User.objects.filter(role='instructor').count()),
            ('Courses',        Course.objects.count()),
            ('Topics',         Topic.objects.count()),
            ('Lessons',        Lesson.objects.count()),
            ('Quizzes',        Quiz.objects.count()),
            ('Questions',      Question.objects.count()),
            ('QuizAttempts',   QuizAttempt.objects.count()),
            ('AttemptAnswers', AttemptAnswer.objects.count()),
            ('Enrollments',    Enrollment.objects.count()),
            ('Orders',         Order.objects.count()),
            ('Coupons',        Coupon.objects.count()),
            ('Redemptions',    CouponRedemption.objects.count()),
        ]
        self.stdout.write('\nETL Validation Report')
        self.stdout.write('=' * 40)
        for label, count in checks:
            lo, hi = EXPECTED.get(label, (0, 999999))
            ok = 'OK ' if lo <= count <= hi else 'WARN'
            self.stdout.write(f'[{ok}] {label:<20} {count:>8}')
        self.stdout.write('=' * 40)
        self.stdout.write('Expected ~5,483 users, ~9,767 attempts, ~246,864 answers')
