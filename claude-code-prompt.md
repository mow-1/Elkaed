# Claude Code Prompt — El-Kaed (القائد) Landing Page in React

Copy everything below into Claude Code, and attach the `ElKaed Landing.dc.html` file with it.

---

I'm attaching an HTML file with the finished design of a landing page for "القائد" (El-Kaed), an online Egyptian History teaching platform by teacher Mostafa Arafa (أ/ مصطفى عرفة), for Egyptian secondary-school students (grades 1–3 ثانوي). Recreate this design EXACTLY as a React app. Do not redesign, restyle, or "improve" anything — match the attached file pixel-for-pixel.

## Stack
- React 18 + Vite (or the stack of the existing project if there is one)
- Plain CSS Modules or Tailwind — your choice, but the rendered output must match the attached HTML exactly
- No UI library needed

## Global rules
- The whole page is RTL: `dir="rtl"` on the root, `lang="ar"`
- Fonts (Google Fonts): **Cairo** (weights 400–900) for headings, **Almarai** (300–800) for body text
- Color tokens — define as CSS variables and use everywhere:
  - `--night: #14213D` (primary dark blue), `--night-deep: #0E1729` (footer)
  - `--night-soft: #1E3160`, border on dark `#2C4174`
  - `--gold: #D4A72C`, `--gold-dark: #B08A1E`, `--gold-deeper: #8F6E12`, hover gold `#F0C34A`
  - `--cream: #F5E6BE`, `--sand: #F2E8CF`, sand border `#E0CE96`
  - `--bg: #FAF6EE`, card border `#E8DFC9`, hairline `#F0EADA`
  - text: `#1C2333` (main), `#5A6072` (secondary), `#8A8F9E` (muted), `#3A4152` (quotes)
- Decorative motif used in several places: a repeating gold dash strip —
  `repeating-linear-gradient(90deg, #D4A72C 0 24px, transparent 24px 48px)` as a 5–6px top border on dark sections; gold squares rotated 45° as bullets; hieroglyph glyph characters (𓂀 𓋹 𓉐 𓏞) as icon accents.
- Max content width 1200px, centered, 24px side padding.

## Component structure
Build these components (all copy is in the attached HTML — use it verbatim, it's Egyptian-Arabic):

1. **Navbar** — sticky, blurred cream background (`rgba(250,246,238,0.92)` + backdrop-blur), gold pyramid logo mark (triangle in a navy rounded square) + "القائد / EL-KAED" wordmark, 4 anchor links, "تسجيل الدخول" text link + "حساب جديد" navy pill button.
2. **Hero** — 2-column grid (text right, image left in RTL). Eyebrow pill, 52px Cairo-900 headline with gold highlighted word "القائد", paragraph, two CTAs (solid gold + outlined navy), stats row (+12,000 طالب / +340 حصة / %94) above a hairline. Image column: 480px-tall rounded photo of the teacher with an offset 2px gold border frame behind it and a floating name card (𓂀 avatar + "أ/ مصطفى عرفة") overlapping the bottom.
3. **Features** — centered section header (gold eyebrow, Cairo-900 title, short gold underline bar), 4 white cards in a row: sand icon tile with hieroglyph, bold title, 2-line description. Hover: gold border + soft shadow.
4. **DarkBand** — full-width navy section with gold dash strip on top. Right: Cairo-900 cream headline, paragraph, 2×2 checklist grid with rotated gold-square bullets, gold CTA button. Left: photo collage grid (one tall image spanning 2 rows, one image, one navy quote tile with 𓋹 glyph and "التاريخ مش حفظ… التاريخ فهم وحكاية").
5. **Courses** — centered header ("أشهر كورسات القائد"), grade filter pills (كل الصفوف / الصف الأول الثانوي / الثاني / الثالث) that filter the cards with React state (active pill = navy fill, cream text). 3-column grid of course cards: cover image (190px) with navy price badge bottom-left, teacher row (𓂀 avatar + name + grade chip), Cairo-800 course title, footer meta row (👥 students / lessons 📖) above a hairline. Hover: gold border + shadow. Course data (6 courses) is in the attached file's script — extract it into a `courses.js` data file.
6. **Testimonials** — sand-background full-width band, 3 white quote cards: big gold "”", quote text, avatar circle with initial + name + grade.
7. **RegisterCTA** — navy rounded-24px card, gold dash strip top, 𓂀 glyph, "هتحس إنك قاعد في الفصل بالظبط!" headline, paragraph, gold CTA button.
8. **Footer** — deepest navy, 3 columns (brand + blurb / روابط سريعة / تواصل معانا with Facebook link `https://www.facebook.com/MostafaArafaOfficial1` and WhatsApp), hairline, copyright row with gold tagline "التاريخ حكاية… والقائد راويها".

## Images
The design uses placeholder image slots (teacher hero photo, 2 band photos, 6 course covers). In React, render plain `<img>` elements with `object-fit: cover` and the same dimensions/border-radius, reading from `/public/images/…` — I'll drop in the real photos. Use a neutral navy placeholder background until then.

## Behavior
- Grade filter pills filter the course grid (React `useState`)
- Anchor links scroll to sections
- All hover states from the HTML (buttons darken/brighten, cards get gold border + shadow)

## Acceptance criteria
- Side-by-side with the attached HTML at 1440px wide, layout/spacing/colors/typography are indistinguishable
- Fully RTL, Arabic copy identical
- Responsive: below 900px, grids collapse to 1 column and nav links collapse into a simple menu
