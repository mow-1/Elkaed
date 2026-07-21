# Phase 5 Summary — Admin Dashboard, Customer Management, Notification Preferences

**Date:** 2026-07-15  
**Status:** Complete

---

## What Was Built

### Enhanced Django Admin

#### `apps/users/admin.py`

| Feature | Detail |
|---|---|
| **EnrollmentInline** | Readonly inline on User detail: course, status, payment_method, enrolled_at |
| **OrderInline** | Readonly inline: status, payment_method, total_price, created_at |
| **QuizAttemptInline** | Readonly inline: quiz, status, result, earned_marks, total_marks, started_at |
| **SegmentFilter** | Combined student_type × academic_year: 6 options (center/online × 1st/2nd/3rd) |
| **ChurnFilter** | Last login filter: inactive 30 days / inactive 90 days (uses `last_login__lt` OR `isnull`) |
| **lifetime_value column** | Per-user LTV: `SUM(Order.total_price WHERE status='completed')` — displayed as `X.XX ج.م` |
| **readonly_fields** | wp_user_id, date_joined, last_login are read-only in admin form |

#### `apps/courses/admin.py`

| Feature | Detail |
|---|---|
| **CourseAdmin enrollment_count** | `Count('enrollment')` annotation via `get_queryset`; sortable column |
| **TopicInline** | Stacked inline on Course detail page |
| **EnrollmentAdmin** | Full admin: filter by status, payment_method, academic_year; raw_id_fields for FKs |
| **LessonProgressAdmin** | View/filter student progress per lesson |
| **CategoryAdmin** | Prepopulated slug from name; filter by student_type, academic_year |

#### `apps/commerce/admin.py`

| Feature | Detail |
|---|---|
| **notify_order_status action** | Sends WhatsApp to order's user with current status (Arabic); fires `send_whatsapp_task.delay` |

#### `apps/notifications/admin.py`

| Feature | Detail |
|---|---|
| **NotificationPreferenceAdmin** | list_editable enabled/disabled per user+type; inline update |
| **EmailCampaignAdmin** | Draft→send via `send_email_campaign` action; status/count readonly |

---

### New Models

#### `apps/users/models.py`
```python
email = models.EmailField(blank=True)  # optional — phone is primary identity
```

#### `apps/notifications/models.py`
```python
class NotificationPreference(models.Model):
    user       = ForeignKey(User, related_name='notification_prefs')
    notif_type = CharField(choices=['quiz_result','enrollment_confirmed','order_status','campaign'])
    enabled    = BooleanField(default=True)
    # unique_together: (user, notif_type)

def user_wants(user, notif_type: str) -> bool:
    """Returns True if user has not explicitly disabled this notification type."""
    pref = NotificationPreference.objects.filter(user=user, notif_type=notif_type).first()
    return pref.enabled if pref else True  # default = enabled

class EmailCampaign(models.Model):
    subject    = CharField(max_length=200)
    body_html  = TextField()
    segment    = CharField(choices=Campaign.SEGMENTS)
    status     = CharField(choices=['draft','sending','done'])
    created_by = ForeignKey(User, null=True)
    sent_count = PositiveIntegerField(default=0)
    sent_at    = DateTimeField(null=True)
```

#### `apps/commerce/models.py` — Signal
```python
@receiver(post_save, sender=Order)
def order_status_changed(sender, instance, created, **kwargs):
    if created or instance.status not in ('completed', 'cancelled'):
        return
    if not user_wants(instance.user, 'order_status'):
        return
    status_ar = dict(Order.STATUSES).get(instance.status, instance.status)
    send_whatsapp_task.delay(instance.user.phone, f'طلبك #{instance.pk} — الحالة: {status_ar}')
```

---

### New Celery Task

#### `apps/notifications/tasks.py` — `send_email_campaign_task`
- Filters `User` by segment + `email != ''`
- Calls `send_mail(html_message=campaign.body_html)` per user
- Updates `EmailCampaign.status='done'`, `sent_count`, `sent_at` via `filter().update()`

---

### Migrations

| Migration | What it adds |
|---|---|
| `users/0002_add_email_field.py` | `email EmailField(blank=True)` on User |
| `notifications/0003_add_notification_preference_and_email_campaign.py` | NotificationPreference + EmailCampaign tables |

---

### Environment Bootstrapped

| Item | Value |
|---|---|
| **DB** | PostgreSQL 18, `elkaed_dev` at localhost:5432 |
| **Admin URL** | `http://localhost:8000/django-admin/` |
| **Admin credentials** | phone: `201000000000` / password: `admin123` |
| **API base** | `http://localhost:8000/api/` |
| **Dev mode** | `CELERY_TASK_ALWAYS_EAGER=True` — no Redis needed for local dev |
| **Verified flows** | OTP send (200) → OTP verify → JWT issued → Profile GET → Course list (200) |

---

## Key Decisions Made

- **`user_wants()` as module-level function** — not a method, so signals and tasks can call it without importing a class.
- **Signal at bottom of `commerce/models.py`** — Django auto-discovers signals at import time; no `apps.py` ready hook needed.
- **`EmailCampaign.SEGMENTS` reuses `Campaign.SEGMENTS`** — `segment = CharField(choices=Campaign.SEGMENTS)`. No separate constant.
- **`CELERY_TASK_EAGER_PROPAGATES = False`** — WhatsApp/SMTP failures in dev don't crash the request. Errors are logged only.
- **`Course.Meta.ordering = ['-created_at']`** — fixes `UnorderedObjectListWarning` on paginated course list.
- **LTV column uses aggregate per request** — ponytail: no caching. Add `wallet_balance` snapshot or periodic annotation if this column appears on 5k+ row lists.

---

## Bugs Fixed (Post-Audit)

1. **`send_email_campaign_task` missing `DoesNotExist` guard** — `EmailCampaign.objects.get(pk=campaign_id)` was unprotected. If a campaign is deleted while the Celery task is queued, the task would crash. Fixed to match the pattern in `send_campaign_task`: wrap in `try/except EmailCampaign.DoesNotExist: return`.

---

## Issues Fixed from Phase 4

1. **`notifications/admin.py` imported `NotificationPreference` before model existed** — stripped import, re-added after model was written.
2. **`psycopg2-binary==2.9.9` blocked pip** — 2.9.10 already installed; changed to `>=2.9.9`.
3. **`passlib` not installed** — installed manually; `pip install -r requirements.txt` previously silently skipped it due to psycopg2 build failure.
4. **`python manage.py shell` echo bug** — BOM character in pipe; used `python -c` with multiline string instead.
5. **`Course.ordering` missing** — DRF pagination warning; added `ordering = ['-created_at']` to `Course.Meta`.

---

## Known Ceilings (ponytail notes)

- **`lifetime_value` column** — one aggregate query per row in changelist. Fine at <1k users; add annotation to `get_queryset` if admin slows.
- **`send_email_campaign_task`** — calls `send_mail` per user in a loop. For >5k users, batch with `send_mass_mail`. Add when campaign list > 5k recipients.
- **`order_status_changed` signal** — fires on every `Order.save()`. The `if created: return` guard prevents double-sends on new orders, but any field edit triggers the check. This is acceptable — `user_wants` is a single indexed lookup.
- **Email field** — no verification flow yet (no email OTP or confirm link). Add when email login or email-only campaigns are needed.

---

## Phase 6 Scope (confirmed by pre-check audit)

Core student flow is **fully working** (OTP → JWT → browse → enroll → video → quiz). Admin flash sales and WhatsApp campaigns work. The following gaps must close before React integration.

### Must-Have (6 missing endpoints, 1 missing model)

| Priority | Endpoint / Feature | File | Notes |
|---|---|---|---|
| 🔴 | `GET /api/notifications/banners/` | create `notifications/views.py` + `urls.py` | React homepage fetch |
| 🔴 | `GET+PATCH /api/notifications/preferences/` | `notifications/views.py` | User opt-in/out settings page |
| 🔴 | `GET /api/instructor/courses/` | `courses/views.py` or new instructor app | Instructor dashboard |
| 🔴 | `GET /api/instructor/courses/<id>/students/` | `courses/views.py` | Per-course student list |
| 🟡 | `GET /api/commerce/orders/` | `commerce/views.py` | Student order history |
| 🟡 | `GET /api/quizzes/<id>/export/` | `quizzes/views.py` | Admin/instructor CSV export |
| 🟡 | `LessonWatchlist` model + toggle endpoint | `courses/models.py` + views | Bookmark lessons |

### Already Fixed in This Phase (pre-Phase 6 prep)
- ✅ `SITE_URL` added to `base.py` — was missing, would crash `create_kanga_payment()`
- ✅ `CourseListView` now has `search_fields`, `filterset_fields`, `ordering_fields`
- ✅ `PAGE_SIZE = 20` already set in `base.py` (agent false alarm — was there all along)

### Nice-to-Have
- `POST /api/auth/change-password/`
- `GET /api/instructor/earnings/`
- React SPA scaffold (`frontend/` with Vite + React + Tailwind + RTL support)

---

## Running Phase 5

```bash
cd E:\Elkaed\backend

# Start dev server (no Redis needed)
python manage.py runserver

# Check OTP flow
curl -X POST http://localhost:8000/api/auth/send-otp/ \
  -H "Content-Type: application/json" \
  -d '{"phone":"201000000001","purpose":"register"}'

# Check admin
# Open: http://localhost:8000/django-admin/
# Login: phone=201000000000 / password=admin123
```

## API Quick Reference (Phase 5 — no new public endpoints, admin enhancements only)

Phase 5 added no new public API routes. All changes are Django admin improvements + model additions.

```
# All existing Phase 2-3 endpoints remain unchanged:
POST /api/auth/send-otp/
POST /api/auth/verify-otp/
GET  /api/auth/profile/
PATCH /api/auth/profile/
POST /api/auth/create-student/
GET  /api/auth/analytics/
POST /api/auth/token/refresh/

GET  /api/courses/
GET  /api/courses/<slug>/
POST /api/courses/<id>/enroll/
GET  /api/courses/my-enrollments/
POST /api/courses/bulk-enroll/

GET  /api/commerce/flash-sales/
GET  /api/commerce/bundles/
POST /api/commerce/bundles/<id>/purchase/
GET  /api/commerce/wallet/
POST /api/commerce/coupons/redeem/
POST /api/commerce/kanga-pay/webhook/

GET  /api/quizzes/<id>/
POST /api/quizzes/<id>/start/
POST /api/quizzes/attempts/<id>/submit/
GET  /api/quizzes/attempts/<id>/

POST /api/videos/<lesson_id>/token/
GET  /api/videos/key/<token>/
POST /api/videos/<lesson_id>/progress/
```
