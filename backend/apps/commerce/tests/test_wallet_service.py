from decimal import Decimal

from django.test import TestCase

from apps.attendance.models import PricingSettings
from apps.commerce.models import WalletTransaction
from apps.commerce.services import InsufficientBalance, wallet_credit, wallet_debit
from apps.users.models import User


class WalletServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            phone='201111111111', first_name='W', last_name='Test',
            role='student', password='x',
        )

    def test_credit_increases_balance_and_writes_ledger_row(self):
        wallet_credit(self.user, Decimal('100'), reason_code='admin_credit')
        self.user.refresh_from_db()
        self.assertEqual(self.user.wallet_balance, Decimal('100'))
        txn = WalletTransaction.objects.get(user=self.user)
        self.assertEqual(txn.type, 'credit')
        self.assertEqual(txn.amount, Decimal('100'))
        self.assertEqual(txn.balance_after, Decimal('100'))

    def test_debit_decreases_balance(self):
        wallet_credit(self.user, Decimal('100'), reason_code='admin_credit')
        wallet_debit(self.user, Decimal('30'), reason_code='attendance_present')
        self.user.refresh_from_db()
        self.assertEqual(self.user.wallet_balance, Decimal('70'))

    def test_debit_blocked_when_negative_and_not_allowed(self):
        PricingSettings.objects.filter(pk=1).delete()
        settings_obj = PricingSettings.get_solo()
        settings_obj.allow_negative_balance = False
        settings_obj.save(update_fields=['allow_negative_balance'])

        with self.assertRaises(InsufficientBalance):
            wallet_debit(self.user, Decimal('10'), reason_code='attendance_present')
        self.user.refresh_from_db()
        self.assertEqual(self.user.wallet_balance, Decimal('0'))
        self.assertFalse(WalletTransaction.objects.filter(user=self.user).exists())

    def test_debit_allowed_negative_when_setting_enabled(self):
        settings_obj = PricingSettings.get_solo()
        settings_obj.allow_negative_balance = True
        settings_obj.save(update_fields=['allow_negative_balance'])

        wallet_debit(self.user, Decimal('10'), reason_code='attendance_present')
        self.user.refresh_from_db()
        self.assertEqual(self.user.wallet_balance, Decimal('-10'))

    def test_refund_reverses_a_prior_debit(self):
        wallet_credit(self.user, Decimal('100'), reason_code='admin_credit')
        wallet_debit(self.user, Decimal('40'), reason_code='attendance_present')
        wallet_credit(self.user, Decimal('40'), reason_code='reversal', note='refund')
        self.user.refresh_from_db()
        self.assertEqual(self.user.wallet_balance, Decimal('100'))
        self.assertEqual(WalletTransaction.objects.filter(user=self.user).count(), 3)


class AttendanceIdempotencyTests(TestCase):
    """Idempotent status transitions are exercised more fully in
    apps/attendance/tests/test_absence_flow.py — this just confirms the
    underlying reconcile command sees no drift after normal operations."""

    def test_reconcile_command_finds_no_drift_after_normal_operations(self):
        from io import StringIO
        from django.core.management import call_command

        user = User.objects.create_user(
            phone='201111111112', first_name='R', last_name='Test',
            role='student', password='x',
        )
        wallet_credit(user, Decimal('50'), reason_code='admin_credit')
        wallet_debit(user, Decimal('20'), reason_code='attendance_present')

        out = StringIO()
        call_command('reconcile_wallet', stdout=out)
        self.assertNotIn(str(user.phone), out.getvalue())
