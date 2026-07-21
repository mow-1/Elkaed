import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { COURSES, GRADES } from '../data/courses'
import { getCourses } from '../api/courses'
import styles from './Courses.module.css'

function mapApiCourse(c) {
  return {
    id: c.id,
    slug: c.slug,
    title: c.title,
    grade: c.category_name ?? '—',
    price: `${c.price} جنيه`,
    students: 0,
    lessons: '—',
    img: c.thumbnail ?? null,
  }
}

function SkeletonCard() {
  return (
    <div className={`${styles.card} ${styles.skeleton}`}>
      <div className={styles.skelImg} />
      <div className={styles.skelBody}>
        <div className={styles.skelLine} style={{ width: '60%', height: 14 }} />
        <div className={styles.skelLine} style={{ width: '90%', height: 18, marginTop: 8 }} />
        <div className={styles.skelLine} style={{ width: '40%', height: 12, marginTop: 8 }} />
      </div>
    </div>
  )
}

export default function Courses() {
  const [activeGrade, setActiveGrade] = useState('الكل')
  const [courses, setCourses] = useState(COURSES)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getCourses()
      .then(res => res.ok ? res.json() : Promise.reject())
      .then(data => { if (data.results?.length) setCourses(data.results.map(mapApiCourse)) })
      .catch(() => { /* static fallback already in state */ })
      .finally(() => setLoading(false))
  }, [])

  const filtered = activeGrade === 'الكل'
    ? courses
    : courses.filter(c => c.grade === activeGrade)

  return (
    <section id="courses" className={styles.section}>
      <div className={styles.container}>
        <div className={styles.header}>
          <p className={styles.eyebrow}>اتعلّم بالأسلوب اللي يناسبك</p>
          <h2 className={styles.title}>أشهر كورسات القائد</h2>
          <p className={styles.subtitle}>
            تصفّح الكورسات واختار اللي يناسب صفّك وهدفك. ابدأ المذاكرة معانا، وخلّي هدفك أقرب كل يوم!
          </p>
        </div>

        <div className={styles.pills}>
          {GRADES.map(grade => (
            <button
              key={grade}
              className={`${styles.pill} ${activeGrade === grade ? styles.pillActive : ''}`}
              onClick={() => setActiveGrade(grade)}
            >
              {grade === 'الكل' ? 'كل الصفوف' : 'الصف ' + grade}
            </button>
          ))}
        </div>

        <div className={styles.grid} key={activeGrade}>
          {loading
            ? [0, 1, 2].map(i => <SkeletonCard key={i} />)
            : filtered.map(c => <CourseCard key={c.id} course={c} />)
          }
        </div>

        <div className={styles.bottomLink}>
          <a href="#register" className={styles.link}>سجّل دلوقتي وابدأ أول حصة ←</a>
        </div>
      </div>
    </section>
  )
}

function CourseCard({ course: c }) {
  const inner = (
    <div className={styles.card}>
      <div className={styles.imageArea}>
        <div className={styles.imagePlaceholder}>
          <span className={styles.imagePlaceholderGlyph}>𓂀</span>
        </div>
        {c.img && (
          <img
            src={c.img}
            alt={c.title}
            className={styles.image}
            onError={e => { e.currentTarget.style.display = 'none' }}
          />
        )}
        <span className={styles.priceBadge}>{c.price}</span>
      </div>

      <div className={styles.cardBody}>
        <div className={styles.teacherRow}>
          <span className={styles.teacherAvatar}>𓂀</span>
          <span className={styles.teacherName}>مصطفى عرفة</span>
          <span className={styles.gradeChip}>الصف {c.grade}</span>
        </div>

        <h3 className={styles.courseTitle}>{c.title}</h3>

        <div className={styles.cardFooter}>
          <span>👥 {c.students} طالب</span>
          <span>{c.lessons} 📖</span>
        </div>
      </div>
    </div>
  )

  return c.slug
    ? <Link to={`/courses/${c.slug}`} style={{ display: 'contents' }}>{inner}</Link>
    : inner
}
