from decimal import Decimal

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.utils.timezone import now as tz_now

from apps.audit.services import log_action
from apps.commerce.services import InsufficientBalance, wallet_credit, wallet_debit
from .models import AttendanceRecord, PricingSettings, StudentDiscount


def effective_price(user, base_price, scope: str):
    """Returns (final_price, discount_or_None) after applying the student's active discount, if any."""
    now = tz_now()
    discount = (
        StudentDiscount.objects
        .filter(Q(scope=scope) | Q(scope='both'), student=user, active=True)
        .filter(Q(starts_at__isnull=True) | Q(starts_at__lte=now))
        .filter(Q(ends_at__isnull=True) | Q(ends_at__gte=now))
        .order_by('-created_at')
        .first()
    )
    if discount is None:
        return base_price, None

    if discount.discount_type == 'free':
        return Decimal('0'), discount
    if discount.discount_type == 'percentage':
        price = base_price - base_price * discount.value / Decimal('100')
        return price.quantize(Decimal('0.01')), discount
    if discount.discount_type == 'fixed_amount':
        return max(Decimal('0'), base_price - discount.value), discount
    return base_price, None


def _absence_message(record):
    lesson = record.session.linked_lesson
    link = f'{settings.SITE_URL}/courses/{lesson.topic.course.slug}' if lesson else ''
    return (
        f'نأسف لغيابك عن حصة "{record.session.title_ar}".\n'
        + (f'يمكنك مشاهدة الدرس أونلاين هنا: {link}' if link else 'تواصل معنا لمتابعة الدرس.')
    )


def _apply_status(record, status_value, actor):
    """The ONE place a status's financial + access + WhatsApp side effects get applied,
    for a record being set for the first time (fresh or via override)."""
    from apps.courses.models import LessonAccessGrant
    from apps.notifications.tasks import send_whatsapp_task

    if status_value == 'present':
        price, discount = effective_price(record.student, record.session.lesson_price, 'physical_only')
        try:
            wallet_debit(
                record.student, price, reason_code='attendance_present',
                related_object=record, created_by=actor,
                note=f'حضور: {record.session.title_ar}',
                original_amount=record.session.lesson_price if discount else None,
                discount=discount,
            )
            record.deducted = True
        except InsufficientBalance:
            record.deducted = False

    elif status_value == 'absent':
        price, discount = effective_price(record.student, record.session.lesson_price, 'physical_only')
        try:
            wallet_debit(
                record.student, price, reason_code='attendance_absent',
                related_object=record, created_by=actor,
                note=f'غياب — إرسال الدرس أونلاين: {record.session.title_ar}',
                original_amount=record.session.lesson_price if discount else None,
                discount=discount,
            )
            record.deducted = True
        except InsufficientBalance:
            record.deducted = False

        if record.session.linked_lesson:
            grant, created = LessonAccessGrant.objects.get_or_create(
                student=record.student, lesson=record.session.linked_lesson,
                defaults={'granted_via': 'absence', 'session': record.session, 'granted_by': actor},
            )
            if not created and grant.revoked:
                grant.revoked = False
                grant.save(update_fields=['revoked'])

            message = _absence_message(record)
            send_whatsapp_task.delay(record.student.phone, message)
            if PricingSettings.get_solo().notify_guardian_on_absence and record.student.guardian_phone:
                send_whatsapp_task.delay(record.student.guardian_phone, message)
            record.whatsapp_sent = True

    # absent_excused / makeup: no deduction, no WhatsApp, no grant — safe minimal default

    record.status = status_value
    record.save()
    log_action(actor, 'attendance_changed', target=record, after={'status': status_value, 'deducted': record.deducted})
    return record


def mark(session, student, status_value, actor) -> AttendanceRecord:
    """Get-or-create the record for this session+student, then apply/transition to
    `status_value`. Fresh record -> apply effects once. Existing + same status ->
    idempotent no-op (safe for QR re-scans). Existing + different status -> reverse
    old + apply new via set_attendance_status. THE single dispatch used by mark_present/
    mark_absent/mark_absent_excused and the /mark/ endpoint."""
    record, created = AttendanceRecord.objects.get_or_create(
        session=session, student=student, defaults={'status': status_value},
    )
    if created:
        return _apply_status(record, status_value, actor)
    if record.status == status_value:
        return record
    return set_attendance_status(record, status_value, actor)


def mark_present(session, student, actor, via='manual') -> AttendanceRecord:
    return mark(session, student, 'present', actor)


def mark_absent(session, student, actor) -> AttendanceRecord:
    return mark(session, student, 'absent', actor)


def mark_absent_excused(session, student, actor) -> AttendanceRecord:
    return mark(session, student, 'absent_excused', actor)


def set_attendance_status(record, new_status, actor, notes='') -> AttendanceRecord:
    """The single override entry point — reverses the old status's money/access, then
    applies the new one. Used by manual re-marks, override tools, and (Phase 5) QR re-scans."""
    from apps.courses.models import LessonAccessGrant

    if new_status == record.status:
        return record  # idempotent no-op

    old_status = record.status

    if record.deducted:
        content_type = ContentType.objects.get_for_model(AttendanceRecord)
        original_txn = (
            record.student.wallet_transactions
            .filter(content_type=content_type, object_id=record.pk,
                     reason_code__in=('attendance_present', 'attendance_absent'))
            .order_by('-created_at')
            .first()
        )
        if original_txn:
            wallet_credit(
                record.student, original_txn.amount, reference='attendance_reversal',
                note=f'عكس: {record.session.title_ar}', reason_code='reversal',
                related_object=record, created_by=actor,
            )

    if old_status == 'absent':
        LessonAccessGrant.objects.filter(
            student=record.student, lesson=record.session.linked_lesson, revoked=False,
        ).update(revoked=True)

    _apply_status(record, new_status, actor)

    record.overridden_by = actor
    record.notes = notes or record.notes
    record.save(update_fields=['overridden_by', 'notes'])

    log_action(
        actor, 'attendance_changed', target=record,
        before={'status': old_status}, after={'status': new_status},
    )
    return record


def revoke_access(grant, actor=None):
    grant.revoked = True
    grant.save(update_fields=['revoked'])
    log_action(actor, 'access_revoked', target=grant)
    return grant


def resend_whatsapp(record, actor):
    from apps.notifications.tasks import send_whatsapp_task
    message = _absence_message(record)
    send_whatsapp_task.delay(record.student.phone, message)
    record.whatsapp_sent = True
    record.save(update_fields=['whatsapp_sent'])
    log_action(actor, 'updated', target=record, note='إعادة إرسال واتساب')
    return record
