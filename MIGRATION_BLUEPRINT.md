# منصة القائد — Migration & Architecture Blueprint
# Elkaed.online — Complete Migration & Architecture Blueprint

> **Document Version:** 2.0  
> **Date:** 2026-07-14  
> **Status:** Reference document for all development sessions  
> **Scope:** WordPress + TutorLMS + WooCommerce → Django REST API + React SPA

---

## TABLE OF CONTENTS

1. [Forensic Summary](#1-forensic-summary)
2. [Phase 1 — Forensic Discovery](#2-phase-1--forensic-discovery)
3. [Phase 2 — Database Schema Deconstruction](#3-phase-2--database-schema-deconstruction)
4. [Phase 3 — Architectural Blueprint](#4-phase-3--architectural-blueprint)
   - [4.1 Django ORM Strategy](#41-django-orm-strategy)
   - [4.2 React Component Tree](#42-react-component-tree)
   - [4.3 Internationalization — Arabic First](#43-internationalization--arabic-first)
   - [4.4 Admin Panel — Full Arabic Interface](#44-admin-panel--full-arabic-interface)
   - [4.5 Self-Hosted Video Pipeline](#45-self-hosted-video-pipeline)
   - [4.6 Advanced Video Protection Strategy](#46-advanced-video-protection-strategy)
   - [4.7 Feature Parity Plan](#47-feature-parity-plan)
5. [Phase 4 — ETL Strategy](#5-phase-4--etl-strategy)
6. [System Enhancement Recommendations](#6-system-enhancement-recommendations)
7. [Credential Registry](#7-credential-registry)
8. [Project Constraints & Risks](#8-project-constraints--risks)

---

## 1. FORENSIC SUMMARY

| Property | Value |
|---|---|
| **Platform** | WordPress 6.x + Tutor LMS Pro + WooCommerce |
| **Active Theme** | Ecademy + Ecademy-Child |
| **Table Prefix** | `29_` (not `wp_`) |
| **Total Users** | ~5,483 (AUTO_INCREMENT=5483) |
| **Total Posts** | ~60,632 (courses, lessons, quizzes, orders, media) |
| **Quiz Attempts** | 9,767 attempts / 246,864 attempt answers |
| **Quiz Questions** | 12,590 questions / 48,475 answer choices |
| **Instructor Earnings Records** | 7,916 |
| **Payment Gateway** | Kanga Pay (Egyptian) — ONLY active gateway |
| **Video Host** | **YouTube ONLY** (changing to self-hosted — see §4.5) |
| **Upload Media** | 13,000+ images (JPG/PNG/JPEG), 8 MP4 files (thumbnails only) |
| **WhatsApp Provider** | wa-ma.org API |
| **Primary Identity** | Phone number (not email) |
| **Currency** | EGP (Egyptian Pound) |
| **Target Students** | Secondary school (Grades 10, 11, 12) — Egypt |

---

## 2. PHASE 1 — FORENSIC DISCOVERY

### 2.1 Custom Plugins (MAIM Suite) — Must Replicate All

All 7 custom plugins are operational business logic, not cosmetic. Every one maps to a Django feature.

---

#### Plugin 1: `maim-phone` — WhatsApp Phone Authentication
**Criticality: CRITICAL — entire auth system depends on this**

- Phone number is the primary user identifier (`user_login` = `201XXXXXXXXX`)
- Email is a fake synthetic field: `+20XXXXXXXXXX@elkaed.online`
- Registration, login, and password reset all use WhatsApp OTP
- OTP delivered via `wa-ma.org` API with hardcoded key in `sendwa.php`
- `sendwa.php` is a publicly-accessible unauthenticated relay (security debt)

---

#### Plugin 2: `maim-tutor-create-student` — Instructor Student Factory
**Criticality: HIGH — instructors actively use this to onboard students**

- Shortcode: `[tutor_create_student]`
- Form fields collected: First Name, Last Name, Student Phone (becomes password), Guardian Phone, Academic Year, Student Type
- Instructor-only access — creates WordPress user directly
- Requires equivalent "Create Student" page in React instructor dashboard

---

#### Plugin 3: `maim-instructor-enrollment` — Bulk Enrollment Engine
**Criticality: HIGH — used for class-level enrollments**

- Shortcode: `[maim_bulk_tutor_enroll]`
- Uses hardcoded Tutor LMS REST API credentials
- Two-step process: `POST /wp-json/tutor/v1/enrollments` → `PUT /wp-json/tutor/v1/enrollments/completed`
- Security issue: `wp_ajax_nopriv` allows unauthenticated AJAX trigger

---

#### Plugin 4: `maim-instructor-dashboard-tabs` — Instructor Dashboard Extension
**Criticality: MEDIUM — instructor UX depends on it**

Adds 5 tabs to Tutor LMS instructor dashboard:
- Lesson Watchlist
- Quiz Export (CSV download of student scores)
- Quiz Permissions (lock/unlock quizzes)
- Create Student (links to `/create-student/`)
- Enroll Students (links to `/enroll-students/`)

---

#### Plugin 5: `maim-student-courses` — Segmented Course Catalog + Wallet Purchase
**Criticality: CRITICAL — this is the main student course-buying flow**

- Shortcode: `[maim_fast_buy_courses]`
- Filters courses by `student_type` (center/online) × `academic_year` (1st/2nd/3rd secondary)
- Student buys using internal wallet balance
- Flow: check balance → deduct balance → call Tutor REST API to enroll → redirect to dashboard
- Falls back to WooCommerce checkout URL if wallet insufficient

---

#### Plugin 6: `maim-user-wallet-coupons` — Coupon-to-Wallet Converter
**Criticality: HIGH — active payment method used alongside Kanga Pay**

- Students redeem WooCommerce fixed-cart coupons to top-up `_user_balance` user meta
- Custom DB table `29_coupon_redemptions`: logs every redemption (user_id, coupon_code, amount, date)
- Deduplication: user cannot redeem same coupon twice
- Usage limit enforcement per WooCommerce coupon rules
- Admin log page in WordPress dashboard

---

#### Plugin 7: `tutor-quiz-permissions` — Per-Quiz Access Control
**Criticality: HIGH — instructors regularly toggle quiz locks**

- Per-quiz postmeta flags:
  - `_forbidden_take = 1` → blocks any student from starting the quiz
  - `_forbidden_attempt_details = 1` → hides score breakdown after attempt
- Managed via bulk-action admin table
- Resets cache on change

---

### 2.2 Child Theme Critical Logic (`ecademy-child/functions.php`)

| Hook/Filter | Business Logic |
|---|---|
| `woocommerce_add_to_cart_redirect` | Skip cart → go directly to checkout |
| `woocommerce_add_to_cart_validation` | Auto-empty cart (max 1 product at a time) |
| `woocommerce_checkout_fields` | Strip all address/email fields for virtual products |
| `default_checkout_billing_country` | Default Egypt (EG) |
| `woocommerce_product_single_add_to_cart_text` | Custom Arabic text: "اشتري الان" |
| `billing_company` field override | Re-purposed as **guardian phone** field |
| `tutor_quiz/attempt_ended` | On quiz submit → POST to `sendwa.php` → WhatsApp to student AND guardian |
| `show_user_profile` | Adds `student_type` (center/online) select field |
| `wp_logout` | Redirect to homepage after logout |
| `custom_validate_billing_phone` | Enforce 11-digit Egyptian phone validation |

---

### 2.3 `sendwa.php` — WhatsApp Relay

- Publicly accessible at `https://elkaed.online/sendwa.php`
- Accepts `phone_to` + `message` via POST — **no authentication**
- Normalizes Egyptian numbers to international format (201XXXXXXXXX)
- Calls `https://api.wa-ma.org/send-message`
- **Security risk:** Open relay — anyone can send WhatsApp messages via this endpoint

---

### 2.4 Third-Party Integrations

| Service | Role | Status |
|---|---|---|
| **Kanga Pay** (kanga-pay.com) | Egyptian payment gateway | ACTIVE |
| **wa-ma.org** (WhatsApp) | OTP auth + quiz result notifications | ACTIVE |
| **YouTube** | Video hosting (all lesson videos) | ACTIVE — changing to self-hosted |
| **Mailchimp** | Email marketing | ABANDONED (tables empty) |
| **Advanced Custom Fields Pro** | Extra page fields | ACTIVE (ecademy theme) |
| **Elementor Pro** | Page builder | ACTIVE (replacing with React) |
| **WP Optimize** | Caching | RETIRING |

---

### 2.5 Media Asset Profile

| Type | Count | Disposition |
|---|---|---|
| `.jpg / .jpeg / .png` | ~13,000 | **Migrate to new CDN** |
| `.mp4` | 8 | Small demo/promo clips — migrate |
| `.woff2` | 73 | Arabic web fonts — migrate |
| `.svg` | 27 | UI icons — recreate or migrate |
| Course videos | 0 on-server | YouTube hosted → **changing to self-hosted** |

---

## 3. PHASE 2 — DATABASE SCHEMA DECONSTRUCTION

### 3.1 Core LMS Post Type Hierarchy

```
wp_posts (table prefix: 29_)
│
├── post_type = 'courses'          → Course
│   ├── post_type = 'topics'       → Topic/Section (post_parent = course.ID)
│   │   ├── post_type = 'lesson'   → Lesson (post_parent = topic.ID)
│   │   └── post_type = 'tutor_quiz' → Quiz (post_parent = topic.ID)
│   └── post_type = 'tutor_zoom_meeting' → Live Sessions (if any)
│
├── post_type = 'tutor_enrolled'   → Legacy enrollment record
├── post_type = 'shop_product'     → WooCommerce product (linked to course)
└── post_type = 'shop_order'       → WooCommerce order (legacy, replaced by HPOS)
```

### 3.2 Critical Postmeta Keys

| meta_key | Object | Value Description |
|---|---|---|
| `_tutor_course_product_id` | Course | WooCommerce product ID linked to this course |
| `tutor_course_price` | Course | Display price in EGP |
| `_video` | Lesson | PHP-serialized: `{source: 'youtube', source_video_id: '...'}` |
| `_forbidden_take` | Quiz | 0/1 — blocks quiz attempt |
| `_forbidden_attempt_details` | Quiz | 0/1 — hides result breakdown |
| `_tutor_enrolled_by_order_id` | Enrollment Post | WooCommerce order that triggered enrollment |
| `_is_tutor_order_for_course` | WC Order | Course ID that this order purchases |
| `_billing_company` | WC Order/User | **Guardian phone number** (repurposed field) |
| `_billing_phone` | WC Order | Student phone number |
| `_billing_email` | WC Order | Fake email (`+20...@elkaed.online`) |

### 3.3 User Metadata Fields

| meta_key | Description | New Field |
|---|---|---|
| `student_type` | `center` or `online` | `User.student_type` |
| `academic_year` | `first_secondary`, `second_secondary`, `third_secondary` | `User.academic_year` |
| `billing_company` | Guardian phone number | `User.guardian_phone` |
| `_user_balance` | Wallet balance in EGP | `User.wallet_balance` |
| `wp_capabilities` | `tutor_instructor` → instructor role | `User.role` |

### 3.4 Tutor LMS Dedicated Tables

| Table | Rows (approx) | Purpose |
|---|---|---|
| `29_tutor_quiz_questions` | 12,590 | Quiz questions with type + settings |
| `29_tutor_quiz_question_answers` | 48,475 | Answer choices per question |
| `29_tutor_quiz_attempts` | 9,767 | Student quiz sessions |
| `29_tutor_quiz_attempt_answers` | 246,864 | Per-question student responses |
| `29_tutor_orders` | — | Native Tutor LMS orders |
| `29_tutor_order_items` | — | Course items per order |
| `29_tutor_customers` | — | Billing snapshots |
| `29_tutor_earnings` | 7,916 | Instructor revenue splits |
| `29_tutor_coupons` | — | Native LMS discount codes |
| `29_tutor_carts` + `29_tutor_cart_items` | — | Tutor native cart |
| `29_coupon_redemptions` | — | **CUSTOM** — wallet coupon log |

### 3.5 WooCommerce HPOS Tables (Modern)

WooCommerce 8.x has High-Performance Order Storage enabled. Orders exist in BOTH legacy (`29_posts`) and HPOS (`29_wc_orders`) tables. **ETL must use `29_wc_orders` as source of truth.**

| Table | Purpose |
|---|---|
| `29_wc_orders` | Order headers |
| `29_wc_order_addresses` | Billing/shipping addresses |
| `29_wc_order_items` | Line items |
| `29_wc_orders_meta` | Order metadata |
| `29_wc_order_stats` | Analytics aggregates |
| `29_wc_customer_lookup` | Customer summary view |

### 3.6 Data Anomalies & Risks

| Anomaly | Risk Level | Notes |
|---|---|---|
| Fake email addresses (`+20...@elkaed.online`) | CRITICAL | Cannot use email for any auth or notification |
| Guardian phone in `billing_company` | HIGH | Must extract and migrate to dedicated column |
| Two enrollment systems coexist | HIGH | `tutor_enrolled` posts + `tutor_orders` — deduplicate on ETL |
| Elementor JSON in postmeta | MEDIUM | Do NOT migrate — pages rebuilt in React |
| Hardcoded API credentials in 2 plugins | HIGH | Rotate all keys post-migration |
| `sendwa.php` unauthenticated relay | HIGH | Must secure in Django |
| phpass password hashing | MEDIUM | Requires custom Django password hasher bridge |
| `quiz_attempt_logs.txt` flat file | LOW | Redundant — skip migration |
| Table prefix `29_` | LOW | All ETL queries must use this prefix |

---

## 4. PHASE 3 — ARCHITECTURAL BLUEPRINT

### 4.1 Django ORM Strategy

#### Project Structure

```
backend/
├── config/
│   ├── settings/
│   │   ├── base.py
│   │   ├── development.py
│   │   └── production.py
│   ├── urls.py
│   └── wsgi.py
├── apps/
│   ├── users/          # Custom user model, OTP, roles
│   ├── courses/        # Course, Topic, Lesson, Enrollment
│   ├── quizzes/        # Quiz, Question, Attempt
│   ├── commerce/       # Order, Coupon, Wallet
│   ├── videos/         # Video upload, transcoding, delivery
│   ├── notifications/  # WhatsApp, push, in-app
│   ├── i18n/           # Translations management
│   └── analytics/      # Progress, reporting
├── etl/                # Migration scripts
└── manage.py
```

#### Custom User Model

```python
# apps/users/models.py

class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ('student', 'طالب'),
        ('instructor', 'مدرس'),
        ('admin', 'مدير'),
        ('staff', 'موظف'),
    ]
    STUDENT_TYPE_CHOICES = [
        ('center', 'سنتر'),
        ('online', 'أونلاين'),
    ]
    ACADEMIC_YEAR_CHOICES = [
        ('1st', 'الصف الأول الثانوي'),
        ('2nd', 'الصف الثاني الثانوي'),
        ('3rd', 'الصف الثالث الثانوي'),
    ]

    phone          = models.CharField(max_length=15, unique=True)  # 201XXXXXXXXX
    first_name     = models.CharField(max_length=100)
    last_name      = models.CharField(max_length=100)
    guardian_phone = models.CharField(max_length=15, blank=True)
    student_type   = models.CharField(choices=STUDENT_TYPE_CHOICES, max_length=10, blank=True)
    academic_year  = models.CharField(choices=ACADEMIC_YEAR_CHOICES, max_length=5, blank=True)
    wallet_balance = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    role           = models.CharField(choices=ROLE_CHOICES, max_length=15, default='student')
    is_active      = models.BooleanField(default=True)
    is_staff       = models.BooleanField(default=False)
    date_joined    = models.DateTimeField(auto_now_add=True)
    wp_user_id     = models.IntegerField(null=True, unique=True, db_index=True)  # migration key

    USERNAME_FIELD  = 'phone'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    objects = UserManager()

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

class PhoneOTP(models.Model):
    PURPOSE_CHOICES = [
        ('register', 'تسجيل'),
        ('login', 'دخول'),
        ('reset', 'استعادة كلمة المرور'),
    ]
    phone      = models.CharField(max_length=15)
    code       = models.CharField(max_length=6)
    purpose    = models.CharField(choices=PURPOSE_CHOICES, max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used       = models.BooleanField(default=False)
    attempts   = models.PositiveSmallIntegerField(default=0)  # brute-force protection

    class Meta:
        indexes = [models.Index(fields=['phone', 'purpose', 'used'])]
```

#### Course Models

```python
# apps/courses/models.py

class Category(models.Model):
    name          = models.CharField(max_length=200)        # Arabic
    name_en       = models.CharField(max_length=200, blank=True)  # English
    slug          = models.SlugField(unique=True)
    student_type  = models.CharField(max_length=10, blank=True)
    academic_year = models.CharField(max_length=5, blank=True)
    parent        = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL)
    order         = models.PositiveIntegerField(default=0)

class Course(models.Model):
    title         = models.CharField(max_length=300)
    title_en      = models.CharField(max_length=300, blank=True)
    slug          = models.SlugField(unique=True)
    description   = models.TextField()
    description_en = models.TextField(blank=True)
    instructor    = models.ForeignKey(User, related_name='courses', on_delete=models.PROTECT)
    category      = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    price         = models.DecimalField(max_digits=10, decimal_places=2)
    thumbnail     = models.ImageField(upload_to='courses/thumbnails/')
    is_published  = models.BooleanField(default=False)
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)
    wp_post_id    = models.IntegerField(null=True, unique=True, db_index=True)

class Topic(models.Model):  # Section inside a course
    course  = models.ForeignKey(Course, related_name='topics', on_delete=models.CASCADE)
    title   = models.CharField(max_length=300)
    title_en = models.CharField(max_length=300, blank=True)
    order   = models.PositiveIntegerField()
    wp_post_id = models.IntegerField(null=True, db_index=True)

class Lesson(models.Model):
    VIDEO_SOURCES = [('self_hosted', 'مستضاف ذاتياً'), ('youtube', 'يوتيوب')]
    
    topic         = models.ForeignKey(Topic, related_name='lessons', on_delete=models.CASCADE)
    title         = models.CharField(max_length=300)
    title_en      = models.CharField(max_length=300, blank=True)
    video         = models.ForeignKey('videos.Video', null=True, on_delete=models.SET_NULL)
    video_source  = models.CharField(choices=VIDEO_SOURCES, max_length=15, default='self_hosted')
    youtube_id    = models.CharField(max_length=50, blank=True)  # legacy fallback
    order         = models.PositiveIntegerField()
    view_limit    = models.PositiveIntegerField(default=0)  # 0 = unlimited
    is_free_preview = models.BooleanField(default=False)
    duration_seconds = models.PositiveIntegerField(default=0)
    wp_post_id    = models.IntegerField(null=True, db_index=True)

class Enrollment(models.Model):
    STATUS_CHOICES = [
        ('active', 'نشط'),
        ('expired', 'منتهي'),
        ('cancelled', 'ملغي'),
    ]
    PAYMENT_METHOD_CHOICES = [
        ('kanga_pay', 'كانجا باي'),
        ('wallet', 'محفظة'),
        ('free', 'مجاني'),
        ('manual', 'يدوي'),
    ]
    student        = models.ForeignKey(User, related_name='enrollments', on_delete=models.PROTECT)
    course         = models.ForeignKey(Course, on_delete=models.PROTECT)
    status         = models.CharField(choices=STATUS_CHOICES, max_length=15, default='active')
    payment_method = models.CharField(choices=PAYMENT_METHOD_CHOICES, max_length=15)
    order          = models.ForeignKey('commerce.Order', null=True, on_delete=models.SET_NULL)
    enrolled_at    = models.DateTimeField(auto_now_add=True)
    expires_at     = models.DateTimeField(null=True)
    enrolled_by    = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name='enrollments_created')

    class Meta:
        unique_together = [('student', 'course')]

class LessonProgress(models.Model):
    student      = models.ForeignKey(User, on_delete=models.CASCADE)
    lesson       = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    view_count   = models.PositiveIntegerField(default=0)
    last_position_seconds = models.PositiveIntegerField(default=0)  # resume position
    completed    = models.BooleanField(default=False)
    last_watched = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [('student', 'lesson')]
```

#### Quiz Models

```python
# apps/quizzes/models.py

class Quiz(models.Model):
    QUESTION_TYPES = [
        ('mcq', 'اختيار متعدد'),
        ('tf', 'صح أو خطأ'),
        ('fill', 'اكمل الفراغ'),
        ('open', 'سؤال مقالي'),
        ('ordering', 'ترتيب'),
    ]
    topic            = models.ForeignKey('courses.Topic', on_delete=models.CASCADE)
    title            = models.CharField(max_length=300)
    title_en         = models.CharField(max_length=300, blank=True)
    time_limit       = models.PositiveIntegerField(null=True, help_text='بالدقائق')
    pass_mark        = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0'))
    attempts_allowed = models.PositiveIntegerField(default=0)  # 0 = unlimited
    is_locked        = models.BooleanField(default=False)       # _forbidden_take
    hide_results     = models.BooleanField(default=False)       # _forbidden_attempt_details
    shuffle_questions = models.BooleanField(default=False)
    shuffle_answers  = models.BooleanField(default=False)
    wp_post_id       = models.IntegerField(null=True, unique=True, db_index=True)

class Question(models.Model):
    TYPES = [('mcq','MCQ'),('tf','T/F'),('fill','Fill'),('open','Open'),('ordering','Order')]
    quiz          = models.ForeignKey(Quiz, related_name='questions', on_delete=models.CASCADE)
    text          = models.TextField()
    text_en       = models.TextField(blank=True)
    question_type = models.CharField(choices=TYPES, max_length=10)
    mark          = models.DecimalField(max_digits=8, decimal_places=2)
    order         = models.PositiveIntegerField()
    explanation   = models.TextField(blank=True)
    explanation_en = models.TextField(blank=True)
    image         = models.ImageField(upload_to='quiz/questions/', null=True, blank=True)
    wp_question_id = models.IntegerField(null=True, db_index=True)

class AnswerChoice(models.Model):
    question   = models.ForeignKey(Question, related_name='choices', on_delete=models.CASCADE)
    text       = models.TextField()
    text_en    = models.TextField(blank=True)
    is_correct = models.BooleanField(default=False)
    order      = models.PositiveIntegerField()
    image      = models.ImageField(upload_to='quiz/answers/', null=True, blank=True)
    wp_answer_id = models.IntegerField(null=True, db_index=True)

class QuizAttempt(models.Model):
    STATUS = [('in_progress','جاري'),('submitted','مكتمل'),('timed_out','انتهى الوقت')]
    RESULT = [('pass','ناجح'),('fail','راسب')]
    
    student        = models.ForeignKey('users.User', on_delete=models.CASCADE)
    quiz           = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    course         = models.ForeignKey('courses.Course', on_delete=models.CASCADE)
    total_marks    = models.DecimalField(max_digits=9, decimal_places=2)
    earned_marks   = models.DecimalField(max_digits=9, decimal_places=2, default=Decimal('0'))
    status         = models.CharField(choices=STATUS, max_length=15, default='in_progress')
    result         = models.CharField(choices=RESULT, max_length=5, null=True)
    started_at     = models.DateTimeField(auto_now_add=True)
    ended_at       = models.DateTimeField(null=True)
    is_reviewed    = models.BooleanField(default=False)  # for open-ended questions
    wp_attempt_id  = models.IntegerField(null=True, unique=True, db_index=True)

    class Meta:
        indexes = [models.Index(fields=['student', 'quiz', 'status'])]

class AttemptAnswer(models.Model):
    attempt        = models.ForeignKey(QuizAttempt, related_name='answers', on_delete=models.CASCADE)
    question       = models.ForeignKey(Question, on_delete=models.CASCADE)
    given_answer   = models.TextField()
    is_correct     = models.BooleanField(null=True)
    marks_achieved = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0'))
    wp_answer_id   = models.IntegerField(null=True, db_index=True)
```

#### Commerce & Wallet Models

```python
# apps/commerce/models.py

class Order(models.Model):
    STATUSES = [
        ('pending','قيد الانتظار'),
        ('completed','مكتمل'),
        ('cancelled','ملغي'),
        ('refunded','مسترد'),
        ('failed','فشل'),
    ]
    PAYMENT_METHODS = [('kanga_pay','كانجا باي'),('wallet','محفظة')]

    user           = models.ForeignKey('users.User', on_delete=models.PROTECT)
    status         = models.CharField(choices=STATUSES, max_length=15, default='pending')
    payment_method = models.CharField(choices=PAYMENT_METHODS, max_length=15)
    transaction_id = models.CharField(max_length=255, blank=True)  # Kanga Pay ref
    total_price    = models.DecimalField(max_digits=10, decimal_places=2)
    coupon_code    = models.CharField(max_length=50, blank=True)
    coupon_amount  = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'))
    created_at     = models.DateTimeField(auto_now_add=True)
    wp_order_id    = models.IntegerField(null=True, unique=True, db_index=True)

class OrderItem(models.Model):
    order  = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    course = models.ForeignKey('courses.Course', on_delete=models.PROTECT)
    price  = models.DecimalField(max_digits=10, decimal_places=2)

class Coupon(models.Model):
    TYPES = [('wallet_recharge','شحن محفظة'),('course_discount','خصم كورس')]
    
    code           = models.CharField(max_length=50, unique=True)
    coupon_type    = models.CharField(choices=TYPES, max_length=20, default='wallet_recharge')
    amount         = models.DecimalField(max_digits=10, decimal_places=2)
    usage_limit    = models.PositiveIntegerField(default=1)
    usage_count    = models.PositiveIntegerField(default=0)
    expires_at     = models.DateTimeField(null=True)
    created_at     = models.DateTimeField(auto_now_add=True)
    created_by     = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True)
    is_active      = models.BooleanField(default=True)

class CouponRedemption(models.Model):
    user        = models.ForeignKey('users.User', on_delete=models.CASCADE)
    coupon      = models.ForeignKey(Coupon, on_delete=models.CASCADE)
    amount      = models.DecimalField(max_digits=10, decimal_places=2)
    redeemed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('user', 'coupon')]

class WalletTransaction(models.Model):
    TYPES = [('credit','إيداع'),('debit','خصم')]
    
    user       = models.ForeignKey('users.User', related_name='wallet_transactions', on_delete=models.CASCADE)
    amount     = models.DecimalField(max_digits=10, decimal_places=2)
    type       = models.CharField(choices=TYPES, max_length=6)
    balance_after = models.DecimalField(max_digits=10, decimal_places=2)
    reference  = models.CharField(max_length=100)
    note       = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
```

---

### 4.2 React Component Tree

```
src/
├── main.jsx                          # Entry point, providers
├── App.jsx                           # Router + LanguageProvider + AuthProvider
│
├── router/
│   ├── PublicRoutes.jsx
│   ├── StudentRoutes.jsx
│   ├── InstructorRoutes.jsx
│   └── AdminRoutes.jsx
│
├── pages/
│   │
│   ├── public/
│   │   ├── HomePage.jsx              # Hero + Course catalog preview
│   │   ├── CourseCatalogPage.jsx     # Public browseable catalog
│   │   ├── CourseDetailPage.jsx      # Course info + enroll CTA
│   │   ├── LoginPage.jsx             # Phone input → OTP input
│   │   └── RegisterPage.jsx          # Phone + Name + Year + Type → OTP
│   │
│   ├── student/
│   │   ├── StudentDashboardPage.jsx  # Enrolled courses + progress
│   │   ├── MyCatalogPage.jsx         # Segmented catalog (type+year filtered)
│   │   ├── CoursePage.jsx            # Course player page
│   │   │   ├── LessonPlayer.jsx      # Self-hosted video player (HLS)
│   │   │   ├── TopicAccordion.jsx    # Sidebar curriculum
│   │   │   └── QuizEntry.jsx         # Start quiz button
│   │   ├── QuizPage.jsx              # Quiz session
│   │   │   ├── QuizTimer.jsx
│   │   │   ├── QuestionRenderer.jsx  # MCQ / T-F / Fill / Open / Ordering
│   │   │   └── QuizResultPage.jsx
│   │   ├── WalletPage.jsx            # Balance + transactions + coupon redeem
│   │   ├── CheckoutPage.jsx          # Kanga Pay + wallet option
│   │   └── ProfilePage.jsx
│   │
│   ├── instructor/
│   │   ├── InstructorDashboard.jsx
│   │   ├── CreateStudentPage.jsx     # Replaces [tutor_create_student]
│   │   ├── BulkEnrollPage.jsx        # Replaces [maim_bulk_tutor_enroll]
│   │   ├── LessonWatchlistPage.jsx
│   │   ├── QuizExportPage.jsx
│   │   ├── QuizPermissionsPage.jsx
│   │   └── CourseBuilderPage.jsx     # Create/edit courses + video upload
│   │
│   └── admin/                        # Full Arabic admin panel (see §4.4)
│       ├── AdminDashboardPage.jsx
│       ├── UserManagementPage.jsx
│       ├── CustomerListPage.jsx
│       ├── CustomerDetailPage.jsx
│       ├── CustomerSegmentsPage.jsx
│       ├── OrderManagementPage.jsx
│       ├── CouponManagementPage.jsx
│       ├── WalletLogsPage.jsx
│       ├── BannerManagementPage.jsx
│       ├── EmailCampaignsPage.jsx
│       ├── FlashSalesPage.jsx
│       └── AnalyticsPage.jsx
│
├── components/
│   ├── ui/                           # Reusable design system
│   │   ├── Button.jsx
│   │   ├── Card.jsx
│   │   ├── Modal.jsx
│   │   ├── Table.jsx
│   │   ├── Badge.jsx
│   │   └── RTLWrapper.jsx            # dir="rtl" context wrapper
│   │
│   ├── video/
│   │   ├── HLSPlayer.jsx             # hls.js video player (§4.6)
│   │   ├── VideoWatermark.jsx        # Dynamic watermark overlay
│   │   ├── VideoAccessGate.jsx       # Token check before render
│   │   └── ViewLimitBanner.jsx       # "X views remaining" banner
│   │
│   ├── quiz/
│   │   ├── MCQQuestion.jsx
│   │   ├── TrueFalseQuestion.jsx
│   │   ├── FillBlankQuestion.jsx
│   │   ├── OpenQuestion.jsx
│   │   └── OrderingQuestion.jsx
│   │
│   ├── auth/
│   │   ├── PhoneInput.jsx            # Egyptian format validator
│   │   ├── OTPInput.jsx              # 6-box OTP entry
│   │   └── ProtectedRoute.jsx
│   │
│   └── layout/
│       ├── Header.jsx                # Navigation + language toggle
│       ├── Footer.jsx
│       ├── Sidebar.jsx
│       └── LanguageToggle.jsx        # AR ↔ EN switch
│
├── hooks/
│   ├── useAuth.js
│   ├── useWallet.js
│   ├── useVideoToken.js              # Fetches signed video token
│   └── useTranslation.js            # Wraps i18next
│
├── store/
│   ├── authStore.js                  # Zustand: user + JWT token
│   ├── cartStore.js                  # Zustand: pre-checkout state
│   └── languageStore.js             # Zustand: 'ar' | 'en'
│
└── locales/
    ├── ar/
    │   ├── common.json
    │   ├── courses.json
    │   ├── quiz.json
    │   ├── wallet.json
    │   └── admin.json
    └── en/
        ├── common.json
        ├── courses.json
        ├── quiz.json
        ├── wallet.json
        └── admin.json
```

**Tech Stack:**
- **Routing:** React Router v6
- **Server State:** TanStack Query (React Query)
- **Client State:** Zustand
- **Styling:** Tailwind CSS v3 with RTL plugin (`tailwindcss-rtl`)
- **Video:** hls.js

- **i18n:** i18next + react-i18next
- **Forms:** React Hook Form + Zod validation
- **HTTP:** Axios with JWT interceptors

---

### 4.3 Internationalization — Arabic First

The platform is **Arabic-first** with English as a secondary option. This is not a simple translation layer — RTL layout, Arabic typography, and Arabic number formatting must be native.

#### Frontend (React)

```bash
npm install i18next react-i18next i18next-browser-languagedetector
```

```javascript
// src/i18n.js
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';
import arCommon from './locales/ar/common.json';
import enCommon from './locales/en/common.json';

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    fallbackLng: 'ar',    // Arabic is the default
    defaultNS: 'common',
    resources: {
      ar: { common: arCommon },
      en: { common: enCommon },
    },
    detection: {
      order: ['localStorage', 'navigator'],
      caches: ['localStorage'],
    },
    interpolation: { escapeValue: false },
  });
```

```jsx
// src/App.jsx — RTL/LTR direction sync
import { useTranslation } from 'react-i18next';

function App() {
  const { i18n } = useTranslation();
  const isRTL = i18n.language === 'ar';

  useEffect(() => {
    document.documentElement.dir = isRTL ? 'rtl' : 'ltr';
    document.documentElement.lang = i18n.language;
  }, [i18n.language]);
  // ...
}
```

```jsx
// components/layout/LanguageToggle.jsx
export function LanguageToggle() {
  const { i18n } = useTranslation();
  return (
    <button onClick={() => i18n.changeLanguage(i18n.language === 'ar' ? 'en' : 'ar')}>
      {i18n.language === 'ar' ? 'English' : 'العربية'}
    </button>
  );
}
```

**Tailwind RTL Configuration:**
```javascript
// tailwind.config.js
module.exports = {
  content: ['./src/**/*.{js,jsx}'],
  theme: { extend: {} },
  plugins: [require('tailwindcss-rtl')],
};
// Use ms-* (margin-start) instead of ml-*, me-* instead of mr-*
// These automatically flip in RTL mode
```

**Arabic Typography:**
```css
/* globals.css */
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&family=Tajawal:wght@400;500;700&display=swap');

:root {
  --font-arabic: 'Cairo', 'Tajawal', sans-serif;
  --font-english: 'Inter', sans-serif;
}

[lang="ar"] body { font-family: var(--font-arabic); }
[lang="en"] body { font-family: var(--font-english); }
```

#### Backend (Django)

```python
# config/settings/base.py
LANGUAGE_CODE = 'ar'           # Arabic as default
LANGUAGES = [
    ('ar', 'العربية'),
    ('en', 'English'),
]
USE_I18N = True
USE_L10N = True
LOCALE_PATHS = [BASE_DIR / 'locale']
```

```python
# apps/courses/models.py — bilingual fields strategy
# Option A (simple): Separate fields per language
class Course(models.Model):
    title    = models.CharField(max_length=300)      # Arabic
    title_en = models.CharField(max_length=300, blank=True)  # English

# Option B (recommended for scale): django-modeltranslation
# pip install django-modeltranslation
# auto-generates title_ar, title_en from a single title field
```

---

### 4.4 Admin Panel — Full Arabic Interface

The admin panel is a **custom React SPA** (not Django admin) to allow full Arabic interface control, RTL design, and a modern UX. It runs at `/admin/` and is protected by admin/staff role JWT.

#### Admin Panel Scope (All pages in Arabic)

| Section | Pages |
|---|---|
| **لوحة التحكم** | Overview KPIs, revenue chart, recent orders |
| **المستخدمون** | Customer list, customer detail, customer segments |
| **الكورسات** | Course list, course editor, topic/lesson manager |
| **الطلبات** | Order list, order detail, refund management |
| **الكوبونات** | Coupon create/list, wallet recharge coupons |
| **المحافظ** | Wallet transaction logs, balance adjustments |
| **الإشعارات** | WhatsApp template manager, bulk WhatsApp send |
| **الإعلانات** | Banner upload/manage (homepage banners) |
| **الحملات** | Email campaigns (Mailchimp or replacement) |
| **الأسعار** | Flash sales, bundle deals |
| **التحليلات** | Revenue, enrollment trends, quiz performance |
| **الإعدادات** | Site settings, Kanga Pay config, WhatsApp config |

#### Django REST Admin API

All admin operations go through Django REST Framework endpoints under `/api/admin/` with `IsAdminUser` or `IsStaff` permissions.

```python
# apps/users/views_admin.py
class AdminCustomerListView(ListAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = CustomerDetailSerializer
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['phone', 'first_name', 'last_name']
    ordering_fields = ['date_joined', 'wallet_balance']
```

#### Language Enforcement in Admin

All admin UI strings are in Arabic only (no language toggle in admin). The admin React app uses:
```javascript
i18n.init({ fallbackLng: 'ar', lng: 'ar' });
// Admin always Arabic, no toggle button rendered
```

---

### 4.5 Self-Hosted Video Pipeline

Videos will be **uploaded by instructors through the website** and served via HLS with encryption. This replaces the YouTube dependency entirely.

#### Upload Architecture

```
Instructor (browser)
    │
    ▼
React <VideoUploadWidget />
    │   (chunked multipart upload using tus protocol)
    ▼
Django /api/videos/upload/              ← DRF endpoint
    │
    ├── Validate: file type (mp4/mov/avi), size limit (e.g. 5GB)
    ├── Save original to S3/Cloudflare R2 (private bucket)
    ├── Create Video(status='processing') record
    └── Dispatch Celery task: transcode_video.delay(video_id)
    │
    ▼
Celery Worker (FFmpeg)
    │
    ├── Transcode to multiple HLS qualities:
    │   ├── 1080p → stream_1080/
    │   ├── 720p  → stream_720/
    │   ├── 480p  → stream_480/
    │   └── 360p  → stream_360/
    │
    ├── Generate AES-128 encryption key per video
    ├── Encrypt each HLS segment with the per-video key
    ├── Store encrypted segments to private CDN bucket
    ├── Store key in Django database (NOT in bucket)
    └── Update Video(status='ready', duration=X)
```

#### Django Video Model

```python
# apps/videos/models.py

class Video(models.Model):
    STATUS = [
        ('uploading', 'جاري الرفع'),
        ('processing', 'جاري المعالجة'),
        ('ready', 'جاهز'),
        ('failed', 'فشل'),
    ]
    title          = models.CharField(max_length=300)
    uploaded_by    = models.ForeignKey('users.User', on_delete=models.PROTECT)
    original_path  = models.CharField(max_length=500)  # S3 key
    hls_path       = models.CharField(max_length=500, blank=True)  # Base HLS path in S3
    aes_key        = models.BinaryField(max_length=16)  # 16-byte AES-128 key (stored encrypted)
    aes_key_id     = models.CharField(max_length=50)    # Key identifier for m3u8
    duration_seconds = models.PositiveIntegerField(default=0)
    file_size_bytes  = models.BigIntegerField(default=0)
    status         = models.CharField(choices=STATUS, max_length=15, default='uploading')
    created_at     = models.DateTimeField(auto_now_add=True)
    thumbnails     = models.JSONField(default=list)  # [{quality:'720', url:'...'}, ...]

class VideoAccessToken(models.Model):
    """Short-lived token granting access to one video for one user"""
    token      = models.UUIDField(default=uuid.uuid4, unique=True)
    user       = models.ForeignKey('users.User', on_delete=models.CASCADE)
    video      = models.ForeignKey(Video, on_delete=models.CASCADE)
    lesson     = models.ForeignKey('courses.Lesson', on_delete=models.CASCADE)
    issued_at  = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()  # issued_at + 20 minutes
    ip_address = models.GenericIPAddressField()
    used       = models.BooleanField(default=False)
```

#### Celery Transcode Task

```python
# apps/videos/tasks.py
import subprocess
from celery import shared_task

@shared_task(bind=True, max_retries=3)
def transcode_video(self, video_id):
    video = Video.objects.get(id=video_id)
    
    # Download from S3
    # Run FFmpeg for each quality:
    qualities = [
        ('1080p', '1920x1080', '4000k'),
        ('720p',  '1280x720',  '2500k'),
        ('480p',  '854x480',   '1200k'),
        ('360p',  '640x360',   '800k'),
    ]
    
    for name, resolution, bitrate in qualities:
        cmd = [
            'ffmpeg', '-i', input_path,
            '-vf', f'scale={resolution}',
            '-b:v', bitrate,
            '-hls_time', '6',
            '-hls_key_info_file', key_info_path,   # AES-128 encryption
            '-hls_playlist_type', 'vod',
            '-hls_segment_filename', f'{output_dir}/{name}_%04d.ts',
            f'{output_dir}/{name}.m3u8',
        ]
        subprocess.run(cmd, check=True)
    
    # Generate master playlist
    # Upload all segments + playlists to private S3 bucket
    # Update video.status = 'ready'
```

---

### 4.6 Advanced Video Protection Strategy

This is the core security concern. The strategy uses **layered defense** across backend, CDN, and frontend — no single layer is sufficient alone.

---

#### Layer 1 — AES-128 HLS Encryption (Primary Protection)

**What it does:** Every 6-second `.ts` segment of the video is encrypted with AES-128-CBC. Without the decryption key, the downloaded `.ts` files are unplayable binary data.

**How it works:**

```
# HLS key info file (referenced in FFmpeg -hls_key_info_file)
https://api.elkaed.online/api/videos/key/{video_id}?token={access_token}
/tmp/video_aes.key
0000000000000000
```

```python
# The key delivery endpoint — Django view
# apps/videos/views.py

class VideoKeyView(APIView):
    permission_classes = []  # Auth via token, not JWT
    
    def get(self, request, video_id):
        token_str = request.GET.get('token')
        
        # 1. Validate access token
        try:
            access_token = VideoAccessToken.objects.get(
                token=token_str,
                video_id=video_id,
                expires_at__gt=now(),
            )
        except VideoAccessToken.DoesNotExist:
            return Response(status=403)
        
        # 2. IP lock — token must be used from same IP it was issued to
        if access_token.ip_address != get_client_ip(request):
            return Response(status=403)
        
        # 3. Fetch decryption key from DB (never stored in CDN/bucket)
        video = Video.objects.get(id=video_id)
        
        # 4. Return raw 16-byte AES key (only for valid tokens)
        return HttpResponse(
            video.aes_key,
            content_type='application/octet-stream'
        )
```

**Result:** Even if a student downloads every `.ts` file and the `.m3u8` playlist, they cannot play the video without the AES key. The key is only served by the Django backend to valid, IP-locked, time-limited tokens.

---

#### Layer 2 — Signed CDN URLs (Segment Access Control)

Even with HLS encryption, the `.ts` segment files should not be publicly accessible. Every CDN URL must be signed and short-lived.

**With Cloudflare R2 + Cloudflare Workers:**
```javascript
// Cloudflare Worker: sign each segment URL
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const token = url.searchParams.get('cf_token');
    const expiry = url.searchParams.get('expires');
    
    // Verify HMAC signature
    const expected = await hmacSign(url.pathname + expiry, env.SIGNING_SECRET);
    if (token !== expected || Date.now() > expiry * 1000) {
      return new Response('Forbidden', { status: 403 });
    }
    
    // Serve from private R2 bucket
    const object = await env.VIDEO_BUCKET.get(url.pathname.slice(1));
    return new Response(object.body);
  }
};
```

**With AWS S3 + CloudFront:**
```python
# Django generates signed CloudFront URLs (15-minute expiry)
import boto3
from botocore.signers import CloudFrontSigner
from cryptography.hazmat.primitives import hashes, serialization

def generate_signed_url(s3_key: str, expires_in_seconds=900):
    expiry = datetime.utcnow() + timedelta(seconds=expires_in_seconds)
    cloudfront_signer = CloudFrontSigner(CF_KEY_PAIR_ID, rsa_signer)
    return cloudfront_signer.generate_presigned_url(
        f"https://{CF_DOMAIN}/{s3_key}",
        date_less_than=expiry
    )
```

---

#### Layer 3 — Video Access Token System (Enrollment Gate)

**No student can obtain a video URL without:**
1. Being authenticated (valid JWT)
2. Having an active enrollment in the parent course
3. Requesting a `VideoAccessToken` from the Django API (not the CDN directly)

```python
# apps/videos/views.py

class RequestVideoAccessView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, lesson_id):
        lesson = get_object_or_404(Lesson, id=lesson_id)
        
        # 1. Check enrollment
        has_enrollment = Enrollment.objects.filter(
            student=request.user,
            course=lesson.topic.course,
            status='active'
        ).exists()
        
        if not has_enrollment and not lesson.is_free_preview:
            return Response({'error': 'لا يوجد اشتراك'}, status=403)
        
        # 2. Check view limit
        progress, _ = LessonProgress.objects.get_or_create(
            student=request.user, lesson=lesson
        )
        if lesson.view_limit > 0 and progress.view_count >= lesson.view_limit:
            return Response({'error': 'تجاوزت الحد المسموح به من المشاهدات'}, status=403)
        
        # 3. Issue access token (20 min, IP-locked)
        token = VideoAccessToken.objects.create(
            user=request.user,
            video=lesson.video,
            lesson=lesson,
            expires_at=now() + timedelta(minutes=20),
            ip_address=get_client_ip(request)
        )
        
        # 4. Increment view count
        LessonProgress.objects.filter(
            student=request.user, lesson=lesson
        ).update(view_count=F('view_count') + 1)
        
        # 5. Return signed master playlist URL (not raw S3 path)
        signed_playlist_url = generate_signed_hls_url(
            lesson.video.hls_path,
            token=str(token.token),
            expires_in=1200  # 20 minutes
        )
        
        return Response({
            'playlist_url': signed_playlist_url,
            'duration_seconds': lesson.video.duration_seconds,
            'views_remaining': max(0, lesson.view_limit - progress.view_count - 1) if lesson.view_limit > 0 else None,
        })
```

---

#### Layer 4 — Dynamic Canvas Watermarking

**What it does:** Renders the student's phone number as a semi-transparent overlay on the video canvas. Any screen recording captures the identity of the leaker.

```jsx
// components/video/VideoWatermark.jsx
import { useEffect, useRef } from 'react';
import { useAuth } from '../../hooks/useAuth';

export function VideoWatermark({ videoRef }) {
  const canvasRef = useRef(null);
  const { user } = useAuth();
  const animFrameRef = useRef(null);
  
  useEffect(() => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) return;
    
    const ctx = canvas.getContext('2d');
    const text = user?.phone || 'elkaed.online';
    
    // Positions change every 8 seconds to prevent cropping the watermark
    const positions = [
      { x: 0.15, y: 0.15 },
      { x: 0.70, y: 0.80 },
      { x: 0.50, y: 0.45 },
      { x: 0.20, y: 0.75 },
    ];
    let posIndex = 0;
    
    const draw = () => {
      canvas.width = video.videoWidth || video.clientWidth;
      canvas.height = video.videoHeight || video.clientHeight;
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      
      const pos = positions[posIndex % positions.length];
      ctx.font = `bold ${canvas.width * 0.025}px Cairo, sans-serif`;
      ctx.fillStyle = 'rgba(255, 255, 255, 0.22)';
      ctx.textAlign = 'center';
      ctx.fillText(text, canvas.width * pos.x, canvas.height * pos.y);
      ctx.fillText('elkaed.online', canvas.width * pos.x, canvas.height * pos.y + canvas.width * 0.03);
      
      animFrameRef.current = requestAnimationFrame(draw);
    };
    
    const rotatePosition = setInterval(() => { posIndex++; }, 8000);
    draw();
    
    return () => {
      cancelAnimationFrame(animFrameRef.current);
      clearInterval(rotatePosition);
    };
  }, [user]);
  
  return (
    <canvas
      ref={canvasRef}
      style={{
        position: 'absolute', top: 0, left: 0,
        width: '100%', height: '100%',
        pointerEvents: 'none',
        zIndex: 10,
      }}
    />
  );
}
```

---

#### Layer 5 — HLS Player with Security Hardening

```jsx
// components/video/HLSPlayer.jsx
import Hls from 'hls.js';

export function HLSPlayer({ playlistUrl, lesson }) {
  const videoRef = useRef(null);
  const hlsRef = useRef(null);
  
  useEffect(() => {
    if (!playlistUrl) return;
    const video = videoRef.current;
    
    if (Hls.isSupported()) {
      const hls = new Hls({
        // Pass access token with every segment/key request
        xhrSetup: (xhr, url) => {
          // The key delivery endpoint is authenticated via URL token
          // segment URLs are signed CloudFront/R2 URLs
        },
        // Disable quality switching manifest caching to prevent URL extraction
        manifestLoadingMaxRetry: 2,
        levelLoadingMaxRetry: 2,
      });
      
      hls.loadSource(playlistUrl);
      hls.attachMedia(video);
      hlsRef.current = hls;
    } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
      // Safari native HLS
      video.src = playlistUrl;
    }
    
    return () => hlsRef.current?.destroy();
  }, [playlistUrl]);
  
  return (
    <div style={{ position: 'relative' }}>
      <video
        ref={videoRef}
        controls
        controlsList="nodownload nofullscreen noremoteplayback"
        disablePictureInPicture
        onContextMenu={e => e.preventDefault()}  // Block right-click
        style={{ width: '100%' }}
      />
      <VideoWatermark videoRef={videoRef} />
    </div>
  );
}
```

---

#### Layer 6 — Anti-DevTools & Screen Capture Deterrence

```javascript
// utils/securityDeterrents.js
// These are deterrents, not hard blocks — determined users bypass them.
// Their purpose is to raise the effort bar and ensure casual downloaders stop.

export function activateVideoDeterrents() {
  // Block common keyboard shortcuts for page source / inspector
  document.addEventListener('keydown', (e) => {
    const blocked = (
      (e.ctrlKey && ['u', 's', 'p'].includes(e.key.toLowerCase())) ||
      e.key === 'F12' ||
      (e.ctrlKey && e.shiftKey && ['i', 'j', 'c'].includes(e.key.toLowerCase()))
    );
    if (blocked) {
      e.preventDefault();
      showToast('هذا الإجراء غير مسموح به في هذه الصفحة');
    }
  });
  
  // Detect rapid DevTools open (size-based heuristic)
  const threshold = 160;
  const devToolsCheck = setInterval(() => {
    if (window.outerWidth - window.innerWidth > threshold ||
        window.outerHeight - window.innerHeight > threshold) {
      // Pause video, show warning
      document.querySelectorAll('video').forEach(v => v.pause());
    }
  }, 1000);
  
  return () => clearInterval(devToolsCheck);
}
```

---

#### Layer 7 — Backend Rate Limiting & Abuse Prevention

```python
# Per-user rate limits on video access token generation
# Using django-ratelimit

from django_ratelimit.decorators import ratelimit

class RequestVideoAccessView(APIView):
    @method_decorator(ratelimit(key='user', rate='20/h', method='POST', block=True))
    def post(self, request, lesson_id):
        ...

# Also: log every token request for anomaly detection
class VideoAccessLog(models.Model):
    user       = models.ForeignKey('users.User', on_delete=models.CASCADE)
    lesson     = models.ForeignKey('courses.Lesson', on_delete=models.CASCADE)
    ip_address = models.GenericIPAddressField()
    user_agent = models.CharField(max_length=500)
    timestamp  = models.DateTimeField(auto_now_add=True)
    token_issued = models.BooleanField(default=True)
    denial_reason = models.CharField(max_length=100, blank=True)
```

---

#### Video Protection Summary

| Layer | Technique | What It Blocks |
|---|---|---|
| 1 | AES-128 HLS Encryption | Downloaded `.ts` segments are unplayable without key |
| 2 | Signed CDN URLs (15-20 min) | Direct S3/R2 URL sharing |
| 3 | Enrollment-gated access tokens | Non-enrolled users getting any URL |
| 4 | IP-locked tokens | Token sharing between users |
| 5 | View count limiting | Sharing account credentials |
| 6 | Dynamic moving watermark | Screen recording → leaker identified |
| 7 | `controlsList="nodownload"` | Browser download button |
| 8 | `disablePictureInPicture` | PiP and platform-level capture |
| 9 | Right-click disabled | `<video>` context menu "Save video" |
| 10 | Rate limiting | Token farming / scraping |
| 11 | DevTools deterrence | Casual inspector URL extraction |

**Realistic Threat Model:** Layers 1–5 stop 99% of users. Layer 6 (watermark) enables you to identify and ban the remaining 1% who screen-record and share. True DRM (Widevine/FairPlay) requires a paid video host (Mux, Bunny.net, Cloudflare Stream) — add this in a later phase if warranted by piracy incidents.

---

### 4.7 Feature Parity Plan

| Current WordPress Feature | Django + React Solution |
|---|---|
| Phone OTP login (maim-phone) | Django: `phonenumbers` + wa-ma.org service. JWT via `djangorestframework-simplejwt`. Redis OTP cache (5-min TTL, 3-attempt limit) |
| WhatsApp quiz notifications (functions.php) | Django signal on `post_save(QuizAttempt, status='submitted')` → Celery task → wa-ma.org API |
| Student segmentation by type+year (maim-student-courses) | Django filter: `Course.objects.filter(category__student_type=user.student_type, category__academic_year=user.academic_year)` |
| Wallet purchase flow (maim-student-courses + ajax) | Django atomic transaction: `select_for_update()` on user balance → debit → create Order → create Enrollment |
| Coupon-to-wallet redemption (maim-user-wallet-coupons) | `CouponRedemption` with unique_together constraint. `WalletTransaction` audit log |
| Bulk enrollment (maim-instructor-enrollment) | Instructor API: `POST /api/instructor/courses/{id}/enroll/` accepting `{user_ids: [...]}` |
| Create student by instructor (maim-tutor-create-student) | `POST /api/instructor/students/` — creates User with role='student', sends OTP via WhatsApp |
| Quiz permissions toggle (tutor-quiz-permissions) | `PATCH /api/admin/quizzes/{id}/` with `{is_locked: true}`. Instructor can toggle their own quiz |
| View limiting (tutor-views-limiter) | `LessonProgress.view_count` checked on every video token request |
| Kanga Pay payment (kanga-pay plugin) | Django: `POST /api/payments/kanga-pay/webhook/` — verify HMAC signature → complete Order → create Enrollment |
| WooCommerce checkout flow (ecademy-child) | `POST /api/orders/` → returns Kanga Pay payment URL → redirect → webhook confirms |
| Course compare (tutor-course-compare) | React: `CompareDrawer` component, state in Zustand (max 3 courses) |
| Quiz export CSV (instructor dashboard tab) | `GET /api/instructor/quizzes/{id}/export/?format=csv` — streams Django CSV response |
| Lesson watchlist (instructor tab) | `POST /api/instructor/watchlist/{lesson_id}/` — `LessonWatchlist` model |
| Mailchimp (abandoned) | Replace with Brevo (formerly Sendinblue) — free tier adequate, has Arabic support |

---

## 4.8 PHASE 3 — IMPLEMENTATION SUMMARY

> **Status:** ✅ Complete — 2026-07-14  
> **Scope:** Full Django REST API backend — all apps, models, views, admin, Celery tasks, and migrations

---

### 4.8.1 Apps Delivered

| App | Models | API Endpoints | Admin | Migrations |
|---|---|---|---|---|
| `users` | User, PhoneOTP | 6 endpoints | ✅ (CSV export, WhatsApp action) | ✅ `0001_initial` |
| `courses` | Category, Course, Topic, Lesson, Enrollment, LessonProgress | 6 endpoints | ✅ | ✅ `0001–0002` |
| `quizzes` | Quiz, Question, AnswerChoice, QuizAttempt, AttemptAnswer | 4 endpoints | ✅ (lock/unlock actions) | ✅ `0001_initial` |
| `commerce` | Order, OrderItem, Coupon, CouponRedemption, WalletTransaction, FlashSale, Bundle | 8 endpoints | ✅ | ✅ `0001–0003` |
| `videos` | Video, VideoAccessToken, VideoAccessLog | 3 endpoints | ✅ | ✅ `0001` |
| `notifications` | HomepageBanner, NotificationTemplate, Campaign | — (admin-only) | ✅ (Campaign send action) | ✅ `0001–0002` |

---

### 4.8.2 Authentication & Users

| Feature | Endpoint | Notes |
|---|---|---|
| Send OTP | `POST /api/auth/send-otp/` | WhatsApp via wa-ma.org, Celery task |
| Verify OTP + JWT | `POST /api/auth/verify-otp/` | Issues access + refresh tokens |
| Token refresh | `POST /api/auth/token/refresh/` | simplejwt standard |
| Get profile | `GET /api/auth/profile/` | — |
| Update profile | `PATCH /api/auth/profile/` | first_name, last_name, guardian_phone |
| Create student | `POST /api/auth/create-student/` | Instructor/admin only; phone = default password |
| Analytics | `GET /api/auth/analytics/` | Admin/staff only; students, revenue, enrollments, top courses |

**Password handling:** `PhpassPasswordHasher` bridges WP phpass hashes — migrated users can log in with existing WP password without reset.

---

### 4.8.3 Courses & Enrollment

| Feature | Endpoint | Notes |
|---|---|---|
| Course list | `GET /api/courses/` | Auto-filters by user's student_type × academic_year |
| Course detail | `GET /api/courses/<slug>/` | Includes topics + lessons tree |
| Enroll | `POST /api/courses/<id>/enroll/` | Wallet first; falls back to Kanga Pay; applies active FlashSale price |
| My enrollments | `GET /api/courses/my-enrollments/` | Active only |
| Bulk enroll | `POST /api/courses/bulk-enroll/` | Instructor/admin; phone list in; enrolled/skipped out |

---

### 4.8.4 Quiz Engine

| Feature | Endpoint | Notes |
|---|---|---|
| Quiz detail | `GET /api/quizzes/<id>/` | Questions + choices; optional shuffle; enrollment-gated |
| Start attempt | `POST /api/quizzes/<id>/start/` | Idempotent; enforces `is_locked` + `attempts_allowed` |
| Submit attempt | `POST /api/quizzes/attempts/<id>/submit/` | Auto-grades MCQ + TF; open/fill/ordering → manual review (`is_reviewed=False`); WhatsApp to student + guardian |
| Attempt result | `GET /api/quizzes/attempts/<id>/` | Respects `hide_results` flag |

**Grading:** MCQ — choice PK match. TF — compare `given_answer` text to `is_correct=True` choice text. fill/open/ordering — deferred to instructor review.

---

### 4.8.5 Commerce & Payments

| Feature | Endpoint | Notes |
|---|---|---|
| Wallet balance + history | `GET /api/commerce/wallet/` | Last 20 transactions |
| Coupon redeem | `POST /api/commerce/coupons/redeem/` | wallet_recharge type; unique-per-user enforced |
| Kanga Pay webhook | `POST /api/commerce/kanga-pay/webhook/` | HMAC-verified; completes order + enrolls + WhatsApp |
| Active flash sales | `GET /api/commerce/flash-sales/` | Time-filtered; returns original + sale price |
| Bundle list | `GET /api/commerce/bundles/` | — |
| Bundle purchase | `POST /api/commerce/bundles/<id>/purchase/` | Wallet debit + multi-course enrollment; partial enroll OK |

**FlashSale integration:** `EnrollView` queries active sales before any payment; passes `effective_price` to `wallet_purchase` and Kanga Pay init.

---

### 4.8.6 Video Access System (Layers 1 + 3 + 5 + view limiting)

| Feature | Endpoint | Notes |
|---|---|---|
| Request token | `POST /api/videos/lesson/<id>/token/` | Enrollment check, view_limit check, IP-locked 20-min UUID token; returns `views_remaining` |
| AES key delivery | `GET /api/videos/key/<uuid>/` | No JWT auth — validated by token + IP match; returns 16-byte binary; increments view_count |
| Save progress | `POST /api/videos/lesson/<id>/progress/` | position_seconds + completion flag |

**Implemented layers:** AES-128 token gate (Layer 1 key delivery), enrollment gate (Layer 3), view count limiting (Layer 5).  
**Pending:** CloudFront signed URLs (Layer 2) — add when `CLOUDFRONT_PRIVATE_KEY` env var is available. Rate limiting (Layer 7) — add `django-ratelimit` when abuse is observed. Video upload + FFmpeg transcoding task (§4.5) — not yet implemented; instructors use YouTube embed as fallback.

---

### 4.8.7 Notifications & Campaigns

| Feature | How |
|---|---|
| WhatsApp OTP | Celery task → wa-ma.org; retry ×3 |
| Quiz result notification | On submit: student + guardian; Arabic message with score |
| Enrollment confirmation | After wallet purchase and Kanga Pay webhook |
| WhatsApp Campaign | `Campaign` model; admin triggers `send_campaign_task`; segments: all / students / center / online / 1st / 2nd / 3rd secondary |
| Notification templates | `NotificationTemplate` model — editable in Django admin |
| Homepage banners | `HomepageBanner` model — managed in Django admin with scheduling |

---

### 4.8.8 Admin Capabilities (Django Admin — Arabic)

| Section | Features |
|---|---|
| Users | List/search/filter by role, type, year; CSV export; WhatsApp bulk send; wallet balance visible |
| Courses | Course/topic/lesson management; prepopulated slugs |
| Quizzes | Lock/unlock bulk actions; question + answer inline editing |
| Commerce | Order inline items; coupon management; wallet transaction log |
| Videos | Status tracking; access log |
| Notifications | Banner scheduling; template editing; Campaign send action |

---

### 4.8.9 Pre-Phase-4 Fixes Applied

| Fix | File | Why |
|---|---|---|
| Created `users/migrations/0001_initial` | users/migrations/ | No migration existed; DB could not be created |
| Created `quizzes/migrations/0001_initial` | quizzes/migrations/ | Same — FK chain broken without it |
| Created `backend/.env` template | backend/.env | `decouple` requires `SECRET_KEY`; needed for `makemigrations` |
| Flash sale price in `wallet_purchase` | commerce/services.py | `wallet_purchase` now accepts `price=` param; service used effective price |
| Flash sale price in `EnrollView` | courses/views.py | Queries active `FlashSale` before payment; passes `effective_price` to both wallet and Kanga Pay paths |
| `views_remaining` in token response | videos/views.py + serializers.py | Blueprint specifies this field; HLS player needs it for "X views left" banner |
| Deduplicated query in `SubmitAttemptView` | quizzes/views.py | `valid_question_ids` derived from `questions_map` — one fewer DB query per submit |

---

### 4.8.10 What Phase 4 (ETL) Needs Next

- PostgreSQL database running at `localhost:5432/elkaed_dev` (or production equivalent)
- `python manage.py migrate` — applies all 14 migrations in correct dependency order
- WordPress SQL dump at accessible path for ETL scripts
- Kanga Pay credentials transferred from WP options table → `.env`
- wa-ma.org API key rotated and set in `.env`
- ETL Pass 1 (`etl_pass_1_users.py`) already exists — remaining passes (categories, courses, topics, lessons, quizzes, enrollments, orders, wallet) to be built

---

## 5. PHASE 4 — ETL STRATEGY

### 5.1 ETL Command Architecture

```
python manage.py migrate_from_wordpress \
  --sql-path=/path/to/SCWORDPRESS-323039458d.sql \
  --dry-run          # Preview only, no DB writes
  --pass=users       # Run only specific pass
  --batch-size=500   # Rows per bulk_create
```

All passes are **idempotent** — safe to re-run. They use `wp_*_id` fields as deduplication keys with `get_or_create` or `update_or_create`.

### 5.2 Seven-Pass ETL Plan

---

#### Pass 1 — Users & Profiles

```python
# Source: 29_users JOIN 29_usermeta

# Transform rules:
# user_login → User.phone (already in 201XXXXXXXXX format)
# display_name → first_name + last_name (split on first space)
# user_registered → date_joined
# usermeta[student_type] → User.student_type
# usermeta[academic_year] → User.academic_year  
# usermeta[billing_company] → User.guardian_phone
# usermeta[_user_balance] → User.wallet_balance
# wp_capabilities → User.role:
#   contains 'tutor_instructor' → 'instructor'
#   contains 'administrator' → 'admin'
#   else → 'student'
# user_pass (phpass) → stored via custom hasher (see §5.3)

# Skip: fake email field (do not migrate)
# Skip: billing_first_name/last_name in usermeta (duplicated in display_name)
```

#### Pass 2 — Categories

```python
# Source: 29_terms + 29_term_taxonomy WHERE taxonomy='course-category'

# For each term: create Category(name=term.name, slug=term.slug)
# Infer student_type from name patterns:
#   contains 'أونلاين' or 'online' → 'online'
#   contains 'سنتر' or 'center' → 'center'
# Infer academic_year from name patterns:
#   contains 'أول' or 'first' → '1st'
#   contains 'ثاني' or 'second' → '2nd'
#   contains 'ثالث' or 'third' → '3rd'
```

#### Pass 3 — Courses, Topics, Lessons

```python
# Source: 29_posts WHERE post_type IN ('courses', 'topics', 'lesson')
#         + 29_postmeta

# Courses:
#   post_type='courses', post_status='publish' → Course
#   postmeta[tutor_course_price] → Course.price
#   postmeta[_thumbnail_id] → Course.thumbnail (copy image file)
#   term relationships → Course.category
#   wp_post_id for deduplication

# Topics: post_type='topics', post_parent=course_id → Topic
#   menu_order → Topic.order

# Lessons: post_type='lesson', post_parent=topic_id → Lesson
#   postmeta[_video] = phpserialize.loads() → extract source + video_id
#   IF source='youtube' → Lesson.video_source='youtube', Lesson.youtube_id=...
#   IF source='html5' → flag for manual video upload after ETL
#   menu_order → Lesson.order
```

#### Pass 4 — Quizzes & Questions

```python
# Source: 29_posts WHERE post_type='tutor_quiz'
#         + 29_tutor_quiz_questions
#         + 29_tutor_quiz_question_answers

# Quiz: tutor_quiz post → Quiz(topic=parent_topic)
#   postmeta[_forbidden_take] → is_locked
#   postmeta[_forbidden_attempt_details] → hide_results
#   postmeta[tutor_quiz_option] = phpserialize → time_limit, pass_mark, attempts_allowed

# Question: tutor_quiz_questions rows → Question
#   question_settings (JSON) → parse by question_type:
#     'single_choice'/'multiple_choice' → 'mcq'
#     'true_false' → 'tf'
#     'fill_in_the_blank' → 'fill'
#     'open_ended' → 'open'
#     'ordering' → 'ordering'

# AnswerChoice: tutor_quiz_question_answers rows → AnswerChoice
#   bulk_create(batch_size=500)
```

#### Pass 5 — Quiz Attempts & Answers (Largest Pass)

```python
# Source: 29_tutor_quiz_attempts (9,767 rows)
#         + 29_tutor_quiz_attempt_answers (246,864 rows)

# Strategy: chunked bulk_create with tqdm progress bar

for chunk in chunks(all_attempts, size=200):
    QuizAttempt.objects.bulk_create(chunk, ignore_conflicts=True)

for chunk in chunks(all_answers, size=1000):
    AttemptAnswer.objects.bulk_create(chunk, ignore_conflicts=True)

# Map attempt_status:
#   'attempt_started' → 'in_progress'
#   'attempt_ended' → 'submitted'
# result: 'pass' / 'fail' → preserved

# Skip if user_id or quiz_id not found in Django DB (log to etl_skipped.log)
```

#### Pass 6 — Orders & Enrollments

```python
# Source: 29_tutor_orders + 29_tutor_order_items + 29_tutor_earnings
#         ALSO: 29_posts WHERE post_type='tutor_enrolled' (legacy fallback)

# Primary: use 29_tutor_orders as source of truth
# Map tutor_orders.payment_method → Order.payment_method
# Map tutor_orders.transaction_id → Order.transaction_id
# Map tutor_orders.order_status:
#   'completed' → Enrollment(status='active')
#   'cancelled' → no enrollment
#   'pending' → Order without Enrollment

# Fallback: for tutor_enrolled posts with no matching tutor_order:
#   create Enrollment(status='active', payment_method='manual')

# Deduplication: Enrollment.objects.get_or_create(student, course)
#   if duplicate, keep the older one (earlier enrolled_at)
```

#### Pass 7 — Wallet & Coupons

```python
# Source: 29_coupon_redemptions (custom table)
#         + 29_posts WHERE post_type='shop_coupon'

# WooCommerce coupons → Coupon model
# 29_coupon_redemptions → CouponRedemption model
# User.wallet_balance already set in Pass 1 from _user_balance
# Create synthetic WalletTransaction records for each redemption
#   type='credit', reference=coupon_code, amount=redemption.amount
```

### 5.3 Critical ETL Technical Details

#### phpass Password Migration

```python
# requirements: pip install passlib

from passlib.hash import phpass

class PhpassPasswordHasher:
    """Custom Django password hasher for migrated WordPress users."""
    algorithm = 'phpass'
    
    def verify(self, password, encoded):
        _, _, hashed = encoded.split('$', 2)
        return phpass.verify(password, '$P$' + hashed)
    
    def encode(self, password, salt):
        return 'phpass$$' + phpass.hash(password)[3:]  # strip $P$

# settings.py
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',  # new users
    'apps.users.hashers.PhpassPasswordHasher',             # migrated users
]
# Django tries hashers in order. On first login with phpass hash,
# it verifies with phpass, then auto-upgrades to Argon2.
```

#### PHP serialize() Parsing

```python
# requirements: pip install phpserialize
import phpserialize

def parse_video_meta(raw_meta_value: str) -> dict:
    try:
        data = phpserialize.loads(raw_meta_value.encode('utf-8'), decode_strings=True)
        return {
            'source': data.get('source', 'youtube'),
            'video_id': data.get('source_youtube_id') or data.get('source_video_id', ''),
        }
    except Exception:
        return {'source': 'unknown', 'video_id': ''}
```

#### Image URL Rewriting

```python
# After ETL: rewrite all content image URLs
OLD_BASE = 'https://elkaed.online/wp-content/uploads/'
NEW_BASE = 'https://cdn.elkaed.online/uploads/'

Course.objects.filter(description__contains=OLD_BASE).update(
    description=Replace('description', Value(OLD_BASE), Value(NEW_BASE))
)
# Run same for Lesson.content, Question.text, etc.
```

### 5.4 ETL Validation Checklist

After running all passes, validate:

```bash
# Check user counts
python manage.py shell -c "from apps.users.models import User; print(User.objects.count())"
# Expected: ~5,483

# Check enrollments
python manage.py shell -c "from apps.courses.models import Enrollment; print(Enrollment.objects.count())"

# Check quiz attempts
python manage.py shell -c "from apps.quizzes.models import QuizAttempt; print(QuizAttempt.objects.count())"
# Expected: ~9,767

# Spot-check specific student
python manage.py shell -c "
from apps.users.models import User
u = User.objects.get(phone='201XXXXXXXXX')
print(u.full_name, u.student_type, u.academic_year, u.wallet_balance)
print(u.enrollments.count(), 'enrollments')
"
```

---

## 5.5 PHASE 4 — IMPLEMENTATION SUMMARY

All 7 ETL passes + master command + validation command implemented in `backend/apps/etl/management/commands/`.

### Files Delivered

| File | Scope |
|---|---|
| `etl_pass_1_users.py` | 5,483 users: phone normalization, phpass hash bridging, wallet balance, academic_year mapping |
| `etl_pass_2_categories.py` | `29_terms` + `29_term_taxonomy` → `Category`; two-pass parent FK linking by slug |
| `etl_pass_3_courses.py` | `29_posts` → Course/Topic/Lesson; sub-pass C parses video meta via phpserialize |
| `etl_pass_4_quizzes.py` | `29_tutor_quiz_questions` + `29_tutor_quiz_question_answers` → Quiz/Question/AnswerChoice; WP→Django type map |
| `etl_pass_5_attempts.py` | 9,767 attempts + 246,864 answers; LIMIT/OFFSET streaming to avoid OOM on answer table |
| `etl_pass_6_orders.py` | `29_tutor_orders` → Order/OrderItem (sub-A), Enrollment from completed orders (sub-B), legacy `tutor_enrolled` posts (sub-C) |
| `etl_pass_7_wallet.py` | `29_posts` shop_coupon → Coupon; `29_coupon_redemptions` → CouponRedemption + WalletTransaction |
| `etl_run_all.py` | Master: runs passes 1-7 in sequence; `--dry-run`, `--batch-size`, `--start-pass N` |
| `etl_validate.py` | Post-ETL row count report vs expected ranges |

### Key Technical Decisions

- **pymysql** throughout (not psycopg2) — WP DB is MariaDB 10.11, port 3306
- **`ACADEMIC_YEAR_MAP`** in Pass 1: `first_secondary→1st`, `second_secondary→2nd`, `third_secondary→3rd`
- **phpass bridging**: `phpass$$<hash>` prefix lets `PhpassPasswordHasher` verify WP passwords; auto-upgrades to Argon2 on first login
- **Idempotency**: all passes use `get_or_create` / `update_or_create` on WP ID fields — safe to re-run
- **Answer streaming (Pass 5)**: 246,864 rows processed in `chunk_size` batches via `LIMIT/OFFSET` — never fetchall
- **Cache dicts (Pass 6)**: `user_cache` and `course_cache` loaded once before loops — no per-row DB queries
- **`etl_run_all --start-pass N`**: resume from any pass without repeating earlier ones
- **Skip logs**: each pass writes `etl_skipped_*.log` for rows that couldn't be mapped

### Known Ceilings (ponytail notes)

- `Order.created_at` is `auto_now_add=True` — WP original order timestamp not preserved. Remove `auto_now_add` and add `created_at` to `update_or_create` defaults if original dates are needed.
- `AttemptAnswer.wp_answer_id` has no `unique=True` constraint — re-runs with `bulk_create(ignore_conflicts=True)` will skip duplicates but only if the field is made unique. Add migration `unique=True` before production ETL run.
- `WalletTransaction.balance_after` uses the Pass-1 wallet snapshot — not recalculated from transaction history.

### Run Order

```bash
cd backend
python manage.py etl_run_all --dry-run          # preview all passes
python manage.py etl_run_all --batch-size 500   # full run
python manage.py etl_validate                   # check counts
```

---

## 6. SYSTEM ENHANCEMENT RECOMMENDATIONS

These are **new capabilities** not in the current WordPress system, recommended to add during the migration window.

---

### 6.1 Authentication & Security Enhancements

#### Two-Factor Login Upgrade
- Add **biometric auth** support via WebAuthn (passkeys) for mobile browsers
- OTP code should expire in **5 minutes** with a **3-attempt limit** before 30-minute lockout
- Login history page: "آخر دخول من: iPhone - القاهرة" with suspicious login WhatsApp alert

#### Session Management
- JWT refresh tokens stored in `HttpOnly Secure SameSite=Strict` cookies (not localStorage)
- Access token: 15-minute lifetime
- Refresh token: 30-day lifetime with rotation on use
- Force logout all sessions on password change

---

### 6.2 Learning Experience Enhancements

#### Adaptive Course Catalog
- **Smart recommendations:** Based on student's completed quizzes and scores, recommend courses they're likely weak in
- **Progress dashboard:** Visual progress bar per course + overall academic year completion percentage

#### Content Drip Scheduling
```python
class LessonDripRule(models.Model):
    lesson      = models.OneToOneField(Lesson, on_delete=models.CASCADE)
    unlock_days = models.PositiveIntegerField(default=0)  # 0 = immediate
    # Lesson unlocks X days after enrollment date
    
    def is_unlocked_for(self, enrollment: Enrollment) -> bool:
        unlock_at = enrollment.enrolled_at + timedelta(days=self.unlock_days)
        return now() >= unlock_at
```

#### Live Session Integration
- Replace any Zoom Tutor LMS meetings with **Jitsi Meet** (self-hosted, free, Arabic-friendly) or **Daily.co**
- Embed live session countdown in student dashboard
- Auto-record and publish to course after session ends

#### Certificate Generation
```python
# Use WeasyPrint or ReportLab to generate PDF certificates
class Certificate(models.Model):
    student     = models.ForeignKey(User, on_delete=models.CASCADE)
    course      = models.ForeignKey(Course, on_delete=models.CASCADE)
    issued_at   = models.DateTimeField(auto_now_add=True)
    verify_code = models.UUIDField(default=uuid.uuid4, unique=True)
    pdf_path    = models.FileField(upload_to='certificates/')
    # Public verify URL: elkaed.online/verify/{verify_code}
```

---

### 6.3 Commerce Enhancements

#### Installment Payment Plans
- Allow Kanga Pay to process in installments (if supported by gateway)
- Or: internal installment tracking — student pays partial upfront, access unlocked after each payment

#### Bundle Deals
```python
class CourseBundle(models.Model):
    title        = models.CharField(max_length=200)
    courses      = models.ManyToManyField(Course)
    bundle_price = models.DecimalField(max_digits=10, decimal_places=2)
    savings_amount = models.DecimalField(max_digits=10, decimal_places=2)
    is_active    = models.BooleanField(default=True)
```

#### Flash Sales (Time-Limited Pricing)
```python
class FlashSale(models.Model):
    course       = models.ForeignKey(Course, on_delete=models.CASCADE)
    sale_price   = models.DecimalField(max_digits=10, decimal_places=2)
    starts_at    = models.DateTimeField()
    ends_at      = models.DateTimeField()
    
    @property
    def is_active(self):
        return self.starts_at <= now() <= self.ends_at
```

#### Wallet Auto-Recharge Notifications
- WhatsApp alert when wallet balance drops below configurable threshold (e.g., 50 EGP)
- "رصيدك أقل من ٥٠ جنيه — اشحن الآن"

---

### 6.4 Communication Enhancements

#### WhatsApp Notification Templates
Move away from hardcoded PHP strings to a **template management system**:

```python
class NotificationTemplate(models.Model):
    TRIGGERS = [
        ('quiz_result', 'نتيجة الاختبار'),
        ('enrollment_confirmed', 'تأكيد التسجيل'),
        ('low_wallet', 'رصيد منخفض'),
        ('payment_success', 'نجاح الدفع'),
        ('new_lesson', 'درس جديد'),
        ('otp', 'رمز التحقق'),
    ]
    trigger  = models.CharField(choices=TRIGGERS, max_length=30, unique=True)
    body_ar  = models.TextField()  # Arabic template with {variables}
    body_en  = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
```

#### Multi-Channel Notifications
- Add **web push notifications** (via FCM + `django-push-notifications`) alongside WhatsApp
- In-app notification bell component in React header
- Student can choose preference: WhatsApp only / Push only / Both

#### Automated Parent Updates
- Weekly WhatsApp summary to guardian phone: courses enrolled, quizzes taken, scores earned
- Admin can configure frequency and template in Arabic admin panel

---

### 6.5 Analytics & Reporting

#### Student Analytics Dashboard
- Per-student: quiz score trends over time (line chart)
- Time spent per lesson (tracked via heartbeat API every 30 seconds)
- Weak subjects identification: courses with lowest avg quiz scores

#### Instructor Analytics
- Enrollment count per course per week
- Quiz pass/fail rates
- Most-watched vs least-watched lessons (video completion rates)

#### Admin Analytics
- Revenue by day/week/month (EGP)
- Top-selling courses
- Student retention: enrollment to first lesson completion rate
- Wallet usage vs Kanga Pay usage split
- Geographic distribution (governorate-level if phone data permits)

```python
# Celery Beat: nightly analytics aggregation
@shared_task
def aggregate_daily_analytics():
    today = date.today() - timedelta(days=1)
    DailyAnalytics.objects.update_or_create(
        date=today,
        defaults={
            'new_users': User.objects.filter(date_joined__date=today).count(),
            'new_enrollments': Enrollment.objects.filter(enrolled_at__date=today).count(),
            'revenue': Order.objects.filter(
                created_at__date=today, status='completed'
            ).aggregate(Sum('total_price'))['total_price__sum'] or 0,
            'quiz_attempts': QuizAttempt.objects.filter(started_at__date=today).count(),
        }
    )
```

---

### 6.6 Performance & Infrastructure Enhancements

#### Caching Strategy
```python
# Redis caching for high-read endpoints
from django.core.cache import cache

class CourseListView(ListAPIView):
    def get_queryset(self):
        cache_key = f"courses:{self.request.user.student_type}:{self.request.user.academic_year}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        qs = Course.objects.filter(...).select_related('instructor', 'category')
        cache.set(cache_key, qs, timeout=300)  # 5 minutes
        return qs
```

#### CDN for Static & Media
- All `wp-content/uploads/` images → **Cloudflare R2** with Cloudflare CDN in front
- Set long `Cache-Control` headers for images (immutable after upload)
- WebP conversion on upload using `Pillow` for 40-60% size reduction

#### Database Optimization
```sql
-- Add indexes for the most common queries
CREATE INDEX idx_enrollment_student_status ON enrollment(student_id, status);
CREATE INDEX idx_lesson_progress_student ON lessonprogress(student_id, completed);
CREATE INDEX idx_quiz_attempt_student_quiz ON quizattempt(student_id, quiz_id, status);
CREATE INDEX idx_course_category ON course(category_id, is_published);
```

#### Async Everything with Celery
| Task | Trigger | Worker |
|---|---|---|
| Send WhatsApp notification | Signal: quiz submitted, payment complete | Celery + Redis |
| Transcode uploaded video | Signal: video uploaded | Celery + FFmpeg |
| Generate certificate PDF | Signal: course completed | Celery + WeasyPrint |
| Aggregate analytics | Celery Beat: nightly 2AM | Celery |
| Send weekly parent report | Celery Beat: Sunday 10AM | Celery |
| Expire OTP codes | Celery Beat: every 10 min | Celery |

---

### 6.7 Mobile Application (Future Phase)

After the web platform is stable, a **React Native** mobile app (sharing API with Django) should be built:
- Expo-based for rapid cross-platform development
- Offline lesson download (cached HLS segments on device) for poor network areas (common in Egyptian governorates)
- Push notifications via Firebase
- Biometric login (Face ID / fingerprint)
- Arabic-first with the same i18next translation files as web

---

### 6.8 Content Management Enhancements

#### Admin Banner Management
```python
class HomepageBanner(models.Model):
    image      = models.ImageField(upload_to='banners/')
    title_ar   = models.CharField(max_length=200)
    title_en   = models.CharField(max_length=200, blank=True)
    link_url   = models.URLField(blank=True)
    is_active  = models.BooleanField(default=True)
    order      = models.PositiveIntegerField(default=0)
    starts_at  = models.DateTimeField(null=True)
    ends_at    = models.DateTimeField(null=True)
```

#### Course Announcement System
- Instructors post announcements to enrolled students
- Students receive WhatsApp notification for new announcements
- Displayed in course page and student dashboard

#### FAQ Management
- Per-course FAQ section (accordion)
- Global platform FAQ (Arabic + English)
- Admin can add/edit via Arabic admin panel

---

## 7. CREDENTIAL REGISTRY

> ⚠️ **SECURITY NOTE:** All credentials below are from the WordPress system and must be **ROTATED immediately after migration.** Do not use these in production Django.

| Credential | Value | Status |
|---|---|---|
| DB Password | `ba649a5b71c3e8a7` | RETIRE after migration |
| DB Host | `wordpressdb-u.hosting.stackcp.net` | WP only |
| wa-ma.org API Key | `3f0c0a9601bcba52ac812a5028f539ebd95e8efc47338d5ab2484959a0b8a25b` | ROTATE |
| Tutor REST API Key | `key_432a3a2ba4798d7b38d83647bc6bef8f` | RETIRE (WP only) |
| Tutor REST API Secret | `secret_b76ceeabe6bcf555b0b3cecbef2f79a3185898771e0371da12e42eb4feebb107` | RETIRE |
| Kanga Pay Public Key | Stored in WP options table (`woocommerce_kanga_pay_settings`) | TRANSFER to Django env |
| Kanga Pay Secret Key | Same — retrieve from DB before shutting down WP | TRANSFER to Django env |
| Kanga Pay Webhook URL | `/wp-json/kanga-pay/v1/webhook` | CHANGE to Django URL |

**New Django `.env` template:**
```env
SECRET_KEY=<generate-new>
DATABASE_URL=postgres://user:pass@host:5432/elkaed
REDIS_URL=redis://localhost:6379/0
KANGA_PAY_PUBLIC_KEY=<from-wp-options>
KANGA_PAY_SECRET_KEY=<from-wp-options>
KANGA_PAY_WEBHOOK_SECRET=<from-kanga-dashboard>
WAMA_API_KEY=<new-key-from-wa-ma.org>
AWS_ACCESS_KEY_ID=<s3-or-r2-key>
AWS_SECRET_ACCESS_KEY=<s3-or-r2-secret>
AWS_STORAGE_BUCKET_NAME=elkaed-videos
CLOUDFRONT_DOMAIN=<cdn-domain>
CLOUDFRONT_KEY_PAIR_ID=<cf-key-id>
CELERY_BROKER_URL=redis://localhost:6379/1
```

---

## 8. PROJECT CONSTRAINTS & RISKS

| Risk | Severity | Mitigation |
|---|---|---|
| **Fake emails break any email auth path** | CRITICAL | Phone-only auth. Never implement email login |
| **phpass hashes need bridge hasher** | HIGH | Implement `PhpassPasswordHasher` before ETL |
| **246K quiz answers — ETL timeout** | HIGH | Chunked `bulk_create`, run ETL on production server not dev machine |
| **WordPress stays live during migration** | HIGH | Run ETL → freeze WP → run delta ETL → cutover DNS |
| **Guardian phone in billing_company** | MEDIUM | Extract in Pass 1 — map to `User.guardian_phone` |
| **Elementor page data (not migratable)** | MEDIUM | Rebuild all pages in React. Do NOT try to parse Elementor JSON |
| **YouTube videos (no local copy)** | MEDIUM | Instructors must re-upload to self-hosted after launch. Provide YouTube embed as fallback during transition |
| **Mailchimp tables (abandoned)** | LOW | Skip entirely in ETL |
| **OpenEndend quiz questions need human review** | MEDIUM | Flag `is_reviewed=False`. Build instructor review queue in dashboard |
| **AES key storage security** | HIGH | Store AES keys encrypted in DB using Django `encrypted-fields` library. Never put in CDN |
| **wa-ma.org rate limits** | MEDIUM | Queue WhatsApp sends via Celery. Add retry logic with exponential backoff |

---

## APPENDIX: RECOMMENDED TECH STACK

### Backend
| Layer | Technology |
|---|---|
| Framework | Django 5.x + Django REST Framework |
| Database | PostgreSQL 16 |
| Cache / Queue Broker | Redis 7 |
| Task Queue | Celery 5 |
| Authentication | `djangorestframework-simplejwt` |
| Video Transcoding | FFmpeg via subprocess or `ffmpeg-python` |
| PDF Generation | WeasyPrint (certificates) |
| Phone Numbers | `phonenumbers` library |
| Password Migration | `passlib[phpass]` |
| PHP Unserialize | `phpserialize` (ETL only) |
| Storage | Cloudflare R2 (S3-compatible, cheaper egress) |
| CDN | Cloudflare (free tier) |
| Email | Brevo (formerly Sendinblue) — Arabic transactional email |

### Frontend
| Layer | Technology |
|---|---|
| Framework | React 18 + Vite |
| Routing | React Router v6 |
| Server State | TanStack Query v5 |
| Client State | Zustand |
| Styling | Tailwind CSS v3 + `tailwindcss-rtl` |
| Video Player | hls.js |
| i18n | i18next + react-i18next |
| Forms | React Hook Form + Zod |
| Charts (admin) | Recharts |
| HTTP | Axios |
| Arabic Fonts | Cairo, Tajawal (Google Fonts) |

### Infrastructure
| Layer | Technology |
|---|---|
| Server | Ubuntu 22.04 LTS |
| Web Server | Nginx (reverse proxy) |
| App Server | Gunicorn (Django) |
| Process Manager | Supervisor |
| SSL | Let's Encrypt via Certbot |
| Monitoring | Sentry (errors) + UptimeRobot (uptime) |
| CI/CD | GitHub Actions |
| Backups | Daily pg_dump to R2 |

---

*Document maintained in `E:\Elkaed\MIGRATION_BLUEPRINT.md` — reference this in every development session.*  
*Last updated: 2026-07-14*
