# Phase 6 — API Completeness Summary

**Date:** 2026-07-15  
**Branch:** main (no git)  
**Status:** ✅ All 8 new endpoints live, migrations applied, `manage.py check` clean

---

## What Was Missing (Pre-Phase 6 Audit)

Six categories identified in the Phase 5 → Phase 6 handoff:

1. Homepage banner API
2. Notification preferences API
3. Instructor courses view
4. Course student roster
5. Lesson watchlist (bookmark)
6. Order history for students
7. Quiz CSV export for instructors

---

## What Was Built (3 Parallel Agents)

### Agent 1 — Notifications App

| File | Action |
|------|--------|
| `apps/notifications/serializers.py` | NEW — `BannerSerializer`, `NotificationPreferenceSerializer` |
| `apps/notifications/views.py` | NEW — `BannerListView`, `NotificationPreferenceView` |
| `apps/notifications/urls.py` | NEW — registered both views |
| `config/urls.py` | Added `api/notifications/` route |

**BannerListView:** `GET /api/notifications/banners/` — active banners with scheduling
(`starts_at`/`ends_at` Q-filter), public, ordered by `order` field.

**NotificationPreferenceView:**
- `GET /api/notifications/preferences/` — returns all 4 pref types with `enabled` state (defaults True if no DB row)
- `PATCH /api/notifications/preferences/` — accepts `{}` (single) or `[{}]` (list), idempotent upsert

---

### Agent 2 — Courses App (Instructor + Watchlist)

| File | Action |
|------|--------|
| `apps/courses/models.py` | `LessonWatchlist` model appended |
| `apps/courses/serializers.py` | Added `WatchlistSerializer`, `InstructorCourseSerializer`, `EnrollmentStudentSerializer` |
| `apps/courses/views.py` | Added `WatchlistToggleView`, `InstructorCoursesView`, `CourseStudentsView` |
| `apps/courses/urls.py` | 4 new routes |
| `apps/courses/migrations/0003_add_lesson_watchlist.py` | Migration created + applied |

**Watchlist:**
- `GET /api/courses/watchlist/` — list all bookmarks for current user
- `POST /api/courses/watchlist/<lesson_id>/` — toggle: adds if new, removes if exists (returns `{"status":"removed"}` on delete)

**Instructor views:**
- `GET /api/courses/instructor/` — instructor's own courses with `enrollment_count` annotation
- `GET /api/courses/instructor/<course_id>/students/` — active enrollments with student phone/name/year

---

### Agent 3 — Commerce + Quizzes

| File | Action |
|------|--------|
| `apps/commerce/serializers.py` | Added `OrderItemSerializer`, `OrderSerializer` (nested items) |
| `apps/commerce/views.py` | Added `OrderListView` |
| `apps/commerce/urls.py` | Added `orders/` route |
| `apps/quizzes/views.py` | Added `QuizExportView` (CSV, UTF-8 BOM) |
| `apps/quizzes/urls.py` | Added `<quiz_id>/export/` route |

**Order history:**
- `GET /api/commerce/orders/` — student's own orders, prefetch items, newest first

**Quiz CSV export:**
- `GET /api/quizzes/<quiz_id>/export/` — instructor or admin only
- Columns: رقم الهاتف, الاسم, الحالة, النتيجة, الدرجة, من, تاريخ البدء
- `Content-Type: text/csv; charset=utf-8-sig` (Excel-compatible BOM)

---

## Complete API Map After Phase 6

```
GET    /api/auth/send-otp/
POST   /api/auth/verify-otp/
POST   /api/auth/refresh/
GET    /api/auth/me/
PATCH  /api/auth/me/update/

GET    /api/courses/
GET    /api/courses/<slug>/
POST   /api/courses/<id>/enroll/
GET    /api/courses/my-enrollments/
POST   /api/courses/bulk-enroll/
GET    /api/courses/watchlist/                       ← NEW
POST   /api/courses/watchlist/<lesson_id>/           ← NEW (toggle)
GET    /api/courses/instructor/                      ← NEW
GET    /api/courses/instructor/<course_id>/students/ ← NEW

GET    /api/quizzes/<quiz_id>/
POST   /api/quizzes/<quiz_id>/start/
POST   /api/quizzes/attempts/<attempt_id>/submit/
GET    /api/quizzes/attempts/<attempt_id>/
GET    /api/quizzes/<quiz_id>/export/                ← NEW (CSV)

GET    /api/commerce/wallet/
POST   /api/commerce/coupons/redeem/
POST   /api/commerce/kanga-pay/webhook/
GET    /api/commerce/flash-sales/
GET    /api/commerce/bundles/
POST   /api/commerce/bundles/<id>/purchase/
GET    /api/commerce/orders/                         ← NEW

GET    /api/videos/<lesson_id>/token/

GET    /api/notifications/banners/                   ← NEW
GET    /api/notifications/preferences/               ← NEW
PATCH  /api/notifications/preferences/               ← NEW
```

---

## Entry Requirements for Phase 7

- ✅ All migrations applied (`courses.0003_add_lesson_watchlist`)
- ✅ `manage.py check` passes (0 issues)
- ✅ `CELERY_TASK_ALWAYS_EAGER=True` in dev — Celery/Redis not required
- ✅ `SITE_URL` configured in base.py
- ✅ All 8 new endpoints wired in urlconf

### Phase 7 Candidates

Based on MIGRATION_BLUEPRINT.md remaining items:

1. **Frontend components** — email verification, password reset flows
2. **Low-stock / auto notifications** — Celery beat (needs Redis in prod)
3. **Address book management** — shipping address CRUD
4. **ETL pass 8+** — migrate quiz content, lesson progress from WP
5. **Admin Customer Management UI** — list, detail, segments (CLAUDE.md checklist)
6. **Email Campaigns admin UI** — `EmailCampaign` model exists, needs admin action + trigger
7. **Flash Sales admin UI** — already has model + API, needs admin trigger endpoint
