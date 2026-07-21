import { useEffect, useState } from 'react'
import { getMyAttempts } from '../../api/portal'
import { blank, load } from './shared'
import styles from '../../pages/PortalPage.module.css'

export default function ResultsTab() {
  const [state, setState] = useState(blank())

  useEffect(() => { load(getMyAttempts, setState) }, [])

  if (state.loading) return <p className={styles.loading}>جارٍ التحميل...</p>
  if (state.error) return (
    <div className={styles.errorRow}>
      <span>حدث خطأ في تحميل البيانات</span>
      <button className={styles.retryBtn} onClick={() => load(getMyAttempts, setState)}>إعادة المحاولة</button>
    </div>
  )

  const list = Array.isArray(state.data) ? state.data : []
  if (!list.length) return <p className={styles.empty}>لا توجد نتائج اختبارات بعد.</p>

  return (
    <div className={styles.tableWrap}>
      <table className={styles.table}>
        <thead>
          <tr>
            <th className={styles.th}>الاختبار</th>
            <th className={styles.th}>الكورس</th>
            <th className={styles.th}>الدرجة</th>
            <th className={styles.th}>النتيجة</th>
            <th className={styles.th}>التاريخ</th>
          </tr>
        </thead>
        <tbody>
          {list.map(a => (
            <tr key={a.id}>
              <td className={styles.td}>{a.quiz_title}</td>
              <td className={styles.td}>{a.course_title}</td>
              <td className={styles.td}>{a.earned_marks} / {a.total_marks}</td>
              <td className={styles.td}>
                <span className={a.result === 'pass' ? styles.badgeGreen : styles.badgeRed}>
                  {a.result === 'pass' ? 'ناجح' : 'راسب'}
                </span>
              </td>
              <td className={styles.td}>
                {a.ended_at ? new Date(a.ended_at).toLocaleDateString('ar-EG') : '—'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
