import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getCourses } from '../../api/courses'
import { blank, load } from './shared'
import { useCart } from '../../context/CartContext'
import CourseCard from './CourseCard'
import styles from '../../pages/PortalPage.module.css'

export default function StoreTab() {
  const [state, setState] = useState(blank())
  const { items, addItem, has } = useCart()

  useEffect(() => { load(getCourses, setState) }, [])

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
    <div>
      {items.length > 0 && (
        <p className={styles.courseStatus} style={{ marginBottom: 12 }}>
          {items.length} كورس في السلة — <Link to="/checkout">الذهاب للسلة والدفع</Link>
        </p>
      )}
      <div className={styles.courseGrid}>
        {list.map(c => {
          const inCart = has(c.id)
          return (
            <CourseCard
              key={c.id}
              course={c}
              action={
                <button
                  className={styles.openBtn}
                  disabled={inCart}
                  onClick={() => addItem({ id: c.id, title: c.title, price: c.price })}
                >
                  {inCart ? '✓ في السلة' : 'أضف للسلة'}
                </button>
              }
            />
          )
        })}
      </div>
    </div>
  )
}
