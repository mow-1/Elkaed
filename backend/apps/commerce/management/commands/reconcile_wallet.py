from django.core.management.base import BaseCommand
from django.db.models import Sum, Case, When, F, DecimalField

from apps.commerce.models import WalletTransaction
from apps.users.models import User


class Command(BaseCommand):
    help = 'Reconcile each user.wallet_balance against the sum of their WalletTransaction ledger.'

    def add_arguments(self, parser):
        parser.add_argument('--fix', action='store_true', help='Set wallet_balance to the computed ledger sum for drifted users.')

    def handle(self, *args, **options):
        fix = options['fix']
        drifted = 0

        signed = Case(
            When(type='credit', then=F('amount')),
            When(type='debit', then=-F('amount')),
            output_field=DecimalField(max_digits=10, decimal_places=2),
        )
        ledger_sums = dict(
            WalletTransaction.objects.values('user_id').annotate(total=Sum(signed)).values_list('user_id', 'total')
        )

        for user in User.objects.all():
            expected = ledger_sums.get(user.pk, 0) or 0
            actual = user.wallet_balance
            if expected != actual:
                drifted += 1
                diff = actual - expected
                self.stdout.write(
                    f'user #{user.pk} ({user.phone}): expected={expected} actual={actual} diff={diff}'
                )
                if fix:
                    user.wallet_balance = expected
                    user.save(update_fields=['wallet_balance'])

        if drifted == 0:
            self.stdout.write(self.style.SUCCESS('No drift found — all wallet balances match their ledgers.'))
        else:
            action = 'fixed' if fix else 'found (run with --fix to correct)'
            self.stdout.write(self.style.WARNING(f'{drifted} drifted user(s) {action}.'))
