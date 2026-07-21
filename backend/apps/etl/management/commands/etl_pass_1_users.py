"""
ETL Pass 1 — WordPress users → Django User model.

Sources: 29_users JOIN 29_usermeta
Target:  apps.users.User

Run:
    python manage.py etl_pass_1_users --dry-run
    python manage.py etl_pass_1_users --batch-size 500
"""
import logging
from decimal import Decimal, InvalidOperation

import pymysql
from decouple import config
from django.core.management.base import BaseCommand
from tqdm import tqdm

from apps.users.models import User

logger = logging.getLogger(__name__)

WP_PREFIX = '29_'

ACADEMIC_YEAR_MAP = {
    'first_secondary':  '1st',
    'second_secondary': '2nd',
    'third_secondary':  '3rd',
}

# WordPress capability → Django role
def _role_from_capabilities(caps_str: str) -> str:
    if 'administrator' in caps_str:
        return 'admin'
    if 'tutor_instructor' in caps_str:
        return 'instructor'
    return 'student'

def _normalize_phone(raw: str) -> str:
    digits = ''.join(c for c in (raw or '') if c.isdigit())
    if digits.startswith('0'):
        digits = '2' + digits
    if not digits.startswith('20'):
        digits = '20' + digits
    return digits


class Command(BaseCommand):
    help = 'ETL Pass 1: migrate WordPress users to Django User model'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Preview only — no DB writes')
        parser.add_argument('--batch-size', type=int, default=500)

    def handle(self, *args, **options):
        dry_run    = options['dry_run']
        batch_size = options['batch_size']

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
                # Pull all users + their relevant meta in one query
                cur.execute(f"""
                    SELECT
                        u.ID,
                        u.user_login,
                        u.user_pass,
                        u.display_name,
                        u.user_registered,
                        MAX(CASE WHEN m.meta_key = 'student_type'       THEN m.meta_value END) AS student_type,
                        MAX(CASE WHEN m.meta_key = 'academic_year'      THEN m.meta_value END) AS academic_year,
                        MAX(CASE WHEN m.meta_key = 'billing_company'    THEN m.meta_value END) AS guardian_phone,
                        MAX(CASE WHEN m.meta_key = '_user_balance'      THEN m.meta_value END) AS wallet_balance,
                        MAX(CASE WHEN m.meta_key = '{WP_PREFIX}capabilities' THEN m.meta_value END) AS capabilities
                    FROM {WP_PREFIX}users u
                    LEFT JOIN {WP_PREFIX}usermeta m ON m.user_id = u.ID
                    GROUP BY u.ID, u.user_login, u.user_pass, u.display_name, u.user_registered
                    ORDER BY u.ID
                """)
                rows = cur.fetchall()
        finally:
            wp_conn.close()

        self.stdout.write(f'Found {len(rows)} WordPress users. dry_run={dry_run}')

        # Build User objects
        to_create = []
        existing_wp_ids = set(User.objects.values_list('wp_user_id', flat=True))

        for row in tqdm(rows, desc='Transforming users'):
            (wp_id, login, wp_pass, display_name, registered,
             student_type, academic_year, guardian_phone, wallet_raw, caps) = row

            if wp_id in existing_wp_ids:
                continue  # already migrated

            phone = _normalize_phone(login)
            if not phone or len(phone) < 12:
                skipped.append((wp_id, login, 'invalid phone'))
                continue

            # split display_name on first space
            parts      = (display_name or '').strip().split(' ', 1)
            first_name = parts[0] or 'مجهول'
            last_name  = parts[1] if len(parts) > 1 else ''

            try:
                balance = Decimal(wallet_raw or '0')
            except InvalidOperation:
                balance = Decimal('0')

            # phpass hash stored as-is; PhpassPasswordHasher verifies it on login
            password_encoded = f'phpass$${wp_pass[3:]}' if (wp_pass or '').startswith('$P$') else ''

            user = User(
                phone          = phone,
                first_name     = first_name,
                last_name      = last_name,
                guardian_phone = _normalize_phone(guardian_phone or ''),
                student_type   = student_type or '',
                academic_year  = ACADEMIC_YEAR_MAP.get(academic_year or '', ''),
                wallet_balance = balance,
                role           = _role_from_capabilities(caps or ''),
                is_active      = True,
                wp_user_id     = wp_id,
            )
            if password_encoded:
                user.password = password_encoded
            else:
                user.set_unusable_password()

            to_create.append(user)

        if dry_run:
            self.stdout.write(f'[dry-run] Would create {len(to_create)} users, skip {len(skipped)}')
            for wp_id, login, reason in skipped[:10]:
                self.stdout.write(f'  SKIP wp_id={wp_id} login={login} reason={reason}')
            return

        # Bulk insert in batches
        created_count = 0
        for i in tqdm(range(0, len(to_create), batch_size), desc='Inserting batches'):
            batch = to_create[i:i + batch_size]
            User.objects.bulk_create(batch, ignore_conflicts=True)
            created_count += len(batch)

        # Log skipped
        if skipped:
            with open('etl_skipped_users.log', 'w', encoding='utf-8') as f:
                for wp_id, login, reason in skipped:
                    f.write(f'{wp_id}\t{login}\t{reason}\n')

        self.stdout.write(
            self.style.SUCCESS(
                f'Done. Created ≈{created_count} users, skipped {len(skipped)} '
                f'(see etl_skipped_users.log)'
            )
        )
