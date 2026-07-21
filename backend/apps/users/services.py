import random
import secrets
import string
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.db.models import F
from django.utils.timezone import now

from .models import PhoneOTP, User
from .serializers import EGYPTIAN_PHONE_RE, normalize_phone

OTP_TTL_MINUTES = 5
OTP_MAX_ATTEMPTS = 3

IMPORT_REQUIRED_COLUMNS = (
    'first_name', 'last_name', 'student_phone', 'guardian_phone',
    'academic_year', 'initial_wallet_balance',
)
IMPORT_VALID_YEARS = ('1st', '2nd', '3rd')

_PW_DIGITS = '23456789'
_PW_UPPER = 'ABCDEFGHJKLMNPQRSTUVWXYZ'  # no 0/O, 1/I/L look-alikes
_PW_LOWER = 'abcdefghjkmnpqrstuvwxyz'   # no l
_PW_CHARSET = _PW_DIGITS + _PW_UPPER + _PW_LOWER


def generate_strong_password(length: int = 10) -> str:
    return ''.join(secrets.choice(_PW_CHARSET) for _ in range(length))


def regenerate_attendance_token(user: User) -> str:
    """Invalidates the old QR (e.g. a lost/shared card) by assigning a fresh token."""
    user.attendance_token = secrets.token_urlsafe(8)
    user.save(update_fields=['attendance_token'])
    return user.attendance_token


def validate_import_row(row: dict, seen_phones: set) -> list:
    """Validate one CSV row for bulk student import. Returns list of error strings (empty = valid)."""
    errors = []
    for col in IMPORT_REQUIRED_COLUMNS:
        if not (row.get(col) or '').strip():
            errors.append(f'{col} مطلوب')
    if errors:
        return errors  # can't validate further without the base fields

    student_phone = normalize_phone(row['student_phone'])
    guardian_phone = normalize_phone(row['guardian_phone'])

    if not EGYPTIAN_PHONE_RE.match(student_phone):
        errors.append('رقم هاتف الطالب غير صالح')
    if not EGYPTIAN_PHONE_RE.match(guardian_phone):
        errors.append('رقم هاتف ولي الأمر غير صالح')
    if student_phone == guardian_phone:
        errors.append('رقم ولي الأمر يجب أن يختلف عن رقم الطالب')
    if row['academic_year'] not in IMPORT_VALID_YEARS:
        errors.append('السنة الدراسية غير صالحة')

    try:
        balance = Decimal(row['initial_wallet_balance'])
        if balance < 0:
            errors.append('الرصيد الافتتاحي لا يمكن أن يكون سالبًا')
    except InvalidOperation:
        errors.append('الرصيد الافتتاحي غير صالح')

    if not errors:
        if User.objects.filter(phone=student_phone).exists():
            errors.append('رقم الهاتف مسجل بالفعل')
        elif student_phone in seen_phones:
            errors.append('رقم الهاتف مكرر في نفس الملف')
        else:
            seen_phones.add(student_phone)

    return errors


def generate_otp(phone: str, purpose: str) -> str:
    """Create a fresh 6-digit OTP, invalidating any prior active ones."""
    code = ''.join(random.choices(string.digits, k=6))
    # expire previous unused OTPs so only one is ever active
    PhoneOTP.objects.filter(phone=phone, purpose=purpose, used=False).update(used=True)
    PhoneOTP.objects.create(
        phone=phone,
        code=code,
        purpose=purpose,
        expires_at=now() + timedelta(minutes=OTP_TTL_MINUTES),
    )
    return code


def verify_otp(phone: str, code: str, purpose: str) -> tuple[bool, str]:
    """
    Returns (True, 'ok') on success or (False, reason) on failure.
    Reasons: 'no_otp', 'blocked', 'expired', 'wrong_code'
    """
    otp = (
        PhoneOTP.objects
        .filter(phone=phone, purpose=purpose, used=False)
        .order_by('-created_at')
        .first()
    )
    if otp is None:
        return False, 'no_otp'
    if otp.attempts >= OTP_MAX_ATTEMPTS:
        return False, 'blocked'
    if otp.expires_at <= now():
        return False, 'expired'
    if otp.code != code:
        otp.attempts = F('attempts') + 1
        otp.save(update_fields=['attempts'])
        return False, 'wrong_code'

    otp.used = True
    otp.save(update_fields=['used'])
    return True, 'ok'
