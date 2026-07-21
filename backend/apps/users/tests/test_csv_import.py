from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from apps.commerce.models import WalletTransaction
from apps.users.models import ImportBatch, User
from apps.users.services import validate_import_row
from apps.users.tasks import import_csv_task

VALID_ROW = {
    'first_name': 'أحمد', 'last_name': 'محمد',
    'student_phone': '01011111111', 'guardian_phone': '01022222222',
    'academic_year': '1st', 'initial_wallet_balance': '50',
}


class ValidateImportRowTests(TestCase):
    def test_valid_row_has_no_errors(self):
        seen = set()
        errors = validate_import_row(dict(VALID_ROW), seen)
        self.assertEqual(errors, [])

    def test_invalid_phone_is_rejected(self):
        row = dict(VALID_ROW, student_phone='123')
        errors = validate_import_row(row, set())
        self.assertTrue(errors)

    def test_guardian_same_as_student_is_rejected(self):
        row = dict(VALID_ROW, guardian_phone=VALID_ROW['student_phone'])
        errors = validate_import_row(row, set())
        self.assertTrue(any('ولي الأمر' in e for e in errors))

    def test_duplicate_within_same_file_is_rejected_on_second_occurrence(self):
        seen = set()
        first = validate_import_row(dict(VALID_ROW), seen)
        second = validate_import_row(dict(VALID_ROW), seen)
        self.assertEqual(first, [])
        self.assertTrue(second)

    def test_existing_phone_in_db_is_rejected(self):
        User.objects.create_user(
            phone='201011111111', first_name='X', last_name='Y',
            role='student', password='x',
        )
        errors = validate_import_row(dict(VALID_ROW), set())
        self.assertTrue(any('مسجل بالفعل' in e for e in errors))


class ImportCsvTaskTests(TestCase):
    def _make_batch(self, csv_text):
        f = SimpleUploadedFile('students.csv', csv_text.encode('utf-8'))
        return ImportBatch.objects.create(file=f)

    def test_any_invalid_row_aborts_with_zero_writes(self):
        csv_text = (
            'first_name,last_name,student_phone,guardian_phone,academic_year,initial_wallet_balance\n'
            'أحمد,محمد,01033333333,01044444444,1st,0\n'
            'سارة,علي,invalid-phone,01055555555,2nd,0\n'
        )
        batch = self._make_batch(csv_text)
        import_csv_task(batch.id)
        batch.refresh_from_db()

        self.assertEqual(batch.status, 'failed')
        self.assertEqual(batch.imported_count, 0)
        self.assertFalse(User.objects.filter(phone='201033333333').exists())

    def test_fully_valid_csv_creates_users_and_credits_wallet(self):
        csv_text = (
            'first_name,last_name,student_phone,guardian_phone,academic_year,initial_wallet_balance\n'
            'أحمد,محمد,01066666666,01077777777,1st,25\n'
        )
        batch = self._make_batch(csv_text)
        import_csv_task(batch.id)
        batch.refresh_from_db()

        self.assertEqual(batch.status, 'done')
        self.assertEqual(batch.imported_count, 1)

        user = User.objects.get(phone='201066666666')
        self.assertEqual(user.student_type, 'center')
        self.assertEqual(user.role, 'student')
        self.assertTrue(user.must_change_password)
        self.assertEqual(user.wallet_balance, Decimal('25'))
        self.assertTrue(WalletTransaction.objects.filter(user=user, reason_code='csv_import').exists())
