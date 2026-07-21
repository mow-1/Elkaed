import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useCart } from '../context/CartContext'
import { checkout } from '../api/commerce'
import styles from './PortalPage.module.css'

export default function CheckoutPage() {
  const { user, loading: authLoading, reload } = useAuth()
  const { items, removeItem, clear } = useCart()
  const navigate = useNavigate()
  const [state, setState] = useState({ status: 'idle', detail: '' }) // idle | loading | done | error
  const [result, setResult] = useState(null)

  if (!authLoading && !user) {
    navigate('/login', { replace: true })
    return null
  }

  const total = items.reduce((sum, i) => sum + Number(i.price ?? 0), 0)

  async function handleCheckout() {
    setState({ status: 'loading', detail: '' })
    try {
      const res = await checkout(items.map(i => i.id))
      const body = await res.json().catch(() => ({}))

      if (res.status === 402) {
        if (body.payment_url) { window.location.href = body.payment_url; return }
        setState({ status: 'error', detail: 'رصيد المحفظة غير كافٍ.' })
        return
      }
      if (res.status === 201) {
        clear()
        await reload()
        setResult(body)
        setState({ status: 'done', detail: '' })
        return
      }
      setState({ status: 'error', detail: body.detail || 'حدث خطأ أثناء إتمام الشراء.' })
    } catch {
      setState({ status: 'error', detail: 'فشل الاتصال بالسيرفر.' })
    }
  }

  if (state.status === 'done' && result) {
    return (
      <div className={styles.page}>
        <h1 className={styles.heading}>تم الشراء بنجاح 🎉</h1>
        <div className={styles.card} style={{ flexDirection: 'column', alignItems: 'stretch' }}>
          <p>تم تسجيلك في:</p>
          <ul>
            {result.enrolled.map(title => <li key={title}>{title}</li>)}
          </ul>
          {result.already_enrolled?.length > 0 && (
            <p className={styles.errorRow}>كنت مشتركاً بالفعل في: {result.already_enrolled.join('، ')}</p>
          )}
          <Link to="/portal" className={styles.openBtn} style={{ display: 'inline-block', width: 'fit-content', marginTop: 12 }}>
            الذهاب لكورساتي
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className={styles.page}>
      <h1 className={styles.heading}>السلة والدفع</h1>

      {items.length === 0 ? (
        <p className={styles.empty}>
          سلتك فارغة — <Link to="/courses">تصفّح الكورسات</Link>
        </p>
      ) : (
        <>
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th className={styles.th}>الكورس</th>
                  <th className={styles.th}>السعر</th>
                  <th className={styles.th}></th>
                </tr>
              </thead>
              <tbody>
                {items.map(item => (
                  <tr key={item.id}>
                    <td className={styles.td}>{item.title}</td>
                    <td className={styles.td}>{item.price} ج.م</td>
                    <td className={styles.td}>
                      <button className={styles.retryBtn} onClick={() => removeItem(item.id)}>إزالة</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className={styles.card} style={{ marginTop: 20, justifyContent: 'space-between' }}>
            <div>
              <p>الإجمالي: <strong>{total.toFixed(2)} ج.م</strong></p>
              <p className={styles.courseStatus}>رصيد محفظتك: {user?.wallet_balance ?? '—'} ج.م</p>
            </div>
            <button
              className={styles.openBtn}
              disabled={state.status === 'loading'}
              onClick={handleCheckout}
            >
              {state.status === 'loading' ? 'جارٍ إتمام الشراء...' : 'إتمام الشراء'}
            </button>
          </div>

          {state.status === 'error' && <p className={styles.errorRow}>{state.detail}</p>}
        </>
      )}
    </div>
  )
}
