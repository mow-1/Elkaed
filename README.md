# القائد (Elkaed.online)

Django REST + React SPA platform for an Egyptian history tutor — phone/WhatsApp OTP auth,
wallet system, Kanga Pay, video courses, and a hybrid center/online student system
(attendance, QR scanning, CSV import). Migrated from a WordPress + Tutor LMS + WooCommerce
site — see `MIGRATION_BLUEPRINT.md` for the full architecture and migration history.

## Stack

- **Backend**: Django 5 + Django REST Framework, PostgreSQL, Celery (Redis broker), JWT auth
- **Frontend**: React 19 + Vite, plain `fetch`, CSS Modules, RTL Arabic-first

## Prerequisites

- Python 3.11+
- Node 20+
- PostgreSQL (running locally, or a connection string to one)
- Redis (optional in dev — Celery runs tasks synchronously via `CELERY_TASK_ALWAYS_EAGER`
  when nothing else is configured, so you don't need Redis running just to develop)

## Backend setup

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

pip install -r requirements.txt

copy .env.example .env       # Windows
# cp .env.example .env       # macOS/Linux
```

Edit `backend/.env` and fill in at least:

| Variable | Required for | Notes |
|---|---|---|
| `SECRET_KEY` | Always | Any random string in dev |
| `DB_NAME` / `DB_USER` / `DB_PASSWORD` / `DB_HOST` / `DB_PORT` | Always | Postgres connection |
| `REDIS_URL` | Celery/cache | Defaults to `redis://localhost:6379/0`; not required in dev (see above) |
| `WAMA_API_KEY` | WhatsApp OTP/notifications | Without it, sends are logged and skipped, not sent |
| `KANGA_PAY_*` | Payment checkout | Only needed to test the Kanga Pay flow |
| `AWS_*` / `CLOUDFRONT_*` | Video storage/CDN | Only needed for the self-hosted video pipeline |
| `SITE_URL` | Links in WhatsApp messages | e.g. `http://localhost:5173` in dev |

Create the database (Postgres), then:

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

The API is at `http://localhost:8000/`, Django admin at `http://localhost:8000/django-admin/`.

Run the test suite:

```bash
python manage.py test
```

## Frontend setup

```bash
cd frontend
npm install
copy .env.example .env    # Windows
# cp .env.example .env    # macOS/Linux
npm run dev
```

`frontend/.env`:

```
VITE_API_URL=http://localhost:8000
```

The app runs at `http://localhost:5173/`.

Other frontend commands:

```bash
npm run build     # production build
npm run lint      # oxlint
npm run preview   # preview a production build locally
```

## Project layout

```
backend/
  apps/
    users/        phone auth, OTP, CSV import, customer admin API
    courses/      courses, lessons, enrollments, materials
    videos/       encrypted HLS video access (tokens, view limits)
    quizzes/      quizzes, attempts, grading
    commerce/     wallet ledger, orders, Kanga Pay, coupons, bundles
    notifications/  WhatsApp/email sending, campaigns, landing page content
    attendance/   center groups, sessions, attendance↔wallet↔WhatsApp, discounts, pricing
    audit/        append-only audit log
    etl/          one-off WordPress → Django migration scripts
  config/         settings, urls, celery app

frontend/
  src/
    pages/        top-level routed pages (Landing, Login, Register, Dashboard, Portal, AdminPanel, ...)
    components/
      admin/       admin-panel tabs (customers, attendance, scan, CSV import, reports, ...)
      portal/      student-portal tabs (results, materials, lessons, store, ...)
    api/           one file per backend app, flat fetch-wrapper functions
    context/       auth context
```

## Notes for new contributors

- Arabic strings are hardcoded directly in JSX throughout — there's no i18n framework, by
  design (see `MIGRATION_BLUEPRINT.md` and the hybrid-student plan for why).
- All wallet balance changes must go through `apps/commerce/services.py` (`wallet_credit`/
  `wallet_debit`) — never mutate `User.wallet_balance` directly, it needs a matching
  `WalletTransaction` ledger row.
- DRF's default pagination (`PageNumberPagination`) applies to every `generics.List*APIView`
  — frontend list consumers must handle `{count, next, previous, results}`, not assume a raw
  array.
