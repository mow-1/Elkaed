"""
ETL Master — runs all 7 passes in order.

Run:
    python manage.py etl_run_all --dry-run
    python manage.py etl_run_all --batch-size 500
    python manage.py etl_run_all --start-pass 3   # resume from pass 3
"""
from django.core.management import call_command
from django.core.management.base import BaseCommand

PASSES = [
    ('etl_pass_1_users',      'Pass 1: Users & Profiles'),
    ('etl_pass_2_categories', 'Pass 2: Categories'),
    ('etl_pass_3_courses',    'Pass 3: Courses, Topics, Lessons'),
    ('etl_pass_4_quizzes',    'Pass 4: Quizzes & Questions'),
    ('etl_pass_5_attempts',   'Pass 5: Quiz Attempts (9,767 attempts + 246,864 answers)'),
    ('etl_pass_6_orders',     'Pass 6: Orders & Enrollments'),
    ('etl_pass_7_wallet',     'Pass 7: Coupons & Wallet'),
]


class Command(BaseCommand):
    help = 'Run all ETL passes in sequence'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--batch-size', type=int, default=500)
        parser.add_argument('--start-pass', type=int, default=1,
                            help='Start from this pass number (1-7), skipping earlier passes')

    def handle(self, *args, **options):
        dry_run    = options['dry_run']
        batch_size = options['batch_size']
        start      = options['start_pass']

        for i, (cmd_name, label) in enumerate(PASSES, start=1):
            if i < start:
                self.stdout.write(f'[skipped] {label}')
                continue
            self.stdout.write(self.style.MIGRATE_HEADING(f'\n=== {label} ==='))
            kwargs = {'batch_size': batch_size}
            if dry_run:
                kwargs['dry_run'] = True
            call_command(cmd_name, **kwargs)

        self.stdout.write(self.style.SUCCESS('\nETL complete. Run etl_validate next.'))
