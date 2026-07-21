"""
ETL Pass 2 — WordPress course categories → Django Category model.

Sources: 29_terms JOIN 29_term_taxonomy WHERE taxonomy='course-category'
Target:  apps.courses.Category

Two-pass strategy:
  1. Upsert all categories with parent=None
  2. Wire parent FKs by resolving parent term_id → slug → Category

Run:
    python manage.py etl_pass_2_categories --dry-run
    python manage.py etl_pass_2_categories --batch-size 200
"""
import logging

import pymysql
from decouple import config
from django.core.management.base import BaseCommand
from tqdm import tqdm

from apps.courses.models import Category

logger = logging.getLogger(__name__)

WP_PREFIX = '29_'


def _infer_student_type(name: str) -> str:
    n = name.lower()
    if 'أونلاين' in name or 'online' in n:
        return 'online'
    if 'سنتر' in name or 'center' in n:
        return 'center'
    return ''


def _infer_academic_year(name: str) -> str:
    n = name.lower()
    if 'أول' in name or 'first' in n:
        return '1st'
    if 'ثاني' in name or 'second' in n:
        return '2nd'
    if 'ثالث' in name or 'third' in n:
        return '3rd'
    return ''


class Command(BaseCommand):
    help = 'ETL Pass 2: migrate WordPress course categories to Django Category model'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Preview only — no DB writes')
        parser.add_argument('--batch-size', type=int, default=500)

    def handle(self, *args, **options):
        dry_run = options['dry_run']

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
            with wp_conn.cursor() as cur:
                cur.execute(f"""
                    SELECT t.term_id, t.name, t.slug, t.term_order,
                           tt.parent AS parent_term_id, tt.count
                    FROM {WP_PREFIX}terms t
                    JOIN {WP_PREFIX}term_taxonomy tt ON tt.term_id = t.term_id
                    WHERE tt.taxonomy = 'course-category'
                    ORDER BY t.term_id
                """)
                rows = cur.fetchall()
        finally:
            wp_conn.close()

        self.stdout.write(f'Found {len(rows)} WP course categories. dry_run={dry_run}')

        if dry_run:
            self.stdout.write(f'[dry-run] Would upsert {len(rows)} categories (2-pass: create then set parents)')
            for term_id, name, slug, term_order, parent_term_id, count in rows[:10]:
                self.stdout.write(
                    f'  term_id={term_id} slug={slug!r} name={name!r} '
                    f'parent_term_id={parent_term_id} '
                    f'student_type={_infer_student_type(name)!r} '
                    f'academic_year={_infer_academic_year(name)!r}'
                )
            return

        # Pass 1: upsert all categories without parent
        term_id_to_slug = {}
        for row in tqdm(rows, desc='Pass 1 — upsert categories'):
            term_id, name, slug, term_order, parent_term_id, count = row
            slug = slug or f'cat-{term_id}'
            term_id_to_slug[term_id] = slug
            try:
                Category.objects.update_or_create(
                    slug=slug,
                    defaults={
                        'name': name,
                        'order': term_order or 0,
                        'student_type': _infer_student_type(name),
                        'academic_year': _infer_academic_year(name),
                        'parent': None,
                    },
                )
            except Exception as e:
                skipped.append((term_id, slug, str(e)))

        # Pass 2: wire up parent FKs
        for row in tqdm(rows, desc='Pass 2 — set parents'):
            term_id, name, slug, term_order, parent_term_id, count = row
            if not parent_term_id:
                continue
            slug = slug or f'cat-{term_id}'
            parent_slug = term_id_to_slug.get(parent_term_id)
            if not parent_slug:
                skipped.append((term_id, slug, f'parent term_id={parent_term_id} not in result set'))
                continue
            parent_obj = Category.objects.filter(slug=parent_slug).first()
            if not parent_obj:
                skipped.append((term_id, slug, f'parent slug={parent_slug!r} not found in DB'))
                continue
            Category.objects.filter(slug=slug).update(parent=parent_obj)

        if skipped:
            with open('etl_skipped_categories.log', 'w', encoding='utf-8') as f:
                for term_id, slug, reason in skipped:
                    f.write(f'{term_id}\t{slug}\t{reason}\n')

        self.stdout.write(
            self.style.SUCCESS(
                f'Done. Upserted {len(rows)} categories, skipped {len(skipped)} '
                f'(see etl_skipped_categories.log)'
            )
        )
