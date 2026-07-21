# PROMPT FOR CLAUDE CODE — Hybrid Student System (Center ↔ Online Bridge)

> Context: You are working on the Elkaed.online migration (Django REST + React SPA). All phases in `MIGRATION_BLUEPRINT.md` are complete: phone-based WhatsApp OTP auth, wallet system, Kanga Pay, course/lesson/quiz models, video protection (4-view limit, HLS), Arabic-first RTL UI, Celery + Redis. Read `MIGRATION_BLUEPRINT.md` before starting. Follow the existing code conventions, Arabic-first UI, and the existing wallet/WhatsApp services — do NOT rebuild them, extend them.

## GOAL

The platform serves an Egyptian history private tutor with TWO student sources that must live in one system:

1. **Online students** — self-register on the website, buy video courses with wallet/Kanga Pay.
2. **Center students** — register physically at the course center, are bulk-imported by admins, attend in person, and only use the website for results, materials, and missed-lesson videos.

The core new idea: **connect physical attendance to the platform.** Absence at the center triggers an automatic WhatsApp message with the missed lesson's video link, and the lesson price is deducted from the student's wallet.

---

## FEATURE 1 — Extended Online Registration

Extend the existing phone-based registration form to collect:

- Full name (first + last)
- Student phone (primary identifier — unchanged)
- Guardian/parent phone (required)
- Academic year (1st / 2nd / 3rd secondary)
- Student type: `online` (self-registration always creates `online`)
- Governorate / school name (optional fields — make them admin-configurable: admin can toggle which optional fields appear on the form)

Keep the existing WhatsApp OTP verification flow. Add backend validation (11-digit Egyptian phone for both student and guardian, guardian ≠ student phone).

## FEATURE 2 — Admin CSV Bulk Import (Center Students)

New admin dashboard page: **"استيراد طلاب السنتر" (Import Center Students)**.

- Admin uploads a CSV. Required columns: `first_name, last_name, student_phone, guardian_phone, academic_year, initial_wallet_balance`. Optional: `center_group` (e.g., which day/time group they attend), `notes`.
- Provide a downloadable CSV template from the admin page.
- For each row:
  1. Validate phone format + uniqueness. Collect all row errors and show a per-row validation report BEFORE committing anything (dry-run preview → confirm → import). Never partially import silently.
  2. Create the user with `student_type='center'`, phone as identifier.
  3. Generate a strong random password (e.g., 10+ chars, unambiguous charset — no 0/O, 1/l).
  4. Credit `initial_wallet_balance` to their wallet with a ledger entry (`source='csv_import'`).
  5. Queue a WhatsApp message via Celery (respect wa-ma.org rate limits, exponential backoff — reuse the existing WhatsApp service):
     - Arabic message: welcome, "you've been registered", the site link, their phone as username, and the generated password, plus a note to change it after first login.
- Import runs as a Celery task with a progress/status view in admin (imported / failed / pending counts). Store an `ImportBatch` record with the uploaded file, admin who ran it, timestamp, and per-row results.
- Force password change on first login for CSV-created accounts (flag on user).

## FEATURE 3 — Student Portal (Single Page, Tabbed)

One portal page at `/portal` (React, RTL Arabic-first) with tabs. Same portal for both student types, but tabs adapt to `student_type`:

Tabs (all students):
1. **النتائج (Results)** — quiz/exam attempts with scores, per-course breakdown. Reuse existing quiz attempt data.
2. **الملفات (Materials/Info)** — downloadable files/PDFs the teacher uploads (notes, summaries). New `Material` model: title_ar, file, academic_year targeting, optional course link, visibility by student_type.
3. **الدروس (Lessons)** — courses/lessons the student has access to (purchased, enrolled, or granted via absence link).
4. **المراجعات (Revisions)** — same as materials/lessons but a separate content type `revision` uploaded by the teacher (video or file). Model it as a category/flag on existing content rather than duplicating the video pipeline.
5. **حسابي (Account)** — profile info, guardian phone, wallet balance, full wallet transaction history (credits, deductions, purchases, absence deductions — each with a clear Arabic label), change password.

Additional for `online` students (and center students may also see it — see Feature 4):
6. **الجديد (Feed)** — YouTube-style feed of newly published videos/courses, newest first, thumbnail grid, filtered by the student's academic year.
7. **المتجر (Store)** — purchasable videos/courses as products; add to cart, checkout with wallet (existing flow) or Kanga Pay fallback.
8. **كورساتي (My Courses)** — everything purchased/granted, with access. Video playback uses the EXISTING protection (4-view limit) — do not touch it.

## FEATURE 4 — Center Students Can Also Buy

Center students see the Store and can purchase online lessons with their wallet like online students. No restrictions — the difference is only defaults (their wallet is mainly consumed by physical attendance).

## FEATURE 5 — Attendance ↔ Wallet ↔ WhatsApp (THE CORE FEATURE)

### Models
- `CenterGroup`: name_ar, academic_year, day/time description, lesson_price override (nullable → falls back to global).
- `PhysicalSession`: group FK, date, title_ar, `linked_lesson` (FK to an online lesson/video — the recording or equivalent of what was taught), lesson_price (snapshot at creation, editable).
- `AttendanceRecord`: session FK, student FK, status ∈ {present, absent, absent_excused, makeup} , `deducted` bool, `whatsapp_sent` bool, `overridden_by` (admin FK, nullable), notes.

### Pricing settings (admin-configurable — NOTHING hardcoded)
Global `PricingSettings` (singleton or per-academic-year):
- `single_lesson_price` (default 80 EGP)
- `monthly_package_price` (default 280 EGP) + `package_lesson_count` (default 4)
- Overridable per CenterGroup and per PhysicalSession.

### Flow
1. Admin creates a `PhysicalSession` for a group, attaches the lesson video link (an existing lesson on the platform).
2. Admin takes attendance: a fast mobile-friendly checklist of the group's students (default all present; tap to toggle). Support marking after the fact.
3. On marking **present** → deduct `lesson_price` from wallet, ledger entry "حضور: {session title}".
4. On marking **absent** → deduct `lesson_price` AND queue a WhatsApp message (Celery) to the STUDENT (and optionally guardian — admin toggle in settings) with: session title, and a direct link to the linked lesson video. Grant the student access to that specific lesson (so the 4-view protection applies to it like a purchased lesson). Ledger entry "غياب — إرسال الدرس أونلاين: {session title}".
5. On **absent_excused** → NO deduction, NO WhatsApp link (student attended another time / declined online). Admin picks this instead of absent.
6. **Override tools**: admin can, per record: refund a deduction, resend the WhatsApp link, revoke granted access, change status after the fact (changing status reverses/applies the money correctly — make this idempotent and ledger-driven, never mutate balance directly).
7. Insufficient balance on deduction → allow wallet to go NEGATIVE (configurable setting: allow_negative_balance, default true) and flag the student in an admin "متأخرات" (arrears) report, OR block and flag — admin setting decides. Portal shows the negative balance clearly to the student.

### Admin views
- Attendance sheet per session (the checklist).
- Per-student attendance + wallet history.
- Arrears report (negative balances).
- Batch actions: mark whole group present, apply monthly package credit to a whole group.

## FEATURE 6 — Wallet Ledger Hardening

All money movement (CSV credit, package credit, purchase, attendance deduction, absence deduction, refund/override) must go through ONE wallet service with an append-only `WalletTransaction` ledger: amount, direction, reason code, related object (generic FK), created_by. Balance = derived or cached-but-reconcilable. Add a management command to reconcile balances against the ledger.

## FEATURE 7 — Per-Student Discounts & Free Attendance

The wallet is the ONE universal currency: a student who tops up 1000 EGP can spend it on online lessons AND physical attendance interchangeably. On top of that, add per-student pricing adjustments:

- `StudentDiscount` model: student FK, type ∈ {percentage, fixed_amount, free}, value, scope ∈ {physical_only, online_only, both}, `reason` (REQUIRED text note — admin must write why: e.g., "ابن زميل", "حالة اجتماعية", "متفوق"), active bool, optional start/end dates, created_by (admin FK).
- Applied automatically at deduction/purchase time: `free` → 0 EGP deduction (attendance still recorded, ledger entry with amount 0 and reason "معفى"), percentage/fixed → adjusted price on the ledger entry.
- The ledger entry must store BOTH the original price and the discounted price, plus a link to the discount that was applied — so analytics can report gross vs net revenue correctly.
- Admin payment/pricing page: list of discounted students, their discount, the reason, who granted it, since when. Add/edit/revoke from there.
- Portal: student sees their discounted price, not the mechanics.

## FEATURE 8 — Audit Log (Monitoring System)

Everything money- or access-related must be traceable so manual edits never silently corrupt payment analytics:

- `AuditLog` model (append-only, no update/delete ever): actor (admin/assistant FK), action (created/updated/deleted/overridden/refunded/discount_granted/discount_revoked/attendance_changed/csv_imported/access_granted/access_revoked...), target (generic FK), timestamp, `before` and `after` JSON snapshots of the changed fields, optional note.
- Automatically written by the wallet service, discount service, attendance flows, CSV import, and manual admin edits to prices/settings — implement as a service-layer call (not signals scattered everywhere) so it's consistent.
- Admin "سجل العمليات" (Activity Log) page: filterable by actor, action type, student, date range. Read-only.
- Analytics must be computed from the LEDGER (with gross/net and reason codes), never from mutable fields — so revenue reports distinguish: real revenue, discounts given, refunds/overrides, free attendances. Add a simple revenue report view: per day/week/month — gross, discounts, net, broken down by physical vs online.
- Deleting is never physical for financial records: use soft-delete/reversal entries only.

## FEATURE 9 — QR Code Attendance Scanning

Each student gets a unique QR code on their profile; assistants scan it at the center door to take attendance automatically.

### QR identity
- On user creation (signup OR CSV import), generate a unique opaque token (e.g., UUID or signed short code) — NEVER encode the raw phone number or user ID in the QR. Store as `attendance_token` on the user, with an admin action to regenerate it (invalidates the old QR if a card is lost/shared).
- QR content: just the token string (or a short URL containing it). Keep it plain text so cheap hardware scanners read it.
- Student portal → Account tab: shows their QR code full-screen (brightness-friendly, works from a phone screen), plus a "download/print card" button that renders a printable ID card (name, academic year, group, QR) — PDF, so the center can print physical cards.
- Admin: bulk-print cards for a whole CenterGroup (one PDF, one card per page or 8-up layout).

### Scanning page (admin dashboard)
- New page: **تسجيل الحضور بالمسح (Scan Attendance)**. Admin/assistant selects the active `PhysicalSession` (default: today's session for the selected group), then the page holds focus on a hidden input.
- **Primary hardware: USB barcode/QR scanner (keyboard-wedge)** — these type the code + Enter like a keyboard. So the implementation is simply: capture input, on Enter → submit token. No drivers, no special API. This is the supermarket-scanner mode and must work flawlessly.
- **Fallback: phone/laptop camera** — same page offers a camera mode using a JS QR library (e.g., `html5-qrcode` or `zxing-js`), for when the hardware scanner isn't available.
- On each successful scan:
  - Mark the student **present** on the session (triggering the normal Feature 5 flow: deduction, ledger, discounts applied).
  - Show instant visual + audio feedback: big green card with student name, photo (if any), group, wallet balance after deduction — and a distinct RED card + error sound for problems.
  - Error cases to handle explicitly: token not found / regenerated, student not in this group (offer one-tap "mark as makeup — no deduction" per Feature 5 rules, or add to session anyway per admin choice), already scanned for this session (idempotent — show "already present", no double deduction), insufficient balance (follow the negative-balance setting, but show it loudly in orange).
- Keep a live counter on the page: scanned / expected, with the remaining unscanned list one tap away — at session close, admin reviews the unscanned list and marks absent / absent_excused in bulk (feeding the absence → WhatsApp flow).
- Scans work fast in sequence (assistants scan a line of students): the input refocuses automatically after every scan, API endpoint must respond < 300ms, and every scan writes to the AuditLog.
- Manual search-by-name/phone stays available on the same page for students who forgot their card/phone.

---

## NON-FUNCTIONAL REQUIREMENTS

- Arabic-first: every new admin page and portal tab fully in Arabic (i18next keys for both ar/en, ar complete).
- All WhatsApp sends via Celery with retry + backoff; never send synchronously in a request.
- Permissions: only admin/assistant roles can import CSV, take attendance, override. Add an `assistant` role if not present (limited admin: attendance + import only, no pricing/settings).
- Tests: unit tests for wallet service (deduct, refund, idempotent status changes, negative balance), CSV import validation, and the absence → WhatsApp + access-grant flow (mock wa-ma.org).
- Migrations must be additive — do not break existing models.

## DELIVERY ORDER

1. Wallet ledger service + PricingSettings + AuditLog service (Feature 8 foundations first — everything else writes to it)
2. Discount system (Feature 7) wired into the wallet service
3. CSV import (models, Celery task, admin UI)
4. Attendance models + flows + WhatsApp integration
5. QR attendance scanning (tokens, printable cards, scan page — hardware scanner mode first, camera second)
6. Student portal tabs (results, materials, lessons, revisions, account)
7. Feed + Store adjustments for both student types
8. Tests + arrears report + revenue report + override tools

Ask me before making assumptions about anything payment- or access-related. Start by proposing the models + API endpoints for review before writing implementation code.
