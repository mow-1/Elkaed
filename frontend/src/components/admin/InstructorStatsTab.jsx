import { useEffect, useState } from 'react'
import { getInstructorStats } from '../../api/courseBuilder'
import styles from '../../pages/AdminPanelPage.module.css'

export default function InstructorStatsTab() {
  const [courses, setCourses] = useState(null)

  useEffect(() => {
    getInstructorStats()
      .then(r => r.ok ? r.json() : [])
      .then(d => setCourses(Array.isArray(d) ? d : (d?.results ?? [])))
  }, [])

  if (!courses) return <p className={styles.muted}>جاري التحميل...</p>
  if (!courses.length) return <p className={styles.muted}>لا توجد كورسات بعد.</p>

  return (
    <div className={styles.tableWrap}>
      <table className={styles.table}>
        <thead>
          <tr>
            <th className={styles.th}>الكورس</th>
            <th className={styles.th}>الفئة</th>
            <th className={styles.th}>السعر</th>
            <th className={styles.th}>عدد المشتركين</th>
            <th className={styles.th}>الحالة</th>
          </tr>
        </thead>
        <tbody>
          {courses.map(c => (
            <tr key={c.id} className={styles.tr}>
              <td className={styles.td}>{c.title}</td>
              <td className={styles.td}>{c.category_name ?? '—'}</td>
              <td className={styles.td}>{c.price} جنيه</td>
              <td className={styles.td}>{c.enrollment_count}</td>
              <td className={styles.td}>{c.is_published ? 'منشور' : 'مسودة'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
