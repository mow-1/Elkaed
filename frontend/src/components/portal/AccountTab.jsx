import { useEffect, useRef, useState } from 'react'
import { changePassword, getMyQrCode, getMyIdCardPdf } from '../../api/auth'
import { getWallet, topUpWallet, getOrders } from '../../api/commerce'
import { getWalletHistory } from '../../api/portal'
import { getNotifPrefs, updateNotifPrefs } from '../../api/notifications'
import { useAuth } from '../../context/AuthContext'
import { blank, load } from './shared'
import ProfileForm from '../ProfileForm'
import styles from '../../pages/PortalPage.module.css'

const ROLE_AR = { student: 'طالب', instructor: 'مدرس', admin: 'مدير' }
const YEAR_AR = { '1st': 'الأول الثانوي', '2nd': 'الثاني الثانوي', '3rd': 'الثالث الثانوي' }
const TYPE_AR = { center: 'سنتر', online: 'أونلاين' }
const ORDER_STATUS_AR = {
  completed: { background: '#D1FAE5', color: '#065F46', label: 'مكتمل' },
  pending:   { background: 'var(--cream-soft)', color: 'var(--gold-mid)', label: 'معلق' },
  cancelled: { background: '#FEE2E2', color: '#991B1B', label: 'ملغي' },
}
const NOTIF_LABELS = {
  quiz_result:          'نتائج الاختبارات',
  enrollment_confirmed: 'تأكيد التسجيل',
  order_status:         'تغيير حالة الطلب',
  campaign:             'الرسائل التسويقية',
}

function pageFromUrl(url) {
  if (!url) return null
  try { return new URL(url).searchParams.get('page') } catch { return null }
}

function ProfileInfoBox() {
  const { user } = useAuth()
  const fields = [
    { label: 'رقم الهاتف',   value: user.phone ?? '—' },
    { label: 'نوع الحساب',   value: ROLE_AR[user.role] ?? user.role ?? '—' },
    { label: 'الصف الدراسي', value: YEAR_AR[user.academic_year] ?? user.academic_year ?? '—' },
    { label: 'طريقة التعلم', value: TYPE_AR[user.student_type] ?? user.student_type ?? '—' },
    { label: 'رصيد المحفظة', value: `${user.wallet_balance ?? '0.00'} ج.م` },
  ]
  return (
    <div className={styles.profileBox}>
      {fields.map(f => (
        <div key={f.label} className={styles.profileField}>
          <p className={styles.fieldLabel}>{f.label}</p>
          <p className={styles.fieldValue}>{f.value}</p>
        </div>
      ))}
    </div>
  )
}

function OrdersBox() {
  const [state, setState] = useState(blank())
  useEffect(() => { load(getOrders, setState) }, [])

  const list = Array.isArray(state.data) ? state.data : (state.data?.results ?? [])

  return (
    <div className={styles.formBox}>
      <h3 className={styles.sectionHeading}>طلباتي</h3>
      {state.loading && <p className={styles.loading}>جارٍ التحميل...</p>}
      {state.error && (
        <div className={styles.errorRow}>
          <span>حدث خطأ في تحميل البيانات</span>
          <button className={styles.retryBtn} onClick={() => load(getOrders, setState)}>إعادة المحاولة</button>
        </div>
      )}
      {!state.loading && !state.error && !list.length && <p className={styles.empty}>لا توجد طلبات بعد.</p>}
      {!state.loading && !state.error && list.map((order, i) => {
        const chip = ORDER_STATUS_AR[order.status] ?? ORDER_STATUS_AR.pending
        const date = order.created_at ? new Date(order.created_at).toLocaleDateString('ar-EG') : ''
        return (
          <div key={order.id ?? i} className={styles.orderCard}>
            <div className={styles.orderMeta}>
              <div className={styles.orderHeaderInfo}>
                <span className={styles.orderId}>طلب #{order.id}</span>
                {date && <span className={styles.orderDate}>{date}</span>}
              </div>
              <span className={styles.badgeGreen} style={{ background: chip.background, color: chip.color }}>
                {chip.label}
              </span>
            </div>
            {order.total != null && <p className={styles.orderTotal}>الإجمالي: {order.total} ج.م</p>}
            {order.items?.length > 0 && (
              <ul className={styles.orderItems}>
                {order.items.map((item, j) => <li key={j}>{item.title} — {item.price} ج.م</li>)}
              </ul>
            )}
          </div>
        )
      })}
    </div>
  )
}

function NotifPrefsBox() {
  const [state, setState] = useState(blank())
  useEffect(() => { load(getNotifPrefs, setState) }, [])

  async function handleToggle(key) {
    const current = state.data?.[key] ?? false
    setState(s => ({ ...s, data: { ...s.data, [key]: !current } }))
    try {
      const r = await updateNotifPrefs({ notif_type: key, enabled: !current })
      if (!r.ok) throw new Error()
    } catch {
      setState(s => ({ ...s, data: { ...s.data, [key]: current } }))
    }
  }

  return (
    <div className={styles.formBox}>
      <h3 className={styles.sectionHeading}>تفضيلات الإشعارات</h3>
      {state.loading && <p className={styles.loading}>جارٍ التحميل...</p>}
      {state.error && (
        <div className={styles.errorRow}>
          <span>حدث خطأ في تحميل البيانات</span>
          <button className={styles.retryBtn} onClick={() => load(getNotifPrefs, setState)}>إعادة المحاولة</button>
        </div>
      )}
      {!state.loading && !state.error && Object.entries(NOTIF_LABELS).map(([key, label]) => (
        <div key={key} className={styles.prefRow}>
          <span className={styles.prefLabel}>{label}</span>
          <label className={styles.toggleWrap}>
            <input
              type="checkbox"
              className={styles.toggleInput}
              checked={state.data?.[key] ?? false}
              onChange={() => handleToggle(key)}
            />
            <span className={styles.slider} />
          </label>
        </div>
      ))}
    </div>
  )
}

function ChangePasswordForm({ forced }) {
  const { reload } = useAuth()
  const [newPw, setNewPw] = useState('')
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState('')

  async function handleSubmit(e) {
    e.preventDefault()
    setSaving(true)
    setMsg('')
    try {
      const r = await changePassword(newPw)
      const body = await r.json().catch(() => ({}))
      if (!r.ok) { setMsg(body.detail || 'حدث خطأ'); return }
      setMsg(body.detail || 'تم تغيير كلمة المرور بنجاح')
      setNewPw('')
      reload()
    } finally {
      setSaving(false)
    }
  }

  return (
    <form className={`${styles.formBox} ${forced ? styles.formBoxForced : ''}`} onSubmit={handleSubmit}>
      <h3 className={styles.sectionHeading}>
        {forced ? 'يجب تغيير كلمة المرور' : 'تغيير كلمة المرور'}
      </h3>
      {forced && <p className={styles.forcedNote}>حسابك يستخدم كلمة مرور مؤقتة — يرجى تعيين كلمة مرور جديدة للمتابعة.</p>}
      <label className={styles.formLabel}>كلمة المرور الجديدة
        <input
          className={styles.input}
          type="password"
          dir="ltr"
          value={newPw}
          minLength={8}
          onChange={e => setNewPw(e.target.value)}
        />
      </label>
      <button className={styles.openBtn} disabled={saving || newPw.length < 8} type="submit">
        {saving ? 'جارٍ الحفظ...' : 'تغيير كلمة المرور'}
      </button>
      {msg && <p className={styles.formMsg}>{msg}</p>}
    </form>
  )
}

function RechargeForm() {
  const [amount, setAmount] = useState('')
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState('')

  async function handleSubmit(e) {
    e.preventDefault()
    setBusy(true)
    setMsg('')
    try {
      const r = await topUpWallet(amount)
      const body = await r.json().catch(() => ({}))
      if (!r.ok || !body.payment_url) { setMsg(body.detail || 'حدث خطأ'); return }
      window.location.href = body.payment_url
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className={styles.rechargeRow} onSubmit={handleSubmit}>
      <input
        className={styles.input}
        type="number" min="1" step="0.01" required dir="ltr"
        placeholder="المبلغ بالجنيه"
        value={amount}
        onChange={e => setAmount(e.target.value)}
      />
      <button className={styles.openBtn} disabled={busy || !amount} type="submit">
        {busy ? 'جارٍ التحويل...' : 'شحن المحفظة'}
      </button>
      {msg && <p className={styles.formMsg}>{msg}</p>}
    </form>
  )
}

function WalletHistoryTable() {
  const [wallet, setWallet] = useState(blank())
  const [history, setHistory] = useState(null)
  const [page, setPage] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => { load(getWallet, setWallet) }, [])

  useEffect(() => {
    setLoading(true)
    getWalletHistory(page ? { page } : {})
      .then(r => r.ok ? r.json() : null)
      .then(d => { if (d) setHistory(d) })
      .finally(() => setLoading(false))
  }, [page])

  return (
    <div className={styles.formBox}>
      <h3 className={styles.sectionHeading}>محفظتي</h3>
      <p className={styles.walletBalanceInline}>
        الرصيد الحالي: {wallet.loading ? '...' : `${wallet.data?.balance ?? '0.00'} ج.م`}
      </p>
      <RechargeForm />

      {loading ? <p className={styles.loading}>جارٍ التحميل...</p> : history && (
        <>
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th className={styles.th}>التاريخ</th>
                  <th className={styles.th}>البيان</th>
                  <th className={styles.th}>المبلغ</th>
                  <th className={styles.th}>الرصيد بعدها</th>
                </tr>
              </thead>
              <tbody>
                {history.results.map(t => (
                  <tr key={t.id}>
                    <td className={styles.td}>{new Date(t.created_at).toLocaleString('ar-EG')}</td>
                    <td className={styles.td}>{t.note}</td>
                    <td className={styles.td}>
                      <span className={t.type === 'credit' ? styles.badgeGreen : styles.badgeRed}>
                        {t.type === 'credit' ? '+' : '-'}{t.amount} ج.م
                      </span>
                    </td>
                    <td className={styles.td}>{t.balance_after} ج.م</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {history.results.length === 0 && <p className={styles.empty}>لا توجد حركات بعد.</p>}
          </div>
          <div className={styles.pagination}>
            <button className={styles.pageBtn} disabled={!history.previous} onClick={() => setPage(pageFromUrl(history.previous) ?? null)}>السابق</button>
            <button className={styles.pageBtn} disabled={!history.next} onClick={() => setPage(pageFromUrl(history.next))}>التالي</button>
          </div>
        </>
      )}
    </div>
  )
}

function QrAndIdCard() {
  const [qrUrl, setQrUrl] = useState(null)
  const [fullscreen, setFullscreen] = useState(false)
  const objectUrlRef = useRef(null)

  useEffect(() => {
    let alive = true
    getMyQrCode()
      .then(r => r.ok ? r.blob() : null)
      .then(blob => {
        if (!blob || !alive) return
        const url = URL.createObjectURL(blob)
        objectUrlRef.current = url
        setQrUrl(url)
      })
    return () => {
      alive = false
      if (objectUrlRef.current) URL.revokeObjectURL(objectUrlRef.current)
    }
  }, [])

  async function handleDownloadIdCard() {
    const r = await getMyIdCardPdf()
    if (!r.ok) return
    const blob = await r.blob()
    const url = URL.createObjectURL(blob)
    window.open(url, '_blank')
    setTimeout(() => URL.revokeObjectURL(url), 30000)
  }

  return (
    <div className={styles.formBox}>
      <h3 className={styles.sectionHeading}>بطاقتي</h3>
      {qrUrl && (
        <img
          src={qrUrl}
          alt="رمز الحضور"
          className={styles.qrImage}
          onClick={() => setFullscreen(true)}
        />
      )}
      <button className={styles.openBtn} onClick={handleDownloadIdCard}>تحميل بطاقة الهوية</button>

      {fullscreen && qrUrl && (
        <div className={styles.modalOverlay} onClick={() => setFullscreen(false)}>
          <img src={qrUrl} alt="رمز الحضور" className={styles.qrImageFull} />
        </div>
      )}
    </div>
  )
}

export default function AccountTab() {
  const { user } = useAuth()

  return (
    <div className={styles.accountGrid}>
      {user?.must_change_password && <ChangePasswordForm forced />}

      <h2 className={styles.groupHeading}>الملف الشخصي</h2>
      <ProfileInfoBox />
      <ProfileForm />

      {!user?.must_change_password && (
        <>
          <h2 className={styles.groupHeading}>الأمان</h2>
          <ChangePasswordForm forced={false} />
        </>
      )}

      <h2 className={styles.groupHeading}>المحفظة والطلبات</h2>
      <WalletHistoryTable />
      <OrdersBox />

      <h2 className={styles.groupHeading}>الإعدادات وبطاقتي</h2>
      <NotifPrefsBox />
      <QrAndIdCard />
    </div>
  )
}
