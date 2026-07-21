"""
ETL Pass 7 — Coupons + Wallet Transactions.

Sub-pass A: Coupons from 29_posts WHERE post_type='shop_coupon' + 29_postmeta
Sub-pass B: CouponRedemptions + WalletTransactions from 29_coupon_redemptions

Run:
    python manage.py etl_pass_7_wallet --dry-run
    python manage.py etl_pass_7_wallet --batch-size 500
"""
import datetime
import logging
from decimal import Decimal, InvalidOperation

import pymysql
from decouple import config
from django.core.management.base import BaseCommand
from django.utils.timezone import make_aware
from tqdm import tqdm

from apps.commerce.models import Coupon, CouponRedemption, WalletTransaction
from apps.users.models import User

logger = logging.getLogger(__name__)

WP_PREFIX = '29_'


class Command(BaseCommand):
    help = 'ETL Pass 7: migrate coupons and wallet transactions'

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
                    SELECT p.ID, p.post_title AS code, p.post_status
                    FROM {WP_PREFIX}posts p
                    WHERE p.post_type = 'shop_coupon' AND p.post_status = 'publish'
                    ORDER BY p.ID
                """)
                coupon_rows = cur.fetchall()

                # Batch fetch all relevant postmeta in one query
                coupon_meta = {}
                if coupon_rows:
                    coupon_ids   = [r[0] for r in coupon_rows]
                    placeholders = ','.join(['%s'] * len(coupon_ids))
                    cur.execute(f"""
                        SELECT post_id, meta_key, meta_value
                        FROM {WP_PREFIX}postmeta
                        WHERE post_id IN ({placeholders})
                          AND meta_key IN ('coupon_amount', 'usage_limit', 'date_expires', 'discount_type')
                    """, coupon_ids)
                    for post_id, meta_key, meta_value in cur.fetchall():
                        coupon_meta.setdefault(post_id, {})[meta_key] = meta_value

                cur.execute(f"""
                    SELECT cr.id, cr.user_id, cr.coupon_code, cr.amount, cr.date_redeemed
                    FROM {WP_PREFIX}coupon_redemptions cr
                    ORDER BY cr.id
                """)
                redemption_rows = cur.fetchall()
        finally:
            wp_conn.close()

        self.stdout.write(
            f'Found {len(coupon_rows)} coupons, {len(redemption_rows)} redemptions. dry_run={dry_run}'
        )

        if dry_run:
            self.stdout.write(f'[dry-run] Sub-pass A: would process {len(coupon_rows)} coupons')
            self.stdout.write(f'[dry-run] Sub-pass B: would process {len(redemption_rows)} redemptions')
            return

        # ── Sub-pass A: Coupons ───────────────────────────────────────────
        self.stdout.write('\n--- Sub-pass A: Coupons ---')
        coupon_created = 0

        for wp_id, code, _ in tqdm(coupon_rows, desc='Coupons'):
            meta = coupon_meta.get(wp_id, {})

            try:
                amount = Decimal(str(meta.get('coupon_amount', '0') or '0'))
            except InvalidOperation:
                amount = Decimal('0')

            try:
                usage_limit = int(meta.get('usage_limit', 1) or 1)
            except (ValueError, TypeError):
                usage_limit = 1

            expires_at  = None
            expires_raw = meta.get('date_expires', '0') or '0'
            try:
                ts = int(expires_raw)
                if ts > 0:
                    expires_at = make_aware(datetime.datetime.fromtimestamp(ts))
            except (ValueError, TypeError, OSError):
                pass

            discount_type = meta.get('discount_type', 'fixed_cart')
            coupon_type   = 'wallet_recharge' if discount_type == 'fixed_cart' else 'course_discount'

            _, created = Coupon.objects.update_or_create(
                code=str(code or '').upper(),
                defaults={
                    'coupon_type': coupon_type,
                    'amount':      amount,
                    'usage_limit': usage_limit,
                    'expires_at':  expires_at,
                    'created_by':  None,
                    'is_active':   True,
                },
            )
            if created:
                coupon_created += 1

        self.stdout.write(self.style.SUCCESS(f'Sub-pass A done. Created {coupon_created} coupons.'))

        # ── Sub-pass B: Redemptions + Wallet Transactions ─────────────────
        self.stdout.write('\n--- Sub-pass B: Coupon Redemptions + Wallet Transactions ---')

        user_cache   = {u.wp_user_id: u for u in User.objects.filter(wp_user_id__isnull=False)}
        coupon_cache = {c.code: c for c in Coupon.objects.all()}

        redemption_created = 0
        tx_created         = 0

        for row in tqdm(redemption_rows, desc='Redemptions'):
            cr_id, user_id, coupon_code, amount, _ = row

            user = user_cache.get(user_id)
            if not user:
                skipped.append((cr_id, user_id, 'user not found'))
                continue

            coupon_key = str(coupon_code or '').upper()
            coupon     = coupon_cache.get(coupon_key)
            if not coupon:
                skipped.append((cr_id, coupon_code, 'coupon not found'))
                continue

            try:
                amount_dec = Decimal(str(amount or '0'))
            except InvalidOperation:
                amount_dec = Decimal('0')

            _, created = CouponRedemption.objects.get_or_create(
                user=user,
                coupon=coupon,
                defaults={'amount': amount_dec},
            )
            if created:
                redemption_created += 1

            _, created = WalletTransaction.objects.get_or_create(
                user=user,
                reference=f'coupon_{coupon_code}',
                defaults={
                    'amount':        amount_dec,
                    'type':          'credit',
                    'balance_after': user.wallet_balance,  # set in Pass 1
                    'note':          f'استرداد كوبون: {coupon_code}',
                },
            )
            if created:
                tx_created += 1

        self.stdout.write(self.style.SUCCESS(
            f'Sub-pass B done. Redemptions: +{redemption_created}, Wallet txns: +{tx_created}.'
        ))

        if skipped:
            with open('etl_skipped_wallet.log', 'w', encoding='utf-8') as f:
                for a, b, reason in skipped:
                    f.write(f'{a}\t{b}\t{reason}\n')

        self.stdout.write(
            self.style.SUCCESS(
                f'\nPass 7 complete. Coupons: +{coupon_created}, '
                f'Redemptions: +{redemption_created}, '
                f'Wallet txns: +{tx_created}, '
                f'Skipped: {len(skipped)} (see etl_skipped_wallet.log)'
            )
        )
