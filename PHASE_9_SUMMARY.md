# Phase 9 — React API Integration + Auth + Pages

**Date:** 2026-07-15  
**Status:** ✅ Clean build — 12 code-split chunks, 318ms  
**Dev server:** http://localhost:5173

---

## What Was Built

### Core Infrastructure (main thread)

| File | Purpose |
|------|---------|
| `src/api/client.js` | Native `fetch` wrapper — auto-attaches JWT, auto-refreshes on 401, fires `auth:logout` event on failure |
| `src/api/auth.js` | `sendOTP`, `verifyOTP`, `getProfile`, `updateProfile`, `getAnalytics` |
| `src/api/courses.js` | `getCourses`, `getCourse`, `enrollCourse`, `getMyEnrollments`, `getWatchlist`, `toggleWatchlist` |
| `src/api/commerce.js` | `getWallet`, `getOrders`, `redeemCoupon` |
| `src/api/notifications.js` | `getBanners`, `getNotifPrefs`, `updateNotifPrefs` |
| `src/context/AuthContext.jsx` | JWT in localStorage, `login/logout/reload`, auto-loads profile on mount |
| `src/pages/LandingPage.jsx` | Extracted from App.jsx — all 6 landing sections |
| `src/App.jsx` | `BrowserRouter` + `AuthProvider` + lazy `<Routes>` — 4 routes |
| `.env` | `VITE_API_URL=http://localhost:8000` |

**react-router-dom** installed.

### Agent 1 — Auth Pages

| Page | Route | Details |
|------|-------|---------|
| `LoginPage` | `/login` | 2-step: phone → OTP → JWT + navigate to `/dashboard`; `slideIn` animation on step 2 |
| `RegisterPage` | `/register` | 3-step: phone → OTP → profile (name, type, year) → account created + login |

Both pages: standalone (no Navbar/Footer), 440px centered card, dot-pattern background, "العودة للرئيسية" link, Arabic error messages.

### Agent 2 — Dashboard

| Tab | Data source | Key feature |
|-----|-------------|-------------|
| كورساتي | `GET /api/courses/my-enrollments/` | Enrollment cards with course link + status |
| طلباتي | `GET /api/commerce/orders/` | Order cards with status chips + nested items |
| الإشعارات | `GET /api/notifications/preferences/` | 4 toggle switches — optimistic update with rollback |
| بياناتي | from AuthContext | Profile fields read-only; wallet balance in header |

- Auth guard: redirects to `/login` if no user
- Wallet summary card at top fetches `GET /api/commerce/wallet/`
- `load()` helper: 8 lines handles all 4 API calls uniformly
- Parallel fetches on `user` becoming truthy

### Agent 3 — Navbar auth + Courses API + CourseDetail

**Navbar (updated):**
- Logged out → `<Link to="/login">` + `<Link to="/register">`
- Logged in → avatar circle (first initial) + name + `/dashboard` link + logout button

**Courses (updated):**
- Starts with static COURSES as immediate value — no empty flash
- Fetches `GET /api/courses/` on mount; on success replaces with API data
- On any error → silently stays on static data
- Skeleton shimmer cards while loading (3 placeholders)
- Course cards link to `/courses/:slug` when slug is available

**CourseDetailPage** (`/courses/:slug`):
- Fetches `GET /api/courses/<slug>/`
- Header: thumbnail (16:9, navy placeholder) + price + instructor + enroll button
- Enroll button: 4 states (idle / loading / success / already-enrolled) + auth guard
- Topics accordion: expandable sections → lessons with free-preview chip + MM:SS duration + lock icon

---

## Routes Map

```
/                   → LandingPage (Navbar + Footer)
/login              → LoginPage (standalone)
/register           → RegisterPage (standalone)
/dashboard          → DashboardPage (Navbar + Footer, auth-guarded)
/courses/:slug      → CourseDetailPage (Navbar + Footer)
```

## Phase 10 Candidates

1. **Video player** — HLS.js integration + `GET /api/videos/<lesson_id>/token/` for AES-128 key delivery
2. **Quiz flow** — Start attempt → question-by-question MCQ → submit → results with score breakdown
3. **Instructor panel** — `/instructor` route: course list, student roster per course, CSV export button
4. **Address book** — `GET/POST /api/auth/addresses/` — manage shipping addresses in dashboard
5. **Production** — CORS config, static files (WhiteNoise), proper SMTP email backend, Redis for Celery Beat
6. **ETL pass 8** — migrate quiz content + lesson progress from WordPress DB
