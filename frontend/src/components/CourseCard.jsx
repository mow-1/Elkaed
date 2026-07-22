import { Link } from 'react-router-dom'
import styles from './Courses.module.css'

// Public marketing-style course card — shared by the landing page's teaser
// section and the full /courses catalog page. Not the same component as
// components/portal/CourseCard.jsx, which is a different, authenticated-portal
// card (buy/browse actions, portal styling) used by Feed/Store tabs.
export function SkeletonCard() {
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

export default function CourseCard({ course: c }) {
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
          <span className={styles.teacherName}>{c.instructorName ?? '—'}</span>
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
