import csv
import io
from decimal import Decimal

from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.utils.timezone import now

from apps.notifications.tasks import send_whatsapp_task


@shared_task
def import_csv_task(batch_id):
    from .models import ImportBatch, User
    from .serializers import normalize_phone
    from .services import validate_import_row, generate_strong_password
    from apps.commerce.services import wallet_credit
    from apps.attendance.models import CenterGroup

    try:
        batch = ImportBatch.objects.get(pk=batch_id)
    except ImportBatch.DoesNotExist:
        return

    try:
        batch.file.open()
        content = batch.file.read()
        batch.file.close()
        if isinstance(content, bytes):
            content = content.decode('utf-8-sig')

        rows = list(csv.DictReader(io.StringIO(content)))

        # re-validate every row at execution time — never trust the earlier preview
        seen_phones = set()
        row_results = []
        for i, row in enumerate(rows, start=1):
            errors = validate_import_row(row, seen_phones)
            row_results.append({
                'row': i,
                'phone': (row.get('student_phone') or '').strip(),
                'status': 'ok' if not errors else 'error',
                'errors': errors,
            })

        if any(r['status'] == 'error' for r in row_results):
            batch.status = 'failed'
            batch.row_results = row_results
            batch.total_rows = len(rows)
            batch.completed_at = now()
            batch.save()
            return

        batch.status = 'processing'
        batch.total_rows = len(rows)
        batch.save()

        queued_messages = []

        with transaction.atomic():
            for row in rows:
                student_phone = normalize_phone(row['student_phone'])
                guardian_phone = normalize_phone(row['guardian_phone'])
                password = generate_strong_password()

                group_name = (row.get('center_group') or '').strip()
                group = CenterGroup.objects.filter(name_ar=group_name).first() if group_name else None

                user = User.objects.create_user(
                    phone=student_phone,
                    first_name=row['first_name'].strip(),
                    last_name=row['last_name'].strip(),
                    guardian_phone=guardian_phone,
                    academic_year=row['academic_year'],
                    student_type='center',
                    role='student',
                    password=password,
                    must_change_password=True,
                    group=group,
                )

                balance = Decimal(row['initial_wallet_balance'])
                if balance > 0:
                    wallet_credit(
                        user, balance,
                        note='رصيد افتتاحي من استيراد CSV',
                        reason_code='csv_import',
                        created_by=batch.uploaded_by,
                    )

                message = (
                    f'أهلاً {user.first_name}،\n'
                    f'تم تسجيلك في منصة القائد ({settings.SITE_URL}).\n'
                    f'رقم الدخول: {student_phone}\n'
                    f'كلمة المرور: {password}\n'
                    'غيّر كلمة المرور بعد أول تسجيل دخول.'
                )
                queued_messages.append((student_phone, message))

            # register the WhatsApp sends to fire only after the transaction actually
            # commits — never for a batch that could still roll back
            transaction.on_commit(
                lambda messages=queued_messages: [
                    send_whatsapp_task.delay(phone, msg) for phone, msg in messages
                ]
            )

        batch.status = 'done'
        batch.imported_count = len(rows)
        batch.failed_count = 0
        batch.row_results = row_results
        batch.completed_at = now()
        batch.save()

    except Exception as exc:
        batch.status = 'failed'
        batch.row_results = [{'row': 0, 'phone': '', 'status': 'error', 'errors': [str(exc)]}]
        batch.completed_at = now()
        batch.save()
