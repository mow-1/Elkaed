import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getCourses } from '../../api/courses'
import { blank, load } from './shared'
import CourseCard from './CourseCard'
import styles from '../../pages/PortalPage.module.css'

const fetchFeed = () => getCourses('ordering=-created_at')

export default function FeedTab() {
  const [state, setState] = useState(blank())

  useEffect(() => { load(fetchFeed, setState) }, [])

  if (state.loading) return <p className={styles.loading}>جارٍ التحميل...</p>
  if (state.error) return (
    <div className={styles.errorRow}>
      <span>حدث خطأ في تحميل البيانات</span>
      <button className={styles.retryBtn} onClick={() => load(fetchFeed, setState)}>إعادة المحاولة</button>
    </div>
  )

  const list = state.data?.results ?? []
  if (!list.length) return <p className={styles.empty}>لا توجد كورسات جديدة حالياً.</p>

  return (
    <div className={styles.courseGrid}>
      {list.map(c => (
        <CourseCard
          key={c.id}
          course={c}
          action={<Link to={`/courses/${c.slug}`} className={styles.openBtn}>التفاصيل</Link>}
        />
      ))}
    </div>
  )
}
