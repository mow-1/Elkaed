"""
ETL Pass 4 — WordPress Tutor LMS quizzes → Django Quiz/Question/AnswerChoice models.

Sources: 29_posts, 29_postmeta, 29_tutor_quiz_questions, 29_tutor_quiz_question_answers
Target:  apps.quizzes.Quiz, Question, AnswerChoice

Sub-passes:
  A — Quizzes    (from 29_posts WHERE post_type='tutor_quiz')
  B — Questions  (from 29_tutor_quiz_questions)
  C — Answers    (from 29_tutor_quiz_question_answers)

Run:
    python manage.py etl_pass_4_quizzes --dry-run
    python manage.py etl_pass_4_quizzes --batch-size 200
    python manage.py etl_pass_4_quizzes --sub-pass A
"""
import logging
from decimal import Decimal, InvalidOperation

import phpserialize
import pymysql
from decouple import config
from django.core.management.base import BaseCommand
from tqdm import tqdm

from apps.courses.models import Topic
from apps.quizzes.models import AnswerChoice, Question, Quiz

logger = logging.getLogger(__name__)

WP_PREFIX = '29_'

TYPE_MAP = {
    'single_choice':   'mcq',
    'multiple_choice': 'mcq',
    'true_false':      'tf',
    'fill_in_the_blank': 'fill',
    'open_ended':      'open',
    'ordering':        'ordering',
    'h5p':             'open',  # fallback
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
    help = 'ETL Pass 4: migrate WordPress Tutor LMS quizzes, questions, and answers'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Preview only — no DB writes')
        parser.add_argument('--batch-size', type=int, default=200)
        parser.add_argument(
            '--sub-pass', choices=['A', 'B', 'C'], default=None,
            help='Run only one sub-pass (A=quizzes, B=questions, C=answers). Default: all.',
        )

    def handle(self, *args, **options):
        dry_run    = options['dry_run']
        batch_size = options['batch_size']
        sub_pass   = options['sub_pass']

        run_a = sub_pass in (None, 'A')
        run_b = sub_pass in (None, 'B')
        run_c = sub_pass in (None, 'C')

        if run_a:
            self._pass_a(dry_run, batch_size)
        if run_b:
            self._pass_b(dry_run, batch_size)
        if run_c:
            self._pass_c(dry_run, batch_size * 5)  # answers: larger batches

    # ------------------------------------------------------------------
    # Sub-pass A: Quizzes
    # ------------------------------------------------------------------
    def _pass_a(self, dry_run, batch_size):
        self.stdout.write('--- Sub-pass A: Quizzes ---')
        conn = _wp_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(f"""
                    SELECT p.ID, p.post_title, p.post_parent, p.menu_order
                    FROM {WP_PREFIX}posts p
                    WHERE p.post_type = 'tutor_quiz' AND p.post_status = 'publish'
                    ORDER BY p.post_parent, p.menu_order
                """)
                rows = cur.fetchall()

            if not rows:
                self.stdout.write('No quizzes found.')
                return

            quiz_ids = [r[0] for r in rows]

            # Batch-fetch all postmeta for these quizzes in one query
            with conn.cursor() as cur:
                placeholders = ','.join(['%s'] * len(quiz_ids))
                cur.execute(f"""
                    SELECT post_id, meta_key, meta_value
                    FROM {WP_PREFIX}postmeta
                    WHERE post_id IN ({placeholders})
                      AND meta_key IN ('tutor_quiz_option', '_forbidden_take', '_forbidden_attempt_details')
                """, quiz_ids)
                meta_rows = cur.fetchall()
        finally:
            conn.close()

        # Index meta by post_id → {meta_key: meta_value}
        meta_by_id: dict[int, dict] = {}
        for post_id, meta_key, meta_value in meta_rows:
            meta_by_id.setdefault(post_id, {})[meta_key] = meta_value

        # Preload existing topic map
        topic_map = {t.wp_post_id: t for t in Topic.objects.filter(wp_post_id__isnull=False)}

        self.stdout.write(f'Found {len(rows)} quizzes. dry_run={dry_run}')

        created = updated = skipped = 0
        for i in tqdm(range(0, len(rows), batch_size), desc='Quizzes'):
            batch = rows[i:i + batch_size]
            for wp_id, title, post_parent, menu_order in batch:
                topic = topic_map.get(post_parent)
                if topic is None:
                    skipped += 1
                    logger.warning('Quiz wp_id=%s: topic wp_post_id=%s not found, skipping', wp_id, post_parent)
                    continue

                meta = meta_by_id.get(wp_id, {})

                # Parse phpserialize quiz options
                time_limit = 0
                pass_mark = Decimal('0')
                attempts_allowed = 0
                raw_opts = meta.get('tutor_quiz_option')
                if raw_opts:
                    try:
                        opts = phpserialize.loads(raw_opts.encode('utf-8'), decode_strings=True)
                        time_limit = int(opts.get('time_limit', {}).get('time_value', 0) or 0)
                        pass_mark = _dec(opts.get('passing_grade', '0'))
                        attempts_allowed = int(opts.get('attempts_allowed', 0) or 0)
                    except Exception as exc:
                        logger.warning('Quiz wp_id=%s: failed to parse tutor_quiz_option: %s', wp_id, exc)

                is_locked    = (meta.get('_forbidden_take') == '1')
                hide_results = (meta.get('_forbidden_attempt_details') == '1')

                defaults = dict(
                    topic=topic,
                    title=title or '',
                    time_limit=time_limit or None,
                    pass_mark=pass_mark,
                    attempts_allowed=attempts_allowed,
                    is_locked=is_locked,
                    hide_results=hide_results,
                )
                if not dry_run:
                    _, was_created = Quiz.objects.update_or_create(
                        wp_post_id=wp_id,
                        defaults=defaults,
                    )
                    if was_created:
                        created += 1
                    else:
                        updated += 1
                else:
                    created += 1  # count as "would create"

        verb = 'Would create/update' if dry_run else 'Done'
        self.stdout.write(
            self.style.SUCCESS(
                f'{verb}: {created} created, {updated} updated, {skipped} skipped (no topic)'
            )
        )

    # ------------------------------------------------------------------
    # Sub-pass B: Questions
    # ------------------------------------------------------------------
    def _pass_b(self, dry_run, batch_size):
        self.stdout.write('--- Sub-pass B: Questions ---')
        conn = _wp_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(f"""
                    SELECT question_id, quiz_id, question_title, question_type,
                           question_mark, question_order, question_description
                    FROM {WP_PREFIX}tutor_quiz_questions
                    ORDER BY quiz_id, question_order
                """)
                rows = cur.fetchall()
        finally:
            conn.close()

        # Preload quiz map
        quiz_map = {q.wp_post_id: q for q in Quiz.objects.filter(wp_post_id__isnull=False)}

        self.stdout.write(f'Found {len(rows)} questions. dry_run={dry_run}')

        created = updated = skipped = 0
        for i in tqdm(range(0, len(rows), batch_size), desc='Questions'):
            batch = rows[i:i + batch_size]
            for question_id, quiz_id, title, qtype, mark, order, description in batch:
                quiz = quiz_map.get(quiz_id)
                if quiz is None:
                    skipped += 1
                    logger.warning('Question wp_id=%s: quiz wp_post_id=%s not found, skipping', question_id, quiz_id)
                    continue

                defaults = dict(
                    quiz=quiz,
                    text=title or '',
                    question_type=TYPE_MAP.get(qtype or '', 'open'),
                    mark=_dec(mark, '1'),
                    order=order or 0,
                    explanation=description or '',
                )
                if not dry_run:
                    _, was_created = Question.objects.update_or_create(
                        wp_question_id=question_id,
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
                f'{verb}: {created} created, {updated} updated, {skipped} skipped (no quiz)'
            )
        )

    # ------------------------------------------------------------------
    # Sub-pass C: Answer Choices
    # ------------------------------------------------------------------
    def _pass_c(self, dry_run, batch_size):
        self.stdout.write('--- Sub-pass C: Answer Choices ---')
        conn = _wp_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(f"""
                    SELECT answer_id, belongs_question_id, answer_title, is_correct, answer_order
                    FROM {WP_PREFIX}tutor_quiz_question_answers
                    ORDER BY belongs_question_id, answer_order
                """)
                rows = cur.fetchall()
        finally:
            conn.close()

        # Preload question map
        question_map = {q.wp_question_id: q for q in Question.objects.filter(wp_question_id__isnull=False)}

        self.stdout.write(f'Found {len(rows)} answer choices. dry_run={dry_run}')

        created = updated = skipped = 0
        for i in tqdm(range(0, len(rows), batch_size), desc='AnswerChoices'):
            batch = rows[i:i + batch_size]
            for answer_id, question_id, answer_title, is_correct, answer_order in batch:
                question = question_map.get(question_id)
                if question is None:
                    skipped += 1
                    continue

                defaults = dict(
                    question=question,
                    text=answer_title or '',
                    is_correct=bool(int(is_correct or 0)),
                    order=answer_order or 0,
                )
                if not dry_run:
                    _, was_created = AnswerChoice.objects.update_or_create(
                        wp_answer_id=answer_id,
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
                f'{verb}: {created} created, {updated} updated, {skipped} skipped (no question)'
            )
        )
