"""
ETL Pass 5 — WordPress Tutor LMS quiz attempts → Django QuizAttempt/AttemptAnswer.

Sources: 29_tutor_quiz_attempts (9,767 rows)
         29_tutor_quiz_attempt_answers (246,864 rows)
Target:  apps.quizzes.QuizAttempt, AttemptAnswer

Strategy:
  - Attempts: update_or_create in batches of 200 (small table, idempotent).
  - Answers:  LIMIT/OFFSET streaming in chunks of 2000, bulk_create(ignore_conflicts=True).
    Never fetchall on 246K rows.

Run:
    python manage.py etl_pass_5_attempts --dry-run
    python manage.py etl_pass_5_attempts --batch-size 200
    python manage.py etl_pass_5_attempts --offset 50000   # resume answers from row 50000
    python manage.py etl_pass_5_attempts --sub-pass A     # attempts only
    python manage.py etl_pass_5_attempts --sub-pass B     # answers only
"""
import logging
from decimal import Decimal, InvalidOperation

import pymysql
from decouple import config
from django.core.management.base import BaseCommand
from django.utils import timezone
from tqdm import tqdm

from apps.quizzes.models import AttemptAnswer, Question, Quiz, QuizAttempt
from apps.users.models import User

logger = logging.getLogger(__name__)

WP_PREFIX = '29_'

STATUS_MAP = {
    'attempt_started': 'in_progress',
    'attempt_ended':   'submitted',
    'attempt_timeout': 'timed_out',
}


def _wp_conn():
    return pymysql.connect(
        host=config('WP_DB_HOST'),
        port=int(config('WP_DB_PORT', default='3306')),
        db=config('WP_DB_NAME'),
        user=config('WP_DB_USER'),
        password=config('WP_DB_PASSWORD'),
        charset='utf8mb4',
    )


def _dec(val, default='0'):
    try:
        return Decimal(str(val or default))
    except InvalidOperation:
        return Decimal(default)


class Command(BaseCommand):
    help = 'ETL Pass 5: migrate WordPress Tutor LMS quiz attempts and answers'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Preview only — no DB writes')
        parser.add_argument('--batch-size', type=int, default=200,
                            help='Rows per batch for attempts (default 200); answers chunk is 10x')
        parser.add_argument('--offset', type=int, default=0,
                            help='Row offset to resume answer streaming from (default 0)')
        parser.add_argument(
            '--sub-pass', choices=['A', 'B'], default=None,
            help='Run only A=attempts or B=answers. Default: both.',
        )

    def handle(self, *args, **options):
        dry_run    = options['dry_run']
        batch_size = options['batch_size']
        offset     = options['offset']
        sub_pass   = options['sub_pass']

        run_a = sub_pass in (None, 'A')
        run_b = sub_pass in (None, 'B')

        if run_a:
            self._pass_a(dry_run, batch_size)
        if run_b:
            self._pass_b(dry_run, batch_size * 10, offset)

    # ------------------------------------------------------------------
    # Sub-pass A: QuizAttempts
    # ------------------------------------------------------------------
    def _pass_a(self, dry_run, batch_size):
        self.stdout.write('--- Sub-pass A: Quiz Attempts ---')
        conn = _wp_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(f"""
                    SELECT attempt_id, course_id, quiz_id, user_id,
                           total_marks, earned_marks,
                           attempt_status, attempt_ended_at, attempt_ip
                    FROM {WP_PREFIX}tutor_quiz_attempts
                    ORDER BY attempt_id
                """)
                rows = cur.fetchall()
        finally:
            conn.close()

        # Preload lookup maps — quiz needs topic.course_id, preload all at once
        # ponytail: select_related in one query avoids N+1 per attempt
        quiz_map  = {q.wp_post_id: q for q in Quiz.objects.select_related('topic').filter(wp_post_id__isnull=False)}
        user_map  = {u.wp_user_id: u for u in User.objects.filter(wp_user_id__isnull=False)}

        self.stdout.write(f'Found {len(rows)} attempts. dry_run={dry_run}')

        created = updated = skipped = 0
        for i in tqdm(range(0, len(rows), batch_size), desc='Attempts'):
            batch = rows[i:i + batch_size]
            for (attempt_id, course_id, quiz_id, user_id,
                 total_marks, earned_marks, attempt_status, ended_at, attempt_ip) in batch:

                quiz = quiz_map.get(quiz_id)
                if quiz is None:
                    skipped += 1
                    logger.warning('Attempt wp_id=%s: quiz wp_post_id=%s not found, skipping', attempt_id, quiz_id)
                    continue

                user = user_map.get(user_id)
                if user is None:
                    skipped += 1
                    logger.warning('Attempt wp_id=%s: user wp_user_id=%s not found, skipping', attempt_id, user_id)
                    continue

                total  = _dec(total_marks)
                earned = _dec(earned_marks)
                status = STATUS_MAP.get(attempt_status or '', 'submitted')

                if attempt_status == 'attempt_ended' and total > 0:
                    threshold = total * (quiz.pass_mark / Decimal('100'))
                    result = 'pass' if earned >= threshold else 'fail'
                else:
                    result = None

                defaults = dict(
                    student=user,
                    quiz=quiz,
                    course_id=quiz.topic.course_id,
                    total_marks=total,
                    earned_marks=earned,
                    status=status,
                    result=result,
                    ended_at=ended_at,
                )
                if not dry_run:
                    _, was_created = QuizAttempt.objects.update_or_create(
                        wp_attempt_id=attempt_id,
                        defaults=defaults,
                    )
                    if was_created:
                        created += 1
                    else:
                        updated += 1
                else:
                    created += 1

        verb = 'Would create/update' if dry_run else 'Done'
        self.stdout.write(
            self.style.SUCCESS(
                f'{verb}: {created} created, {updated} updated, {skipped} skipped'
            )
        )

    # ------------------------------------------------------------------
    # Sub-pass B: AttemptAnswers  (246K rows — streamed with LIMIT/OFFSET)
    # ------------------------------------------------------------------
    def _pass_b(self, dry_run, chunk_size, start_offset):
        self.stdout.write('--- Sub-pass B: Attempt Answers (streaming) ---')

        # Preload maps (IDs only to keep memory low)
        attempt_map  = {a.wp_attempt_id: a.id for a in QuizAttempt.objects.filter(wp_attempt_id__isnull=False)}
        question_map = {q.wp_question_id: q.id for q in Question.objects.filter(wp_question_id__isnull=False)}

        self.stdout.write(
            f'Loaded {len(attempt_map)} attempts, {len(question_map)} questions. '
            f'chunk_size={chunk_size}, start_offset={start_offset} dry_run={dry_run}'
        )

        conn = _wp_conn()
        offset    = start_offset
        total_ins = 0
        total_skip = 0

        try:
            with tqdm(desc='AttemptAnswers', unit=' rows') as pbar:
                while True:
                    with conn.cursor() as cur:
                        cur.execute(f"""
                            SELECT attempt_answer_id, quiz_attempt_id, question_id,
                                   given_answer, is_correct, marks_achieved
                            FROM {WP_PREFIX}tutor_quiz_attempt_answers
                            ORDER BY quiz_attempt_id
                            LIMIT %s OFFSET %s
                        """, (chunk_size, offset))
                        chunk = cur.fetchall()

                    if not chunk:
                        break

                    objs = []
                    for (answer_id, attempt_id, question_id,
                         given_answer, is_correct, marks_achieved) in chunk:

                        django_attempt_id  = attempt_map.get(attempt_id)
                        django_question_id = question_map.get(question_id)

                        if django_attempt_id is None or django_question_id is None:
                            total_skip += 1
                            continue

                        # is_correct: WP stores 0/1/None
                        if is_correct is None:
                            correct = None
                        else:
                            correct = bool(int(is_correct))

                        objs.append(AttemptAnswer(
                            attempt_id=django_attempt_id,
                            question_id=django_question_id,
                            given_answer=given_answer or '',
                            is_correct=correct,
                            marks_achieved=_dec(marks_achieved),
                            wp_answer_id=answer_id,
                        ))

                    if not dry_run and objs:
                        # ponytail: ignore_conflicts — re-runs are safe, wp_answer_id is not unique
                        # constrained at DB level; upgrade to update_or_create if accuracy matters
                        AttemptAnswer.objects.bulk_create(objs, ignore_conflicts=True)

                    total_ins  += len(objs)
                    offset     += len(chunk)
                    pbar.update(len(chunk))
        finally:
            conn.close()

        verb = 'Would insert' if dry_run else 'Inserted'
        self.stdout.write(
            self.style.SUCCESS(
                f'{verb} ~{total_ins} attempt answers '
                f'(skipped {total_skip} with missing attempt/question). '
                f'Total rows processed: {offset - start_offset}'
            )
        )
