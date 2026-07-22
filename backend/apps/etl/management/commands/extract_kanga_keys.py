"""
Extract Kanga Pay API keys from the WordPress options table.

Run:
    python manage.py extract_kanga_keys

Prints the public key and secret key so you can paste them into your
.env file. Run this BEFORE shutting down WordPress. There is no
separate webhook secret in the real Kanga Pay API - webhook requests
are verified with the same public/secret key pair (see
apps.commerce.services.verify_kanga_signature).
"""
import phpserialize
import pymysql
from decouple import config
from django.core.management.base import BaseCommand

WP_PREFIX = '29_'


class Command(BaseCommand):
    help = 'Extract Kanga Pay keys from WordPress 29_options table'

    def handle(self, *args, **options):
        conn = pymysql.connect(
            host=config('WP_DB_HOST'),
            port=int(config('WP_DB_PORT', default='3306')),
            db=config('WP_DB_NAME'),
            user=config('WP_DB_USER'),
            password=config('WP_DB_PASSWORD'),
            charset='utf8mb4',
        )
        try:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT option_value FROM {WP_PREFIX}options "
                    f"WHERE option_name = 'woocommerce_kanga_pay_settings' LIMIT 1"
                )
                row = cur.fetchone()
        finally:
            conn.close()

        if not row:
            self.stderr.write(self.style.ERROR(
                'woocommerce_kanga_pay_settings not found in 29_options. '
                'Make sure the WP DB is imported and the prefix is 29_.'
            ))
            return

        raw = row[0]
        try:
            data = phpserialize.loads(raw.encode('utf-8'), decode_strings=True)
        except Exception as exc:
            self.stderr.write(self.style.ERROR(f'Failed to parse PHP serialized value: {exc}'))
            self.stdout.write(f'Raw value:\n{raw}')
            return

        # Kanga Pay stores keys under different field names depending on version.
        # Try the most common ones.
        public_key  = data.get('public_key') or data.get('api_key') or data.get('publishable_key', '')
        secret_key  = data.get('secret_key') or data.get('private_key') or data.get('api_secret', '')

        self.stdout.write('\n' + '=' * 50)
        self.stdout.write(self.style.SUCCESS('Kanga Pay settings found:'))
        self.stdout.write('=' * 50)
        self.stdout.write(f'\nAll raw keys in the settings:\n')
        for k, v in data.items():
            self.stdout.write(f'  {k} = {v}')

        self.stdout.write('\n' + '-' * 50)
        self.stdout.write('Add these to your .env:')
        self.stdout.write('-' * 50)
        self.stdout.write(f'KANGA_PAY_PUBLIC_KEY={public_key}')
        self.stdout.write(f'KANGA_PAY_SECRET_KEY={secret_key}')
        self.stdout.write(
            '\nIf keys are blank above, check the raw output and find the correct field names.'
        )
