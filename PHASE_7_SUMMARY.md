# Phase 7 — Remaining Features Summary

**Date:** 2026-07-15  
**Status:** ✅ All migrations applied, `manage.py check` 0 issues

---

## What Was Built

### Agent 1 — Address Book (users app)

**New model:** `ShippingAddress` in `apps/users/models.py`
- FK to User, label, governorate (10 Egyptian choices), city, street, is_default
- Ordering: default-first, then by label
- Migration: `users/migrations/0003_add_shipping_address.py`

**New API endpoints:**

| Route | Method | Notes |
|-------|--------|-------|
| `/api/auth/addresses/` | GET | List own addresses |
| `/api/auth/addresses/` | POST | Create new address (auto-sets default if first) |
| `/api/auth/addresses/<id>/` | GET | Retrieve single address |
| `/api/auth/addresses/<id>/` | PATCH | Update address |
| `/api/auth/addresses/<id>/` | DELETE | Remove address |
| `/api/auth/addresses/<id>/set-default/` | POST | Mark as default (unsets others) |

---

### Agent 2 — Customer Communication (users/admin.py)

**New admin action:** `send_whatsapp_to_selected` on UserAdmin

Flow:
1. Admin selects users in the Django admin user list
2. Chooses "إرسال رسالة واتساب للمنتخبين"
3. Redirected to `/django-admin/users/user/send-whatsapp/?ids=1,2,3`
4. Types message in the Arabic-labeled textarea
5. Submits → fires `send_whatsapp_task.delay()` per user via Celery
6. Redirected back to user list with success count

**New file:** `apps/users/templates/admin/users/send_whatsapp.html`
- Extends `admin/base_site.html` — uses Django admin styling
- Displays user count, CSRF-protected form, cancel link

---

### Agent 3 — Email Order Notifications + Enrollment Cap

**Email for order status** (`commerce/models.py` signal):
- `order_status_changed` now also calls `send_mail(fail_silently=True)` when `instance.user.email` is set
- Fires alongside the existing WhatsApp notification
- Subject: `تحديث حالة طلبك #{id} — القائد`

**Enrollment cap** (`courses/models.py`):
- Added `max_students = PositiveIntegerField(default=0)` to Course (0 = unlimited)
- Migration: `courses/migrations/0004_add_max_students.py`

**Enrollment cap check** (`courses/views.py`):
- `_check_enrollment_cap(course)` helper: if `max_students > 0` and active enrollments >= limit, fires `notify_admins_task`
- Called in both `EnrollView` success paths (free + wallet)
- Called in `KangaPayWebhookView` webhook loop (only when `created=True`)

**Admin notification task** (`notifications/tasks.py`):
- `notify_admins_task(message)` — sends WhatsApp to all `role__in=('admin','staff')` active users

---

## CLAUDE.md Checklist — Final Status

### Backend features
| Feature | Status |
|---------|--------|
| Email notifications for order status changes | ✅ Done (Phase 7) |
| Automatic low-stock/enrollment cap notifications for admins | ✅ Done (Phase 7) |
| Address book management | ✅ Done (Phase 7) |
| Order notification preferences | ✅ Done (Phase 6) |
| Frontend email verification/password reset components | ❌ Frontend — out of scope for backend phase |

### Admin dashboard
| Feature | Status |
|---------|--------|
| Customer List: search/filter | ✅ Done (Phase 5 — UserAdmin) |
| Customer Detail: history inlines | ✅ Done (Phase 5 — UserAdmin) |
| Customer Segments: behavior groups | ✅ Done (Phase 5 — SegmentFilter + ChurnFilter) |
| Customer Communication: send messages | ✅ Done (Phase 7 — bulk WhatsApp action) |
| Customer Analytics: LTV, churn | ✅ Done (Phase 5 — lifetime_value + ChurnFilter) |
| Banner Management UI | ✅ Done (Phase 5 — HomepageBannerAdmin) |
| Email Campaigns | ✅ Done (Phase 5 — EmailCampaignAdmin with trigger action) |
| Flash Sales | ✅ Done (Phase 5 — FlashSaleAdmin) |
| Bundle Deals | ✅ Done (Phase 5 — BundleAdmin) |

---

## Phase 8 Candidates

1. **ETL pass 8+** — migrate quiz content, lesson progress from WordPress DB
2. **Frontend** — React components for email verification / password reset flows
3. **Celery Beat** — scheduled tasks (Redis required in prod): low-wallet alerts, expiry reminders
4. **Customer segment analytics API** — aggregate LTV/churn by segment (extend AdminAnalyticsView)
5. **Video resumption** — store `last_position_seconds` and resume on next open
6. **Production hardening** — Redis setup, static files (WhiteNoise/S3), email backend (SMTP)
