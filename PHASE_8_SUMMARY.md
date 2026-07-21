# Phase 8 — React Frontend (Landing Page)

**Date:** 2026-07-15  
**Status:** ✅ Clean build (35 modules, 226ms), dev server at http://localhost:5173  
**Stack:** React 18 + Vite 8 + CSS Modules, RTL Arabic, no UI library

---

## What Was Built

### Project Scaffold (main thread)

| File | Purpose |
|------|---------|
| `frontend/index.html` | RTL `dir="rtl"`, `lang="ar"`, Cairo + Almarai Google Fonts |
| `frontend/src/index.css` | CSS variables (all 18 design tokens from the HTML) + reset |
| `frontend/src/App.jsx` | Root — imports + composes all 9 components |
| `frontend/src/data/courses.js` | All data extracted from the DC HTML: COURSES, FEATURES, TESTIMONIALS, BAND_POINTS, GRADES |

### Agent A — Shell Components

| Component | Key details |
|-----------|------------|
| **Navbar** | Sticky, `backdrop-filter: blur(10px)`, scroll-shadow state, hamburger toggle (☰/✕) for <900px mobile, active link highlight |
| **Hero** | 2-col grid, primary blue bg, dot-pattern overlay, angled cream clip-path at bottom, 2 overlapping course preview cards with placeholder glyphs, floating animation on Card 2 (`float 4s ease-in-out infinite`) |
| **Footer** | 3-col (2fr 1fr 1fr), dark navy `#2338AE`, Facebook + WhatsApp links, gold tagline |
| **WhatsAppBtn** | Fixed bottom-left circle, `#25D366`, pop-in entrance animation on delay 1s, accessibility `title` |

### Agent B — Content Sections

| Component | Key details |
|-----------|------------|
| **Features** | 4-col card grid, glyph tiles, hover: gold border + `translateY(-4px)` lift, 2-col at 900px, 1-col at 500px |
| **DarkBand** | Navy bg, gold-dash strip, 2-col: text+checklist left / photo collage right (tall cell `grid-row: span 2` + hieroglyph quote tile) |
| **Courses** | Grade filter pills (`useState`), filtered grid using `key={activeGrade}` for CSS `fadeIn` re-mount animation, `onError` image fallback, price badge |
| **Testimonials** | Sand background (`var(--cream-soft)`), 3 quote cards with big gold `"` and avatar initials |
| **RegisterCTA** | Navy card, gold-dash strip, dot-pattern overlay, `𓂀` glyph, gold CTA button |

---

## Design Fidelity Tweaks Added

| Tweak | Where |
|-------|-------|
| Card 2 float animation (`float 4s ease-in-out infinite`) | Hero |
| Scroll-triggered navbar shadow | Navbar |
| Hamburger mobile menu with slide-down | Navbar |
| Card lift `translateY(-4px)` on hover | Features |
| `key={activeGrade}` fade-in on filter change | Courses |
| Image `onError` hides broken img, shows placeholder | Courses |
| Dot-pattern overlay on CTA card | RegisterCTA |
| WhatsApp `pop-in` entrance animation (1s delay) | WhatsAppBtn |

---

## How to Preview

```
cd E:\Elkaed\frontend
npm run dev
# → http://localhost:5173
```

## Drop in Real Images

Place files in `E:\Elkaed\frontend\public\images\`:
- `course-1.jpg` through `course-6.jpg` — course cover thumbnails (recommended: 400×190px)
- The app already references `/images/course-N.jpg` and falls back to the navy placeholder if missing

## Phase 9 Candidates

1. **API integration** — wire Courses grid to `GET /api/courses/`, Hero stats to `/api/auth/analytics/`
2. **Auth flow** — OTP login page (phone → code → JWT stored in httpOnly cookie), register page
3. **Student dashboard** — my enrollments, watchlist, order history, notification preferences
4. **Video player page** — HLS + AES-128 with the token endpoint `/api/videos/<id>/token/`
5. **Quiz page** — start attempt, question-by-question, submit, results
6. **Instructor panel** — course list, student roster, quiz CSV export button
