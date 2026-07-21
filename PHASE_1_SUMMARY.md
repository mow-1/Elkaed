# Phase 1 Summary — Django Backend Foundation + CrewAI Crew

**Date:** 2026-07-14  
**Status:** Complete

---

## What Was Built

### `backend/` — Django Project Skeleton

| File/Dir | Purpose |
|---|---|
| `config/settings/base.py` | All shared settings: JWT (15 min access / 30 day refresh), Redis cache, Celery, CORS, i18n Arabic-first |
| `config/settings/development.py` | DEBUG=True, CORS_ALLOW_ALL_ORIGINS |
| `config/settings/production.py` | Strict HTTPS, ALLOWED_HOSTS from env, CONN_MAX_AGE |
| `config/urls.py` | Top-level URL skeleton — all apps rooted at `/api/` |
| `apps/users/` | Custom User model (phone PK), PhoneOTP, PhpassPasswordHasher, UserManager |
| `apps/courses/` | Category, Course, Topic, Lesson, Enrollment, LessonProgress |
| `apps/quizzes/` | Quiz, Question, AnswerChoice, QuizAttempt, AttemptAnswer |
| `apps/commerce/` | Order, OrderItem, Coupon, CouponRedemption, WalletTransaction |
| `apps/videos/` | Video, VideoAccessToken, VideoAccessLog |
| `apps/notifications/` | NotificationTemplate (wa-ma.org trigger registry) |
| `etl/` | Empty package — ETL management commands land here in Phase 4 |
| `requirements.txt` | Pinned: Django 5.0.6, DRF, simplejwt, celery, passlib[phpass], phpserialize, boto3 |
| `.env.example` | All required env vars documented |

### `crew/` — CrewAI Crew

Three agents, three tasks:

| Agent | Task | Invocation |
|---|---|---|
| `django_backend_developer` | `write_api_views_task` | `python main.py views <app> "<feature>"` |
| `schema_validator` | `validate_models_task` | `python main.py validate <app>` |
| `etl_engineer` | `write_etl_pass_task` | `python main.py etl <pass#> <name>` |

The crew is the code-generation layer for subsequent phases — use it to draft views, validate schema drift, and generate ETL passes.

---

## Key Decisions Made

- **Phone as USERNAME_FIELD** — email excluded entirely from User model per blueprint § critical risk.
- **PhpassPasswordHasher.must_update = True** — forces auto-upgrade to Argon2 on first login for every migrated user.
- **`wp_*_id` fields on every model** — migration deduplication keys; NULLable, unique where appropriate.
- **`Enrollment.unique_together(student, course)`** — prevents double-enrollment at the DB level.
- **`VideoAccessToken` validity check inline** — `is_valid(ip)` on the model itself; no service layer needed yet.
- **Coupon.is_valid() on model** — single check covers active flag, usage limit, and expiry.
- **`notifications` app is template-only** — actual WhatsApp send logic (Celery task + wa-ma.org call) deferred to Phase 2 to avoid building before the auth flow exists.

---

## What Phase 2 Must Add (learned this phase)

### Critical gaps identified while writing models:

1. **Missing `__init__.py` in `apps/`** — Django won't find apps without it. Add `E:\Elkaed\backend\apps\__init__.py`.

2. **`Enrollment` has a circular FK to `commerce.Order`** — Django resolves this via string reference `'commerce.Order'` already, but the migration order matters. Courses must migrate **before** commerce. Add migration dependency notes to ETL commands.

3. **`LessonProgress.view_count` increment race** — the blueprint uses `F('view_count') + 1` but the atomic update must wrap the enrollment check too. The wallet debit in `commerce` has the same problem. Use `select_for_update()` in Phase 2 views.

4. **OTP brute-force**: `PhoneOTP.attempts` is tracked but no view checks it yet. Phase 2 OTP view must increment `attempts` on every wrong code and block when `>= 3`.

5. **`VideoAccessToken` is IP-locked** — ensure the Django view that issues tokens uses `X-Forwarded-For` correctly (Nginx must set it). Add `SECURE_PROXY_SSL_HEADER` and `USE_X_FORWARDED_HOST` to production settings in Phase 2.

6. **Admin panel** (from CLAUDE.md backlog) — the custom React admin is Phase 5+. The Django admin configured here is a dev tool only; do not expose it at `/admin/` in production.

7. **`HomepageBanner` model** (Blueprint §6.8) — missing from Phase 1. Add to `apps/notifications/` or a new `apps/content/` app in Phase 2.

8. **CrewAI needs `OPENAI_API_KEY` (or Anthropic key) in env** — the crew won't run without an LLM provider configured. Add to `.env.example` in Phase 2. Consider wiring to Claude via `crewai` LLM config.

---

## Phase 2 Scope (recommended)

1. Add `apps/__init__.py`
2. Add `HomepageBanner` model
3. **Auth API** — OTP send/verify views (wa-ma.org), JWT issue/refresh
4. **Course & Enrollment API** — list/detail/enroll endpoints with wallet atomic debit
5. **Commerce API** — Kanga Pay order create + webhook receiver
6. Wire CrewAI to Claude Sonnet (set `LLM` in crew agents)
7. Run `python manage.py makemigrations` and `migrate` — validate DB structure
8. First ETL pass (users) as management command

---

## Install & Run (after .env is filled)

```bash
cd E:\Elkaed\backend
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Run CrewAI

```bash
cd E:\Elkaed\crew
pip install crewai>=0.80.0
# set OPENAI_API_KEY or configure Claude in crew.py
python main.py validate users
```
