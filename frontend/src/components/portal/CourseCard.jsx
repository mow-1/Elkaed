import styles from '../../pages/PortalPage.module.css'

// Shared presentational card used by FeedTab (browse) and StoreTab (buy) — same
// grid markup, only the action slot differs, so it isn't duplicated per tab.
export default function CourseCard({ course, action }) {
  return (
    <div className={styles.courseCard}>
      <div className={styles.courseThumb}>
        {course.thumbnail
          ? <img src={course.thumbnail} alt={course.title} />
          : <div className={styles.thumbPlaceholder}><span>𓂀</span></div>
        }
      </div>
      <div className={styles.courseCardBody}>
        <p className={styles.courseCardTitle}>{course.title}</p>
        <p className={styles.courseCardMeta}>{course.category_name} — {course.instructor_name}</p>
        <p className={styles.coursePrice}>{course.price} ج.م</p>
        {action}
      </div>
    </div>
  )
}
