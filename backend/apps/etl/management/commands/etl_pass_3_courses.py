"""
ETL Pass 3 — WordPress courses/topics/lessons → Django Course/Topic/Lesson models.

Sources:
  - 29_posts WHERE post_type IN ('courses','topics','lesson') AND post_status='publish'
  - 29_postmeta for price and _video meta
  - 29_term_relationships + 29_term_taxonomy for category assignment

Sub-passes (--subpass flag):
  courses  → 29_posts(courses) → Course
  topics   → 29_posts(topics)  → Topic
  lessons  → 29_posts(lesson)  → Lesson
  all      → courses → topics → lessons in sequence (default)

Run:
    python manage.py etl_pass_3_courses --dry-run
    python manage.py etl_pass_3_courses --subpass courses
    python manage.py etl_pass_3_courses --subpass topics --batch-size 100
    python manage.py etl_pass_3_courses --subpass all
"""
import logging
import re
from decimal import Decimal, InvalidOperation

import phpserialize
import pymysql
from decouple import config
from django.core.management.base import BaseCommand
from tqdm import tqdm

from apps.courses.models import Category, Course, Lesson, Topic
from apps.users.models import User

logger = logging.getLogger(__name__)

WP_PREFIX = '29_'


def _clean_slug(post_name: str, wp_id: int) -> str:
    """Sanitise WP post_name into a valid Django slug, max 50 chars."""
    slug = re.sub(r'[^\w-]', '-', (post_name or '').lower()).strip('-')
    slug = re.sub(r'-+', '-', slug) or f'course-{wp_id}'
    return slug[:50]


class Command(BaseCommand):
    help = 'ETL Pass 3: migrate WordPress courses, topics, and lessons'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Preview only — no DB writes')
        parser.add_argument('--batch-size', type=int, default=200)
        parser.add_argument(
            '--subpass',
            choices=['courses', 'topics', 'lessons', 'all'],
            default='all',
            help='Which sub-pass to run (default: all)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        subpass = options['subpass']

        wp_conn = pymysql.connect(
            host=config('WP_DB_HOST'),
            port=int(config('WP_DB_PORT', default='3306')),
            db=config('WP_DB_NAME'),
            user=config('WP_DB_USER'),
            password=config('WP_DB_PASSWORD'),
            charset='utf8mb4',
        )
        skipped = []

        try:
            if subpass in ('courses', 'all'):
                self._migrate_courses(wp_conn, options, skipped)
            if subpass in ('topics', 'all'):
                self._migrate_topics(wp_conn, options, skipped)
            if subpass in ('lessons', 'all'):
                self._migrate_lessons(wp_conn, options, skipped)
        finally:
            wp_conn.close()

        if skipped:
            with open('etl_skipped_courses.log', 'w', encoding='utf-8') as f:
                for wp_id, title, reason in skipped:
                    f.write(f'{wp_id}\t{title}\t{reason}\n')
            self.stdout.write(f'Total skipped: {len(skipped)} — see etl_skipped_courses.log')
        else:
            self.stdout.write(self.style.SUCCESS('All items migrated with no skips.'))

    # ------------------------------------------------------------------ #
    # Sub-pass A: Courses                                                  #
    # ------------------------------------------------------------------ #
    def _migrate_courses(self, wp_conn, options, skipped):
        dry_run = options['dry_run']

        with wp_conn.cursor() as cur:
            cur.execute(f"""
                SELECT p.ID, p.post_title, p.post_content, p.post_name,
                       p.post_author, p.menu_order
                FROM {WP_PREFIX}posts p
                WHERE p.post_type = 'courses' AND p.post_status = 'publish'
                ORDER BY p.ID
            """)
            courses = cur.fetchall()

        if not courses:
            self.stdout.write('No published courses found.')
            return

        course_ids = [r[0] for r in courses]

        # Batch fetch prices — one query for all course IDs
        price_map = {}
        with wp_conn.cursor() as cur:
            fmt = ','.join(['%s'] * len(course_ids))
            cur.execute(
                f"SELECT post_id, meta_value FROM {WP_PREFIX}postmeta "
                f"WHERE post_id IN ({fmt}) AND meta_key = 'tutor_course_price'",
                course_ids,
            )
            for post_id, meta_value in cur.fetchall():
                price_map[post_id] = meta_value

        # Batch fetch category assignments
        cat_map = {}  # course_id → category slug (last one wins; a course can have multiple cats)
        with wp_conn.cursor() as cur:
            fmt = ','.join(['%s'] * len(course_ids))
            cur.execute(
                f"""
                SELECT tr.object_id, t.slug
                FROM {WP_PREFIX}term_relationships tr
                JOIN {WP_PREFIX}term_taxonomy tt
                  ON tt.term_taxonomy_id = tr.term_taxonomy_id
                JOIN {WP_PREFIX}terms t ON t.term_id = tt.term_id
                WHERE tr.object_id IN ({fmt}) AND tt.taxonomy = 'course-category'
                """,
                course_ids,
            )
            for obj_id, slug in cur.fetchall():
                cat_map[obj_id] = slug

        self.stdout.write(f'Found {len(courses)} published courses. dry_run={dry_run}')

        if dry_run:
            self.stdout.write(f'[dry-run] Would upsert {len(courses)} courses')
            return

        for row in tqdm(courses, desc='Courses'):
            wp_id, post_title, post_content, post_name, post_author, menu_order = row

            instructor = User.objects.filter(wp_user_id=post_author).first()
            if not instructor:
                skipped.append((wp_id, post_title, f'instructor wp_user_id={post_author} not found'))
                continue

            slug = _clean_slug(post_name, wp_id)
            # Guard slug uniqueness collision across different wp_post_ids
            if Course.objects.filter(slug=slug).exclude(wp_post_id=wp_id).exists():
                slug = f'{slug[:45]}-{wp_id}'

            try:
                price = Decimal(price_map.get(wp_id) or '0')
            except InvalidOperation:
                price = Decimal('0')

            cat_slug = cat_map.get(wp_id)
            category = Category.objects.filter(slug=cat_slug).first() if cat_slug else None

            try:
                Course.objects.update_or_create(
                    wp_post_id=wp_id,
                    defaults={
                        'title':        post_title or '',
                        'slug':         slug,
                        'description':  post_content or '',
                        'instructor':   instructor,
                        'category':     category,
                        'price':        price,
                        'is_published': True,
                    },
                )
            except Exception as e:
                skipped.append((wp_id, post_title, str(e)))

        self.stdout.write(self.style.SUCCESS(f'Courses done. Running skip count: {len(skipped)}'))

    # ------------------------------------------------------------------ #
    # Sub-pass B: Topics                                                   #
    # ------------------------------------------------------------------ #
    def _migrate_topics(self, wp_conn, options, skipped):
        dry_run = options['dry_run']

        with wp_conn.cursor() as cur:
            cur.execute(f"""
                SELECT p.ID, p.post_title, p.post_parent, p.menu_order
                FROM {WP_PREFIX}posts p
                WHERE p.post_type = 'topics' AND p.post_status = 'publish'
                ORDER BY p.post_parent, p.menu_order
            """)
            rows = cur.fetchall()

        self.stdout.write(f'Found {len(rows)} published topics. dry_run={dry_run}')

        if dry_run:
            self.stdout.write(f'[dry-run] Would upsert {len(rows)} topics')
            return

        for row in tqdm(rows, desc='Topics'):
            wp_id, post_title, post_parent, menu_order = row
            course = Course.objects.filter(wp_post_id=post_parent).first()
            if not course:
                skipped.append((wp_id, post_title, f'course wp_post_id={post_parent} not found'))
                continue
            try:
                Topic.objects.update_or_create(
                    wp_post_id=wp_id,
                    defaults={
                        'title':  post_title or '',
                        'course': course,
                        'order':  menu_order or 0,
                    },
                )
            except Exception as e:
                skipped.append((wp_id, post_title, str(e)))

        self.stdout.write(self.style.SUCCESS(f'Topics done. Running skip count: {len(skipped)}'))

    # ------------------------------------------------------------------ #
    # Sub-pass C: Lessons                                                  #
    # ------------------------------------------------------------------ #
    def _migrate_lessons(self, wp_conn, options, skipped):
        dry_run = options['dry_run']

        with wp_conn.cursor() as cur:
            cur.execute(f"""
                SELECT p.ID, p.post_title, p.post_parent, p.menu_order
                FROM {WP_PREFIX}posts p
                WHERE p.post_type = 'lesson' AND p.post_status = 'publish'
                ORDER BY p.post_parent, p.menu_order
            """)
            rows = cur.fetchall()

        if not rows:
            self.stdout.write('No published lessons found.')
            return

        lesson_ids = [r[0] for r in rows]

        # Batch fetch _video postmeta — chunked at 1000 to stay under MySQL IN() limits
        # ponytail: 1000-row chunks; raise limit if MariaDB complains about packet size
        video_meta = {}
        with wp_conn.cursor() as cur:
            for i in range(0, len(lesson_ids), 1000):
                chunk = lesson_ids[i:i + 1000]
                fmt = ','.join(['%s'] * len(chunk))
                cur.execute(
                    f"SELECT post_id, meta_value FROM {WP_PREFIX}postmeta "
                    f"WHERE post_id IN ({fmt}) AND meta_key = '_video'",
                    chunk,
                )
                for post_id, meta_value in cur.fetchall():
                    video_meta[post_id] = meta_value

        self.stdout.write(f'Found {len(rows)} published lessons. dry_run={dry_run}')

        if dry_run:
            self.stdout.write(f'[dry-run] Would upsert {len(rows)} lessons')
            return

        for row in tqdm(rows, desc='Lessons'):
            wp_id, post_title, post_parent, menu_order = row
            topic = Topic.objects.filter(wp_post_id=post_parent).first()
            if not topic:
                skipped.append((wp_id, post_title, f'topic wp_post_id={post_parent} not found'))
                continue

            # Deserialise PHP-serialised video meta
            raw = video_meta.get(wp_id, '')
            if raw:
                try:
                    data = phpserialize.loads(raw.encode('utf-8'), decode_strings=True)
                    source = data.get('source', 'youtube')
                    yt_id  = data.get('source_video_id') or data.get('source_youtube_id', '')
                except Exception:
                    source, yt_id = 'youtube', ''
            else:
                source, yt_id = 'youtube', ''

            video_source = 'self_hosted' if source == 'html5' else 'youtube'

            try:
                Lesson.objects.update_or_create(
                    wp_post_id=wp_id,
                    defaults={
                        'title':        post_title or '',
                        'topic':        topic,
                        'order':        menu_order or 0,
                        'video_source': video_source,
                        'youtube_id':   yt_id or '',
                    },
                )
            except Exception as e:
                skipped.append((wp_id, post_title, str(e)))

        self.stdout.write(self.style.SUCCESS(f'Lessons done. Running skip count: {len(skipped)}'))
