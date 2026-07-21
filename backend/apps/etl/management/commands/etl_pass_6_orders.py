"""
ETL Pass 6 — Tutor Orders + Enrollments → Django Order, OrderItem, Enrollment.

Sub-pass A: Orders + OrderItems  (29_tutor_orders, 29_tutor_order_items)
Sub-pass B: Enrollments from completed orders
Sub-pass C: Legacy enrollments   (29_posts WHERE post_type='tutor_enrolled')

Run:
    python manage.py etl_pass_6_orders --dry-run
    python manage.py etl_pass_6_orders --batch-size 500
"""
import logging
from decimal import Decimal, InvalidOperation

import pymysql
from decouple import config
from django.core.management.base import BaseCommand
from tqdm import tqdm

from apps.commerce.models import Order, OrderItem
from apps.courses.models import Course, Enrollment
from apps.users.models import User

logger = logging.getLogger(__name__)

WP_PREFIX = '29_'

PAYMENT_MAP = {
    'kanga_pay': 'kanga_pay',
    'kanga-pay': 'kanga_pay',
    'wallet':    'wallet',
    'free':      'wallet',   # free orders → wallet with 0 price
}

STATUS_MAP = {
    'completed': 'completed',
    'cancelled': 'cancelled',
    'pending':   'pending',
    'refunded':  'refunded',
    'failed':    'failed',
}


class Command(BaseCommand):
    help = 'ETL Pass 6: migrate Tutor orders and enrollments'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Preview only — no DB writes')
        parser.add_argument('--batch-size', type=int, default=500)

    def handle(self, *args, **options):
        dry_run    = options['dry_run']
        batch_size = options['batch_size']  # noqa: F841 — kept for API consistency
        skipped    = []

        wp_conn = pymysql.connect(
            host=config('WP_DB_HOST'),
            port=int(config('WP_DB_PORT', default='3306')),
            db=config('WP_DB_NAME'),
            user=config('WP_DB_USER'),
            password=config('WP_DB_PASSWORD'),
            charset='utf8mb4',
        )

        try:
            with wp_conn.cursor() as cur:
                cur.execute(f"""
                    SELECT o.id, o.user_id, o.payment_method, o.payment_status,
                           o.total_price, o.transaction_id, o.created_at
                    FROM {WP_PREFIX}tutor_orders o
                    ORDER BY o.id
                """)
                order_rows = cur.fetchall()

                # Fetch all order items in one shot to avoid N+1
                item_rows = []
                if order_rows:
                    order_ids    = [r[0] for r in order_rows]
                    placeholders = ','.join(['%s'] * len(order_ids))
                    cur.execute(f"""
                        SELECT oi.id, oi.order_id, oi.item_id AS course_wp_id, oi.regular_price
                        FROM {WP_PREFIX}tutor_order_items oi
                        WHERE oi.order_id IN ({placeholders})
                    """, order_ids)
                    item_rows = cur.fetchall()

                cur.execute(f"""
                    SELECT p.ID, p.post_author AS user_id, p.post_parent AS course_wp_id,
                           p.post_date AS enrolled_at
                    FROM {WP_PREFIX}posts p
                    WHERE p.post_type = 'tutor_enrolled' AND p.post_status = 'completed'
                    ORDER BY p.ID
                """)
                legacy_rows = cur.fetchall()
        finally:
            wp_conn.close()

        self.stdout.write(
            f'Found {len(order_rows)} orders, {len(item_rows)} items, '
            f'{len(legacy_rows)} legacy enrollments. dry_run={dry_run}'
        )

        if dry_run:
            self.stdout.write(f'[dry-run] Sub-pass A: would process {len(order_rows)} orders + {len(item_rows)} items')
            self.stdout.write('[dry-run] Sub-pass B: would create enrollments from completed orders')
            self.stdout.write(f'[dry-run] Sub-pass C: would process {len(legacy_rows)} legacy enrollments')
            return

        # Build items lookup: order_id → [(course_wp_id, price), ...]
        items_by_order = {}
        for _, order_id, course_wp_id, price in item_rows:
            items_by_order.setdefault(order_id, []).append((course_wp_id, price))

        # Cache both lookups once — avoids per-row queries
        user_cache   = {u.wp_user_id: u for u in User.objects.filter(wp_user_id__isnull=False)}
        course_cache = {c.wp_post_id: c for c in Course.objects.filter(wp_post_id__isnull=False)}

        # ── Sub-pass A: Orders + OrderItems ──────────────────────────────
        self.stdout.write('\n--- Sub-pass A: Orders + OrderItems ---')
        created_orders = 0

        for row in tqdm(order_rows, desc='Orders'):
            wp_id, user_id, payment_method, payment_status, total_price, transaction_id, _ = row

            user = user_cache.get(user_id)
            if not user:
                skipped.append((wp_id, user_id, 'user not found'))
                continue

            try:
                price_dec = Decimal(str(total_price or '0'))
            except InvalidOperation:
                price_dec = Decimal('0')

            payment = PAYMENT_MAP.get(str(payment_method or '').lower(), 'wallet')
            status  = STATUS_MAP.get(str(payment_status or '').lower(), 'pending')

            order, created = Order.objects.update_or_create(
                wp_order_id=wp_id,
                defaults={
                    'user':           user,
                    'status':         status,
                    'payment_method': payment,
                    'transaction_id': str(transaction_id or ''),
                    'total_price':    price_dec,
                },
            )
            if created:
                created_orders += 1

            for course_wp_id, item_price in items_by_order.get(wp_id, []):
                course = course_cache.get(course_wp_id)
                if not course:
                    skipped.append((wp_id, course_wp_id, f'course wp_id={course_wp_id} not found'))
                    continue
                try:
                    item_price_dec = Decimal(str(item_price or '0'))
                except InvalidOperation:
                    item_price_dec = Decimal('0')
                OrderItem.objects.get_or_create(
                    order=order,
                    course=course,
                    defaults={'price': item_price_dec},
                )

        self.stdout.write(self.style.SUCCESS(f'Sub-pass A done. Created {created_orders} new orders.'))

        # ── Sub-pass B: Enrollments from completed orders ─────────────────
        self.stdout.write('\n--- Sub-pass B: Enrollments from completed orders ---')
        enroll_b = 0
        completed_qs = (
            Order.objects
            .filter(status='completed', wp_order_id__isnull=False)
            .select_related('user')
        )
        for order in tqdm(completed_qs, desc='Enrollments from orders'):
            for item in order.items.select_related('course').all():
                _, created = Enrollment.objects.get_or_create(
                    student=order.user,
                    course=item.course,
                    defaults={
                        'status':         'active',
                        'payment_method': order.payment_method,
                        'order':          order,
                    },
                )
                if created:
                    enroll_b += 1

        self.stdout.write(self.style.SUCCESS(f'Sub-pass B done. Created {enroll_b} enrollments.'))

        # ── Sub-pass C: Legacy tutor_enrolled posts ───────────────────────
        self.stdout.write('\n--- Sub-pass C: Legacy tutor_enrolled posts ---')
        enroll_c = 0

        for row in tqdm(legacy_rows, desc='Legacy enrollments'):
            wp_post_id, user_id, course_wp_id, _ = row

            user = user_cache.get(user_id)
            if not user:
                skipped.append((wp_post_id, user_id, 'legacy: user not found'))
                continue

            course = course_cache.get(course_wp_id)
            if not course:
                skipped.append((wp_post_id, course_wp_id, f'legacy: course wp_id={course_wp_id} not found'))
                continue

            _, created = Enrollment.objects.get_or_create(
                student=user,
                course=course,
                defaults={
                    'status':         'active',
                    'payment_method': 'manual',
                    'order':          None,
                },
            )
            if created:
                enroll_c += 1

        self.stdout.write(self.style.SUCCESS(f'Sub-pass C done. Created {enroll_c} legacy enrollments.'))

        if skipped:
            with open('etl_skipped_orders.log', 'w', encoding='utf-8') as f:
                for a, b, reason in skipped:
                    f.write(f'{a}\t{b}\t{reason}\n')

        self.stdout.write(
            self.style.SUCCESS(
                f'\nPass 6 complete. Orders: +{created_orders}, '
                f'Enrollments: +{enroll_b + enroll_c} '
                f'({enroll_b} from orders, {enroll_c} legacy), '
                f'Skipped: {len(skipped)} (see etl_skipped_orders.log)'
            )
        )
