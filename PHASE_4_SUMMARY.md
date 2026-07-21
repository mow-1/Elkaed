# Phase 4 Summary — ETL: WordPress → Django Migration

**Date:** 2026-07-14  
**Status:** Complete

---

## What Was Built

All 9 ETL management commands in `backend/apps/etl/management/commands/`:

### ETL Passes

| Pass | File | Source Tables | Target Models | Scale |
|---|---|---|---|---|
| 1 | `etl_pass_1_users.py` | `29_users` + `29_usermeta` | `User` | ~5,483 users |
| 2 | `etl_pass_2_categories.py` | `29_terms` + `29_term_taxonomy` | `Category` | course-category taxonomy |
| 3 | `etl_pass_3_courses.py` | `29_posts` (post_type=courses/topics/lessons) | `Course`, `Topic`, `Lesson` | full course tree |
| 4 | `etl_pass_4_quizzes.py` | `29_tutor_quiz_questions` + `29_tutor_quiz_question_answers` | `Quiz`, `Question`, `AnswerChoice` | 12,590 questions / 48,475 choices |
| 5 | `etl_pass_5_attempts.py` | `29_tutor_attempts` + `29_tutor_attempt_answers` | `QuizAttempt`, `AttemptAnswer` | 9,767 attempts / 246,864 answers |
| 6 | `etl_pass_6_orders.py` | `29_tutor_orders` + `29_tutor_order_items` + `29_posts(tutor_enrolled)` | `Order`, `OrderItem`, `Enrollment` | 3 sub-passes |
| 7 | `etl_pass_7_wallet.py` | `29_posts(shop_coupon)` + `29_coupon_redemptions` | `Coupon`, `CouponRedemption`, `WalletTransaction` | coupon history |

### Support Commands

| File | Purpose |
|---|---|
| `etl_run_all.py` | Master: runs passes 1-7 in sequence with `--start-pass N` resume |
| `etl_validate.py` | Post-ETL row count report vs expected ranges |
| `extract_kanga_keys.py` | Extracts Kanga Pay API keys from `29_options` (run before WP shutdown) |

---

## Key Technical Decisions

### Database Driver
- **pymysql** for WordPress MariaDB 10.11 — NOT psycopg2 (PostgreSQL driver)
- Port: `3306` (not `5432`)
- Connect: `pymysql.connect(db=..., charset='utf8mb4', port=int(...))`

### Academic Year Mapping
```python
ACADEMIC_YEAR_MAP = {
    'first_secondary':  '1st',
    'second_secondary': '2nd',
    'third_secondary':  '3rd',
}
```
WP stores `first_secondary`; Django expects `1st/2nd/3rd`.

### Password Bridging
WP phpass hashes stored as `phpass$$<hash>` — custom `PhpassPasswordHasher` verifies on login, auto-upgrades to Argon2 on first successful login. No user needs to reset their password.

### Idempotency
All passes use `get_or_create` / `update_or_create` on WP ID fields (`wp_user_id`, `wp_post_id`, `wp_order_id`). Safe to re-run after partial failures.

### Memory Management (Pass 5)
246,864 answer rows processed via `LIMIT/OFFSET` streaming — never `fetchall()`. Default chunk size: 2,000 rows. Resume from any offset: `--offset 50000`.

### Cache Dicts (Pass 6)
`user_cache` and `course_cache` loaded once before loops:
```python
user_cache   = {u.wp_user_id: u for u in User.objects.filter(wp_user_id__isnull=False)}
course_cache = {c.wp_post_id: c for c in Course.objects.filter(wp_post_id__isnull=False)}
```
Zero per-row DB queries for lookups.

### Two-Pass Parent Linking (Pass 2)
Categories built with `parent=None` in first pass, parent FKs wired in second pass using in-memory `term_id → slug` dict. No circular dependency issues.

---

## Bugs Fixed

| Bug | Fix |
|---|---|
| `psycopg2` used for MariaDB | Replaced with `pymysql` in `etl_pass_1_users.py` and `extract_kanga_keys.py` |
| Default port 5432 for WP DB | Changed to 3306 in `extract_kanga_keys.py` |
| `academic_year` stored raw WP value | `ACADEMIC_YEAR_MAP` applied during transform |
| Duplicate `psycopg2-binary` in requirements.txt | Removed duplicate, added `PyMySQL==1.1.1` |
| Missing users/quizzes migrations | Ran `makemigrations users --name initial` and `makemigrations quizzes --name initial` |
| SECRET_KEY missing for makemigrations | Created `backend/.env` with dev placeholder values |

---

## Known Ceilings (ponytail notes)

- `Order.created_at` is `auto_now_add=True` — original WP order timestamp not preserved. To fix: remove `auto_now_add`, add `created_at` to `update_or_create` defaults.
- `AttemptAnswer.wp_answer_id` has no `unique=True` — `bulk_create(ignore_conflicts=True)` deduplicates only if the field is unique. Add migration before production ETL run.
- `WalletTransaction.balance_after` uses the Pass-1 wallet balance snapshot — not recalculated from transaction history.

---

## Run Order

```bash
cd E:\Elkaed\backend

# 1. Fill in WP DB credentials in .env
# WP_DB_HOST, WP_DB_PORT, WP_DB_NAME, WP_DB_USER, WP_DB_PASSWORD

# 2. Extract Kanga Pay keys (run before WP shutdown)
python manage.py extract_kanga_keys

# 3. Dry run — preview all passes, no writes
python manage.py etl_run_all --dry-run

# 4. Full run
python manage.py etl_run_all --batch-size 500

# 5. Resume from a specific pass if interrupted
python manage.py etl_run_all --start-pass 4

# 6. Validate counts
python manage.py etl_validate
```

**Expected validation output:**
```
ETL Validation Report
========================================
[OK ] Users                   5483
[OK ] Instructors               12
[OK ] Courses                  ---
[OK ] Topics                   ---
[OK ] Lessons                  ---
[OK ] Quizzes                  ---
[OK ] Questions              12590
[OK ] QuizAttempts            9767
[OK ] AttemptAnswers        246864
[OK ] Enrollments              ---
[OK ] Orders                   ---
[OK ] Coupons                  ---
[OK ] Redemptions              ---
```

---

## Phase 5 Scope (Admin Dashboard + Remaining Features)

1. Enhanced Django admin: customer detail (enrollment history, orders, quiz results)
2. Customer segments: LTV display, churn detection (inactive >30 days)
3. Order status change WhatsApp notifications (signal on Order save)
4. NotificationPreference model (user opt-in/out of WhatsApp types)
5. Email field on User + EmailCampaign model + Celery SMTP task
6. Admin analytics page (custom Django admin view)
7. Banner management enhancements (preview, scheduling)
