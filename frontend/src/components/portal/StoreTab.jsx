import { useEffect, useState } from 'react'
import { getCourses, enrollCourse } from '../../api/courses'
import { blank, load } from './shared'
import CourseCard from './CourseCard'
import styles from '../../pages/PortalPage.module.css'

export default function StoreTab() {
  const [state, setState] = useState(blank())
  const [buyState, setBuyState] = useState({}) // { [courseId]: 'loading'|'done'|'error message' }

  useEffect(() => { load(getCourses, setState) }, [])

  async function handleBuy(course) {
    setBuyState(s => ({ ...s, [course.id]: 'loading' }))
    try {
      const res = await enrollCourse(course.id)
      if (res.status === 402) {
        const body = await res.json().catch(() => ({}))
        if (body.payment_url) { window.location.href = body.payment_url; return }
        setBuyState(s => ({ ...s, [course.id]: 'رصيد المحفظة غير كافٍ' }))
        return
      }
      if (res.ok) { setBuyState(s => ({ ...s, [course.id]: 'done' })); return }
      const body = await res.json().catch(() => ({}))
      setBuyState(s => ({ ...s, [course.id]: body.detail || 'حدث خطأ' }))
    } catch {
      setBuyState(s => ({ ...s, [course.id]: 'حدث خطأ' }))
    }
  }

  if (state.loading) return <p className={styles.loading}>جارٍ التحميل...</p>
  if (state.error) return (
    <div className={styles.errorRow}>
      <span>حدث خطأ في تحميل البيانات</span>
      <button className={styles.retryBtn} onClick={() => load(getCourses, setState)}>إعادة المحاولة</button>
    </div>
  )

  const list = state.data?.results ?? []
  if (!list.length) return <p className={styles.empty}>لا توجد كورسات متاحة حالياً.</p>

  return (
    <div className={styles.courseGrid}>
      {list.map(c => {
        const b = buyState[c.id]
        return (
          <CourseCard
            key={c.id}
            course={c}
            action={
              <div>
                <button
                  className={styles.openBtn}
                  disabled={b === 'loading' || b === 'done'}
                  onClick={() => handleBuy(c)}
                >
                  {b === 'loading' ? 'جارٍ الشراء...' : b === 'done' ? '✓ تم الاشتراك' : 'شراء'}
                </button>
                {b && b !== 'loading' && b !== 'done' && (
                  <p className={styles.buyError}>{b}</p>
                )}
              </div>
            }
          />
        )
      })}
    </div>
  )
}
