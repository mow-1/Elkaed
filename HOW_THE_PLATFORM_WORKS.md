# Elkaed Platform — How It Works

*A plain-language guide to what the website does today, written for the business owner — not a technical document.*

---

## The big picture

The website serves two kinds of students, and connects both of them to one shared system:

1. **Online students** — sign themselves up on the website and buy video courses.
2. **Center students** — register in person at the center, are added to the system by an admin, and mostly use the website to see results, download materials, and watch videos they missed.

Both types share **one wallet** — the same balance can be used to buy an online course or to pay for a center lesson.

---

## For students

### Signing up and logging in
- A student signs up with their **phone number**. A WhatsApp code is sent to confirm it's really them — no email or password needed for online students.
- Center students (added by the admin, see below) get a phone number + password sent to them by WhatsApp when they're registered, and they log in with that.
- Every new student also enters a **parent/guardian phone number**, their academic year (1st/2nd/3rd secondary), and optionally their governorate and school.

### The student portal
Once logged in, every student has a personal dashboard with:
- **Results** — their quiz scores.
- **Files** — notes, summaries, and PDFs the teacher uploads.
- **Lessons** — videos they've purchased or been granted access to.
- **Revisions** — separate review material/videos.
- **My Account** — their profile, wallet balance, full payment history, a QR code ID card they can download/print, and a "change password" option.
- **New** — a feed of the newest videos/courses, filtered to their academic year.
- **Store** — where they browse and buy courses.
- **My Courses** — everything they've bought or been given access to.

### Buying and watching
- Students pay with their **wallet balance**, or with **Kanga Pay** (an Egyptian payment gateway) if their wallet doesn't have enough.
- Each video has a **view limit** (10 by default) to discourage sharing account access.
- Videos are automatically encrypted and processed for streaming as soon as they're uploaded — a student can only ever watch a video they've actually been given access to, and the video link itself can't be shared or downloaded to work outside the site.

---

## For the center (the core new feature)

This is the main thing this round of work added: connecting physical attendance at the center to the online system automatically.

1. The admin creates a **group** (e.g. "Thursday 4pm, 2nd secondary") and a **session** for a specific day, linking it to the online video of that lesson.
2. At the door, an assistant scans each student's **QR code** (printed on an ID card, or shown on their phone) with a normal barcode scanner — this is instant, no typing needed.
3. What happens automatically:
   - If **present**: the lesson price is deducted from their wallet.
   - If **absent**: the lesson price is *still* deducted, and the student automatically gets a **WhatsApp message** with a link to watch that lesson's video online — so they don't fall behind.
   - If **excused**: nothing is charged, no message is sent (for students who make up the lesson another way).
4. The admin can always **override** any of this afterward — mark someone as present/absent after the fact, refund a charge, or resend the WhatsApp message — and the wallet balance always corrects itself properly, it never gets out of sync.
5. If a student forgot their card, the admin can search them by name or phone and mark them manually.

### Importing center students in bulk
Instead of registering one by one, the admin can upload a spreadsheet (CSV file) of many center students at once. The system:
- Checks every row for mistakes (bad phone numbers, duplicates) and shows a full report **before** anything is actually created.
- Creates each account with a random password, sent to the student via WhatsApp along with a "please change your password" reminder.
- Credits their starting wallet balance if the spreadsheet specifies one.

---

## Money — how it's tracked

Every single EGP that moves — a course purchase, a center attendance charge, a refund, a discount, a top-up — is written to one running **ledger**, like a bank statement. This means:
- The teacher/admin can always see exactly why a balance is what it is.
- Nothing can silently disappear or get double-charged.
- Reports (below) are always calculated from this ledger, not from a number that could be edited by mistake.

**Per-student discounts**: the admin can give any individual student a discount (percentage off, a fixed amount off, or entirely free) for online purchases, center attendance, or both — with a required note explaining why (e.g. "financial hardship", "top student"). The student just sees the lower price; they don't see the discount mechanics.

---

## For the admin (you)

The admin dashboard (a separate area from the student side) currently lets you:

- **See and search all customers**, filter by year/type, view a customer's full profile, orders, and enrollments.
- **See business analytics** — total students, revenue, enrollments, top courses.
- **Manage homepage banners**, **flash sales**, **course bundles**.
- **Send bulk WhatsApp/email campaigns** to a segment of students (everyone, just center students, just a specific year, etc.)
- **Import center students** from a spreadsheet.
- **Take attendance** (the mobile-friendly checklist) and **scan QR codes** at the door.
- **Manage per-student discounts**.
- **See an activity log** of every money- or access-related change anyone made, for accountability.
- **See a list of students with a negative wallet balance** (an "arrears" report).
- **See a revenue report** broken down by day/week/month and by center vs. online income.
- **Adjust pricing settings** — the default lesson price, monthly package price, and whether a student's wallet is allowed to go negative or gets blocked instead.
- **Reset a student's password** and send it to them again via WhatsApp.

---

## What's not ready yet

Being fully transparent about the current state, in plain terms:

1. **Video upload/processing now works, but no real lessons have been uploaded yet, and it's only been set up on the development computer, not a real server.** A teacher/admin can add a video file and the system automatically encrypts it and prepares it for streaming — this part has been built and tested successfully. What's left: (a) actually uploading the real lesson recordings, and (b) moving this — like the rest of the site — onto real hosting so it can handle real students (see point 5). Uploading is currently done through a technical admin screen rather than a polished "upload a video" button in the main dashboard — fine to use as-is, but worth a simpler button later if it'll be used often.
2. **"Forgot my password" isn't self-service yet.** If a center student loses their password, the admin has to reset it for them manually from the dashboard — there's no "I forgot my password" button for the student to use themselves.
3. **No one-to-one messaging from the dashboard yet.** The admin can message a whole group of students at once (a campaign), but not send a single WhatsApp message to just one specific student from their profile page.
4. **WhatsApp, payment, and video-storage accounts aren't connected to real credentials yet.** The system is fully built to use them, but the actual WhatsApp business account, Kanga Pay merchant account, and cloud video storage account details still need to be entered before anything goes live for real — right now, everything has only been tested in a safe practice environment.
5. **The website isn't hosted online yet.** Everything described above currently runs only on a development computer — it still needs to be moved onto a real web server so students can actually reach it from their phones.

None of these are difficult — they're mostly a matter of connecting real accounts/servers and (for video) uploading real lesson recordings, not rebuilding anything.
