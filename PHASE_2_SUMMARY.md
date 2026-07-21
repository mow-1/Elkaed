# Phase 2 Summary — Auth API, Course/Commerce API, ETL Pass 1

**Date:** 2026-07-14  
**Status:** Complete

---

## What Was Built

### Auth API (`apps/users/`)

| Endpoint | Method | Auth | What it does |
|---|---|---|---|
| `/api/auth/send-otp/` | POST | Public | Generates 6-digit OTP, sends via WhatsApp (Celery async), invalidates previous active OTPs |
| `/api/auth/verify-otp/` | POST | Public | Verifies OTP with brute-force protection (max 3 attempts), issues JWT on success |
| `/api/auth/profile/` | GET | JWT | Returns current user profile |
| `/api/auth/token/refresh/` | POST | Refresh token | Issues new access token |

**OTP flow nuances implemented:**
- `verify_otp()` returns `(bool, reason)` — the view surfaces translated Arabic error messages per reason code
- Attempts tracked per OTP row, not per phone — protects against timing attacks
- Register: creates User **after** OTP verified (not before) — prevents ghost accounts
- Login: does not reveal whether a phone number exists (same 200 response either way)

### Notifications (`apps/notifications/`)

- `services.py` — `send_whatsapp(phone, message)` calls wa-ma.org directly with timeout/error logging
- `tasks.py` — `send_whatsapp_task` wraps the service in a Celery task with 3 retries (30s delay)
- All OTP sends are async (`.delay()`) — HTTP response never waits for WhatsApp API
- `HomepageBanner` model added (was missing from Phase 1)

### Course API (`apps/courses/`)

| Endpoint | Method | Auth | What it does |
|---|---|---|---|
| `/api/courses/` | GET | Optional | Lists published courses; if auth'd, filters by user's student_type + academic_year |
| `/api/courses/<slug>/` | GET | Optional | Full course detail with topics + lessons |
| `/api/courses/<id>/enroll/` | POST | JWT | Wallet debit (atomic) or Kanga Pay redirect if insufficient |
| `/api/courses/my-enrollments/` | GET | JWT | Student's active enrollments |

**Enroll view logic:**
1. Free course → direct `get_or_create(Enrollment)`
2. Wallet sufficient → `wallet_purchase()` (atomic `select_for_update` on User row)
3. Wallet insufficient → creates `pending` Order, calls Kanga Pay API, returns `payment_url` with HTTP 402

### Commerce API (`apps/commerce/`)

| Endpoint | Method | Auth | What it does |
|---|---|---|---|
| `/api/commerce/wallet/` | GET | JWT | Balance + last 20 transactions |
| `/api/commerce/coupons/redeem/` | POST | JWT | Validates coupon, creates CouponRedemption, credits wallet atomically |
| `/api/commerce/kanga-pay/webhook/` | POST | HMAC | Verifies signature, completes Order, creates Enrollment(s) |

**Kanga Pay webhook:** CSRF-exempt (uses HMAC-SHA256 on request body with `KANGA_PAY_WEBHOOK_SECRET`).  
**Coupon redeem:** `unique_together(user, coupon)` at DB level + pre-check in view — double-spend impossible.

### Commerce Services (`apps/commerce/services.py`)

- `wallet_purchase(user, course)` — full atomic block: `select_for_update` → debit → Order → OrderItem → Enrollment → WalletTransaction. Raises `InsufficientBalance` or `AlreadyEnrolled` cleanly.
- `wallet_credit(user, amount, reference)` — used by coupon redeem and can be reused by Kanga Pay manual top-up.
- `verify_kanga_hmac(payload, signature)` — constant-time HMAC comparison.
- `create_kanga_payment(order, course, return_url)` — initiates Kanga Pay session (needs real API keys from WP options table).

### ETL Pass 1 — Users (`apps/etl/management/commands/etl_pass_1_users.py`)

```bash
python manage.py etl_pass_1_users --dry-run
python manage.py etl_pass_1_users --batch-size 500
```

- Reads `29_users JOIN 29_usermeta` with a single GROUP BY query (one round-trip)
- Transforms: phone normalization, display_name split, wallet_balance, guardian_phone from billing_company
- WordPress `$P$` phpass hashes stored as `phpass$$...` for Django's `PhpassPasswordHasher`
- Idempotent: skips existing `wp_user_id` values
- Writes skipped rows to `etl_skipped_users.log`
- **Expected output:** ~5,483 users

### Infrastructure

- `config/celery.py` + `config/__init__.py` — Celery app wired, autodiscovery enabled
- `apps/etl/` registered as Django app (needed for management commands)
- Production settings: `SECURE_PROXY_SSL_HEADER`, `USE_X_FORWARDED_HOST`, `SITE_URL`
- `crew/crew.py` — all agents now use `claude-sonnet-4-6` via `ANTHROPIC_API_KEY`
- `requirements.txt` — added `requests`, `tqdm` (psycopg2-binary was already there)
- `.env.example` — added `ANTHROPIC_API_KEY`, `WP_DB_*`, `SITE_URL`

---

## Key Decisions Made

- **WhatsApp sends are always async** — `.delay()` not `.apply_async()` — simpler, sufficient. No ETA needed for OTP.
- **OTP verify returns `(bool, reason)` tuple** — views translate reasons to Arabic user messages. Service stays testable without Arabic knowledge.
- **`wallet_purchase` raises exceptions, not Response objects** — service layer stays framework-agnostic. Views catch and translate to HTTP responses.
- **Kanga Pay HMAC on full request body** — not on selected fields, which avoids field-ordering bugs if Kanga Pay adds fields.
- **ETL uses a single GROUP BY query** — not N+1 per user for usermeta. On 5,483 users with ~20 meta keys each, this is ~10x faster.
- **`psycopg2` for WP DB, not Django's DB router** — keeps the WP connection entirely separate; no risk of accidentally writing to WP.

---

## Issues Found in Phase 2 (carry to Phase 3)

1. **`get_client_ip()` is not implemented** — `VideoAccessToken.is_valid(ip)` needs it, and the video access endpoint in Phase 3 will need to call it. Add a `utils.py` helper that checks `X-Forwarded-For` first (guarded by `settings.USE_X_FORWARDED_HOST`).

2. **`SITE_URL` not in base settings** — `create_kanga_payment` references it but it's only set in production.py. Add a `SITE_URL = config('SITE_URL', default='http://localhost:8000')` to `base.py`.

3. **No `requests` library in original requirements** — added in this phase but the Kanga Pay `create_kanga_payment()` and wa-ma.org calls both need it. Already fixed.

4. **WordPress SQL dump must be imported into a local PostgreSQL DB before running ETL** — use `pgloader` to migrate directly from the live MySQL host, or import the `.sql` zip backup after converting MySQL syntax. ETL uses psycopg2 (already correct). See PHASE_2_SUMMARY for the `pgloader` one-liner.

5. **`HomepageBanner` has no public API endpoint** — Phase 3 needs `GET /api/banners/` for the React homepage to fetch active banners.

6. **Course enroll endpoint does not send confirmation WhatsApp** — Blueprint §4.7 shows enrollment should notify student via WhatsApp. Add `send_whatsapp_task.delay(user.phone, message)` after successful enrollment in Phase 3.

7. **Quiz attempt submission has no WhatsApp notify** — `functions.php` hook `tutor_quiz/attempt_ended` sent results to student AND guardian. Phase 3 (quiz API) must replicate this via `QuizAttempt` post_save signal.

8. **`create_kanga_payment` needs real API endpoint/format** — The Kanga Pay API URL and payload format are assumed. Retrieve actual docs + keys from WP options table (`woocommerce_kanga_pay_settings`) before Phase 3 testing.

---

## Phase 3 Scope (recommended)

1. **`utils.py`** — `get_client_ip(request)` helper
2. **Fix `SITE_URL`** in `base.py`
3. **Video API** — `RequestVideoAccessView`, `VideoKeyView` (AES key delivery), upload endpoint stub
4. **Celery task: `transcode_video`** — FFmpeg HLS pipeline skeleton
5. **Quiz API** — attempt start, answer submit, attempt end + WhatsApp result notification
6. **Enrollment WhatsApp confirmation** — add to enroll view
7. **Banner API** — `GET /api/banners/` public endpoint
8. **Instructor API** — create student, bulk enroll, quiz lock/unlock
9. **ETL Pass 2** — Categories; Pass 3 — Courses/Topics/Lessons; Pass 4 — Quizzes
10. **Fix ETL DB driver** — switch from psycopg2 to pymysql for WordPress MySQL connection

---

## Running Phase 2

```bash
# Start backend
cd E:\Elkaed\backend
cp .env.example .env   # fill in values
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver

# Start Celery worker (separate terminal)
celery -A config worker -l info

# Run ETL Pass 1 (fill WP_DB_* in .env first)
python manage.py etl_pass_1_users --dry-run
python manage.py etl_pass_1_users

# Run CrewAI crew (needs ANTHROPIC_API_KEY)
cd E:\Elkaed\crew
python main.py validate courses
```

## API Quick Reference

```
POST /api/auth/send-otp/        {phone, purpose}
POST /api/auth/verify-otp/      {phone, code, purpose, [first_name, last_name, student_type, academic_year]}
GET  /api/auth/profile/
POST /api/auth/token/refresh/

GET  /api/courses/
GET  /api/courses/<slug>/
POST /api/courses/<id>/enroll/
GET  /api/courses/my-enrollments/

GET  /api/commerce/wallet/
POST /api/commerce/coupons/redeem/   {code}
POST /api/commerce/kanga-pay/webhook/
```
