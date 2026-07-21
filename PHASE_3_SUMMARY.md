# Phase 3 Summary — Video API, Quiz API, WhatsApp Campaigns, Flash Sales, Bundle Deals

**Date:** 2026-07-14  
**Status:** Complete

---

## What Was Built

### Quiz API (`apps/quizzes/`)

| Endpoint | Method | Auth | What it does |
|---|---|---|---|
| `/api/quizzes/<id>/` | GET | JWT | Quiz detail + all questions with answer choices (is_correct hidden) |
| `/api/quizzes/<id>/start/` | POST | JWT | Creates QuizAttempt; enforces enrollment check; returns attempt ID |
| `/api/quizzes/attempts/<id>/submit/` | POST | JWT | Grades MCQ+TF answers, closes attempt, sends WhatsApp result to student + guardian |
| `/api/quizzes/attempts/<id>/` | GET | JWT | Attempt result; hides per-answer breakdown if quiz.hide_results=True |

**Grading logic:**
- MCQ: `AnswerChoice.is_correct` flag
- T/F: compare submitted text against the choice where `is_correct=True`
- WhatsApp result sent after `transaction.atomic` commit (outside the block) — no partial sends
- Guardian phone notified if set: `send_whatsapp_task.delay(student.guardian_phone, msg)`

### Profile PATCH + Admin Endpoints (`apps/users/`)

| Endpoint | Method | Auth | What it does |
|---|---|---|---|
| `/api/auth/profile/` | PATCH | JWT | Update first_name, last_name, guardian_phone (partial update) |
| `/api/auth/create-student/` | POST | Instructor/Admin | Creates student account; phone = default password |
| `/api/auth/analytics/` | GET | Admin/Staff | Platform stats: users by segment, revenue, top courses |

### Video Protection API (`apps/videos/`)

| Endpoint | Method | Auth | What it does |
|---|---|---|---|
| `/api/videos/<lesson_id>/token/` | POST | JWT | Issues 20-min IP-locked AES token; checks enrollment + view limit |
| `/api/videos/key/<token>/` | GET | Token+IP | Returns raw AES-128 key as `application/octet-stream`; marks token used |
| `/api/videos/<lesson_id>/progress/` | POST | JWT | Updates last_position_seconds and completed flag |

**Security layers:**
1. JWT for token request (enrollment + view limit check)
2. Token UUID + IP match for AES key (no JWT required — HLS player calls this)
3. AES key delivered binary-only from Django, never from CDN
4. Token expires in 20 minutes; existing unused tokens revoked on new request
5. `VideoAccessLog` records every key fetch with IP + timestamp

### Flash Sales (`apps/commerce/`)

| Endpoint | Method | Auth | What it does |
|---|---|---|---|
| `/api/commerce/flash-sales/` | GET | Public | Lists currently active flash sales with effective_price |
| `/api/courses/<id>/enroll/` | POST | JWT | Applies active flash sale price automatically before wallet debit |

- `FlashSale.effective_price()` = `course.price × (1 - discount_pct/100)`, rounded 2dp
- `wallet_purchase()` accepts `price=None` param — flash sale price passed through
- `OrderItem.price` stores the effective (discounted) price at time of purchase

### Bundle Deals (`apps/commerce/`)

| Endpoint | Method | Auth | What it does |
|---|---|---|---|
| `/api/commerce/bundles/` | GET | Public | Lists active bundles with courses |
| `/api/commerce/bundles/<id>/purchase/` | POST | JWT | Deduplicates, charges bundle price, bulk-enrolls all courses |

### WhatsApp Campaigns (`apps/notifications/`)

| Endpoint / Admin | What it does |
|---|---|
| Django Admin → Campaign → "إرسال الحملة" | Triggers `send_campaign_task.delay(campaign.pk)` |
| `send_campaign_task` Celery task | Filters users by segment, fires `send_whatsapp_task.delay` per user |

**Segments:** all / students / center / online / 1st / 2nd / 3rd

### Bulk Enroll (`apps/courses/`)

| Endpoint | Method | Auth | What it does |
|---|---|---|---|
| `/api/courses/bulk-enroll/` | POST | Instructor/Admin | Enrolls list of phones into a course; returns enrolled/skipped lists |

---

## Key Decisions Made

- **WhatsApp always outside atomic blocks** — send_whatsapp_task.delay() called after transaction.atomic exits, never inside. Prevents phantom sends if the transaction rolls back.
- **AES key endpoint has no JWT auth** — HLS.js player calls the key URL from the M3U8 manifest; it can't attach JWT headers. Auth is the token UUID + IP match instead.
- **AnswerChoiceSerializer hides is_correct** — separate serializer for quiz display vs grading; the grading field never leaves the server.
- **`wallet_purchase` accepts `price=None`** — single-param change lets flash sales pass effective_price without touching the service's internal logic.
- **Campaign task fires one Celery task per user** — fine for thousands; use batch chunking for >100k recipients.
- **`AttemptResultView` pops `answers` key** when `quiz.hide_results=True` — cleaner than a separate serializer.

---

## Issues Fixed from Phase 2

1. **Course enroll WhatsApp** — added `send_whatsapp_task.delay()` after successful enrollment
2. **Quiz attempt WhatsApp** — student + guardian notified after submit
3. **Flash sale pricing not applied** — `EnrollView` now queries active `FlashSale` and passes `effective_price`
4. **Double query in SubmitAttemptView** — map built first, IDs derived from map keys (not separate query)
5. **`views_remaining` missing from video token response** — added to `VideoTokenSerializer`
6. **Kanga Pay webhook WhatsApp** — notification sent after atomic enrollment (outside block)

---

## Migrations Added

- `apps/commerce/0001-0003` — Order, OrderItem, Coupon, CouponRedemption, WalletTransaction, FlashSale, Bundle
- `apps/courses/0001-0002` — Category, Course, Topic, Lesson, Enrollment, LessonProgress
- `apps/videos/0001` — Video, VideoAccessToken, VideoAccessLog
- `apps/notifications/0001-0002` — HomepageBanner, NotificationTemplate, Campaign

---

## Phase 4 Scope (ETL)

1. Fix psycopg2 → pymysql for MariaDB WP database connection
2. ETL passes 1-7: users, categories, courses, quizzes, attempts, orders, wallet
3. Master `etl_run_all` command + `etl_validate` count checker
4. Add `ACADEMIC_YEAR_MAP` (first_secondary→1st etc.)

---

## Running Phase 3

```bash
cd E:\Elkaed\backend
python manage.py migrate
python manage.py runserver

# Celery worker (separate terminal)
celery -A config worker -l info

# Create a flash sale via admin, then test:
curl -X GET http://localhost:8000/api/commerce/flash-sales/
```

## API Quick Reference (Phase 3 additions)

```
GET  /api/quizzes/<id>/
POST /api/quizzes/<id>/start/
POST /api/quizzes/attempts/<id>/submit/   {answers: [{question_id, answer}]}
GET  /api/quizzes/attempts/<id>/

POST /api/videos/<lesson_id>/token/
GET  /api/videos/key/<token>/
POST /api/videos/<lesson_id>/progress/   {position_seconds, completed}

GET  /api/commerce/flash-sales/
GET  /api/commerce/bundles/
POST /api/commerce/bundles/<id>/purchase/

POST /api/courses/bulk-enroll/           {course_id, phones: [...]}

PATCH /api/auth/profile/                 {first_name, last_name, guardian_phone}
POST  /api/auth/create-student/          {phone, first_name, last_name, academic_year, student_type}
GET   /api/auth/analytics/
```
