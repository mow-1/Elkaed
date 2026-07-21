import hashlib
import hmac
import logging

import requests
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import F

from apps.courses.models import Course, Enrollment
from apps.users.models import User
from .models import Order, OrderItem, WalletTransaction

logger = logging.getLogger(__name__)


class InsufficientBalance(Exception):
    pass


class AlreadyEnrolled(Exception):
    pass


def _write_ledger_entry(user, amount, direction, reason_code, related_object=None,
                         created_by=None, note='', original_amount=None, reference=None,
                         discount=None):
    """The single place a WalletTransaction row gets created. Does NOT touch
    user.wallet_balance — caller must have already updated + saved it."""
    content_type = None
    object_id = None
    if related_object is not None:
        content_type = ContentType.objects.get_for_model(related_object)
        object_id = related_object.pk

    if reference is None:
        reference = f'{content_type.model}_{object_id}' if content_type else reason_code

    return WalletTransaction.objects.create(
        user=user,
        amount=amount,
        type=direction,
        balance_after=user.wallet_balance,
        reference=reference,
        note=note,
        reason_code=reason_code,
        content_type=content_type,
        object_id=object_id,
        created_by=created_by,
        original_amount=original_amount,
        discount=discount,
    )


def wallet_purchase(user: User, course: Course, price=None, original_price=None, discount=None) -> Order:
    """Atomic wallet debit + order + enrollment. Raises on insufficient funds or duplicate."""
    price = price if price is not None else course.price
    with transaction.atomic():
        locked_user = User.objects.select_for_update().get(pk=user.pk)

        if Enrollment.objects.filter(student=locked_user, course=course).exists():
            raise AlreadyEnrolled()

        if price > 0 and locked_user.wallet_balance < price:
            raise InsufficientBalance()

        locked_user.wallet_balance -= price
        locked_user.save(update_fields=['wallet_balance'])

        order = Order.objects.create(
            user=locked_user,
            status='completed',
            payment_method='wallet',
            total_price=price,
        )
        OrderItem.objects.create(order=order, course=course, price=price)
        Enrollment.objects.create(
            student=locked_user,
            course=course,
            payment_method='wallet',
            order=order,
        )
        _write_ledger_entry(
            locked_user, price, 'debit', 'purchase',
            related_object=order, created_by=user,
            note=f'شراء كورس: {course.title}' + (' (معفى)' if price == 0 and discount else ''),
            original_amount=original_price, discount=discount,
        )
        return order


def wallet_credit(user: User, amount, reference: str = '', note: str = '', *,
                   reason_code='admin_credit', related_object=None, created_by=None,
                   original_amount=None, discount=None) -> None:
    """Atomic wallet top-up (coupon redeem, Kanga Pay, admin credit, ...)."""
    with transaction.atomic():
        locked_user = User.objects.select_for_update().get(pk=user.pk)
        locked_user.wallet_balance += amount
        locked_user.save(update_fields=['wallet_balance'])
        _write_ledger_entry(
            locked_user, amount, 'credit', reason_code,
            related_object=related_object, created_by=created_by,
            note=note, original_amount=original_amount,
            reference=reference or None, discount=discount,
        )
        from apps.audit.services import log_action
        log_action(
            created_by, 'credited', target=related_object or locked_user,
            after={'amount': str(amount), 'balance_after': str(locked_user.wallet_balance), 'reason_code': reason_code},
        )


def wallet_debit(user: User, amount, reason_code, related_object=None, created_by=None,
                  note='', original_amount=None, discount=None):
    """Atomic wallet deduction. Blocks going negative unless PricingSettings allows it."""
    with transaction.atomic():
        locked_user = User.objects.select_for_update().get(pk=user.pk)
        if amount > 0 and locked_user.wallet_balance - amount < 0:
            from apps.attendance.models import PricingSettings
            if not PricingSettings.get_solo().allow_negative_balance:
                raise InsufficientBalance()
        locked_user.wallet_balance -= amount
        locked_user.save(update_fields=['wallet_balance'])
        _write_ledger_entry(
            locked_user, amount, 'debit', reason_code,
            related_object=related_object, created_by=created_by,
            note=note, original_amount=original_amount, discount=discount,
        )
        from apps.audit.services import log_action
        log_action(
            created_by, 'debited', target=related_object or locked_user,
            after={'amount': str(amount), 'balance_after': str(locked_user.wallet_balance), 'reason_code': reason_code},
        )
    return locked_user.wallet_balance


def verify_kanga_hmac(payload: bytes, signature: str) -> bool:
    expected = hmac.new(
        settings.KANGA_PAY_WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def create_kanga_payment(order: Order, description: str, return_url: str) -> str:
    """
    Initiate a Kanga Pay payment and return the redirect URL.
    Kanga Pay API docs: https://kanga-pay.com/docs (retrieve keys from WP options).
    `description` is a plain label (a course title, or "N courses" for a cart checkout).
    """
    try:
        resp = requests.post(
            'https://api.kanga-pay.com/v1/payments',
            json={
                'amount':      str(order.total_price),
                'currency':    'EGP',
                'order_id':    str(order.pk),
                'description': description,
                'return_url':  return_url,
                'webhook_url': f'{settings.SITE_URL}/api/commerce/kanga-pay/webhook/',
            },
            headers={
                'Authorization': f'Bearer {settings.KANGA_PAY_SECRET_KEY}',
                'X-Public-Key':  settings.KANGA_PAY_PUBLIC_KEY,
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        order.transaction_id = data.get('payment_id', '')
        order.save(update_fields=['transaction_id'])
        return data['payment_url']
    except requests.RequestException as exc:
        logger.error('Kanga Pay init failed for order %s: %s', order.pk, exc)
        raise
