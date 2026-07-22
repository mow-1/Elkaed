import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone

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


def _kanga_signature(date_str: str = None) -> str:
    """Matches the real Kanga Pay API contract (ported from the WooCommerce plugin,
    class-kanga-pay-gateway.php): sha256(public_key + sha256(secret_key) + YYYYMMDD),
    not HMAC — there is no separate webhook secret in the real API."""
    date_str = date_str or datetime.now(timezone.utc).strftime('%Y%m%d')
    secret_hash = hashlib.sha256(settings.KANGA_PAY_SECRET_KEY.encode()).hexdigest()
    return hashlib.sha256(f'{settings.KANGA_PAY_PUBLIC_KEY}{secret_hash}{date_str}'.encode()).hexdigest()


def verify_kanga_signature(signature: str) -> bool:
    return hmac.compare_digest(_kanga_signature(), signature)


def create_kanga_payment(order: Order, description: str, return_url: str) -> str:
    """Initiate a Kanga Pay invoice (POST /v1/invoices/create) and return the redirect
    URL the customer's browser should go to. `description` is used as the single line
    item's name when the order has no OrderItems (e.g. a wallet top-up)."""
    items = [
        {'name': item.course.title, 'qty': 1, 'unit_price': float(item.price)}
        for item in order.items.select_related('course').all()
    ] or [{'name': description, 'qty': 1, 'unit_price': float(order.total_price)}]

    body = {
        'total_amount': float(order.total_price),
        'customer': {
            'name':  order.user.full_name,
            'email': order.user.email or '',
            'phone': order.user.phone,
        },
        'items': items,
        'currency': 'EGP',
        'webhook_override': [
            {'event_type': 'redirect.success', 'url': return_url},
            {'event_type': 'invoice.success', 'url': f'{settings.SITE_URL}/api/commerce/kanga-pay/webhook/'},
        ],
        'payload': json.dumps({'order_id': order.pk}),
    }

    try:
        resp = requests.post(
            'https://api.kanga-pay.com/v1/invoices/create',
            json=body,
            headers={
                'Authorization': f'Bearer {settings.KANGA_PAY_PUBLIC_KEY}',
                'Signature':     _kanga_signature(),
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get('status') != 'success' or not data.get('data', {}).get('invoice_link'):
            raise requests.RequestException(data.get('message', 'Kanga Pay: unexpected response'))
        return data['data']['invoice_link']
    except requests.RequestException as exc:
        logger.error('Kanga Pay init failed for order %s: %s', order.pk, exc)
        raise
