import { useEffect, useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { getMyEnrollments } from '../api/courses'
import { getWallet, getOrders } from '../api/commerce'
import { getNotifPrefs, updateNotifPrefs } from '../api/notifications'
import ProfileForm from '../components/ProfileForm'
import styles from './DashboardPage.module.css'

// ── constants ──────────────────────────────────────────────────────────────
const STATUS_AR = { active: 'نشط', expired: 'منتهي', cancelled: 'ملغي' }
const ROLE_AR   = { student: 'طالب', instructor: 'مدرس', admin: 'مدير' }
const YEAR_AR   = { '1st': 'الأول الثانوي', '2nd': 'الثاني الثانوي', '3rd': 'الثالث الثانوي' }
const TYPE_AR   = { center: 'سنتر', online: 'أونلاين' }

const NOTIF_LABELS = {
  quiz_result:          'نتائج الاختبارات',
  enrollment_confirmed: 'تأكيد التسجيل',
  order_status:         'تغيير حالة الطلب',
  campaign:             'الرسائل التسويقية',
}

const TABS = [
  { key: 'enrollments', label: 'كورساتي' },
  { key: 'orders',      label: 'طلباتي' },
  { key: 'preferences', label: 'الإشعارات' },
  { key: 'profile',     label: 'بياناتي' },
]

const ORDER_CHIP = {
  completed: { background: '#D1FAE5',           color: '#065F46',         label: 'مكتمل' },
  pending:   { background: 'var(--cream-soft)',  color: 'var(--gold-mid)', label: 'معلق'  },
  cancelled: { background: '#FEE2E2',            color: '#991B1B',         label: 'ملغي'  },
}

// ── data-fetching helper ───────────────────────────────────────────────────
const blank = () => ({ data: null, loading: true, error: false })

async function load(apiFn, setter) {
  try {
    const r = await apiFn()
    if (!r.ok) throw new Error()
    setter({ data: await r.json(), loading: false, error: false })
  } catch {
    setter(s => ({ ...s, loading: false, error: true }))
  }
}

// ── shared micro-components ────────────────────────────────────────────────
function LoadingMsg() {
  return <p className={styles.loading}>جارٍ التحميل...</p>
}

function ErrorMsg({ onRetry }) {
  return (
    <div className={styles.errorRow}>
      <span>حدث خطأ في تحميل البيانات</span>
      <button className={styles.retryBtn} onClick={onRetry}>إعادة المحاولة</button>
    </div>
  )
}

// ── tab panels ─────────────────────────────────────────────────────────────
function EnrollmentsTab({ state, retry }) {
  if (state.loading) return <LoadingMsg />
  if (state.error)   return <ErrorMsg onRetry={retry} />

  const list = Array.isArray(state.data) ? state.data : (state.data?.results ?? [])
  if (!list.length) return (
    <p className={styles.empty}>
      لم تسجّل في أي كورس بعد —{' '}
      <Link to="/#courses" className={styles.link}>تصفّح الكورسات</Link>
    </p>
  )

  return (
    <div>
      {list.map((e, i) => (
        <div key={e.id ?? i} className={styles.card}>
          <div>
            <p className={styles.courseTitle}>{e.course?.title ?? e.title}</p>
            <p className={styles.courseStatus}>حالة: {STATUS_AR[e.status] ?? e.status}</p>
          </div>
          <Link to={`/courses/${e.course?.slug ?? ''}`} className={styles.openBtn}>
            فتح الكورس
          </Link>
        </div>
      ))}
    </div>
  )
}

function OrdersTab({ state, retry }) {
  if (state.loading) return <LoadingMsg />
  if (state.error)   return <ErrorMsg onRetry={retry} />

  const list = Array.isArray(state.data) ? state.data : (state.data?.results ?? [])
  if (!list.length) return <p className={styles.empty}>لا توجد طلبات بعد.</p>

  return (
    <div>
      {list.map((order, i) => {
        const chip = ORDER_CHIP[order.status] ?? ORDER_CHIP.pending
        const date = order.created_at
          ? new Date(order.created_at).toLocaleDateString('ar-EG')
          : ''
        return (
          <div key={order.id ?? i} className={styles.orderCard}>
            <div className={styles.orderMeta}>
              <div className={styles.orderHeaderInfo}>
                <span className={styles.orderId}>طلب #{order.id}</span>
                {date && <span className={styles.orderDate}>{date}</span>}
              </div>
              <span
                className={styles.statusChip}
                style={{ background: chip.background, color: chip.color }}
              >
                {chip.label}
              </span>
            </div>

            {order.total != null && (
              <p className={styles.orderTotal}>الإجمالي: {order.total} ج.م</p>
            )}

            {order.items?.length > 0 && (
              <ul className={styles.orderItems}>
                {order.items.map((item, j) => (
                  <li key={j}>{item.title} — {item.price} ج.م</li>
                ))}
              </ul>
            )}
          </div>
        )
      })}
    </div>
  )
}

function PrefsTab({ state, onToggle, retry }) {
  if (state.loading) return <LoadingMsg />
  if (state.error)   return <ErrorMsg onRetry={retry} />

  return (
    <div>
      {Object.entries(NOTIF_LABELS).map(([key, label]) => (
        <div key={key} className={styles.prefRow}>
          <span className={styles.prefLabel}>{label}</span>
          <label className={styles.toggleWrap}>
            <input
              type="checkbox"
              className={styles.toggleInput}
              checked={state.data?.[key] ?? false}
              onChange={() => onToggle(key)}
            />
            <span className={styles.slider} />
          </label>
        </div>
      ))}
    </div>
  )
}

function ProfileTab({ user, wallet }) {
  // Phone/role/year/type/wallet aren't user-editable (system/derived fields) —
  // shown read-only here. Name + guardian phone ARE editable, via the same
  // ProfileForm the /portal Account tab uses — previously this tab had no form
  // at all, so no student could actually change their info from here.
  const fields = [
    { label: 'رقم الهاتف',   value: user.phone ?? '—' },
    { label: 'نوع الحساب',   value: ROLE_AR[user.role] ?? user.role ?? '—' },
    { label: 'الصف الدراسي', value: YEAR_AR[user.academic_year] ?? user.academic_year ?? '—' },
    { label: 'طريقة التعلم', value: TYPE_AR[user.student_type] ?? user.student_type ?? '—' },
    {
      label: 'رصيد المحفظة',
      value: wallet.loading ? '...' : `${wallet.data?.balance ?? '0.00'} ج.م`,
    },
  ]

  return (
    <div>
      <div className={styles.profileBox}>
        {fields.map(f => (
          <div key={f.label} className={styles.profileField}>
            <p className={styles.fieldLabel}>{f.label}</p>
            <p className={styles.fieldValue}>{f.value}</p>
          </div>
        ))}
      </div>
      <ProfileForm />
    </div>
  )
}

// ── main page ──────────────────────────────────────────────────────────────
export default function DashboardPage() {
  const { user, loading, logout } = useAuth()
  const navigate = useNavigate()

  const [activeTab,   setActiveTab]   = useState('enrollments')
  const [wallet,      setWallet]      = useState(blank())
  const [enrollments, setEnrollments] = useState(blank())
  const [orders,      setOrders]      = useState(blank())
  const [prefs,       setPrefs]       = useState(blank())

  // auth guard
  useEffect(() => {
    if (!loading && !user) navigate('/login', { replace: true })
  }, [user, loading, navigate])

  // parallel fetch on mount once user is known
  useEffect(() => {
    if (!user) return
    load(getWallet,        setWallet)
    load(getMyEnrollments, setEnrollments)
    load(getOrders,        setOrders)
    load(getNotifPrefs,    setPrefs)
  }, [user])

  if (loading) {
    return (
      <div className={styles.spinnerWrap}>
        <div className={styles.spinner} />
      </div>
    )
  }
  if (!user) return null

  function handleLogout() {
    logout()
    navigate('/')
  }

  async function handleToggle(key) {
    const current = prefs.data?.[key] ?? false
    setPrefs(s => ({ ...s, data: { ...s.data, [key]: !current } }))
    try {
      const r = await updateNotifPrefs({ notif_type: key, enabled: !current })
      if (!r.ok) throw new Error()
    } catch {
      // revert on API failure
      setPrefs(s => ({ ...s, data: { ...s.data, [key]: current } }))
    }
  }

  return (
    <div className={styles.page}>
      {/* Header */}
      <div className={styles.header}>
        <h1 className={styles.greeting}>أهلاً، {user.first_name}!</h1>
        <button className={styles.logoutBtn} onClick={handleLogout}>تسجيل الخروج</button>
      </div>

      {/* Wallet card */}
      <div className={styles.walletCard}>
        <div className={styles.walletInfo}>
          <span className={styles.walletGlyph}>𓋹</span>
          <span className={styles.walletLabel}>رصيد المحفظة</span>
        </div>
        <div className={styles.walletBalance}>
          {wallet.loading ? '---' : `${wallet.data?.balance ?? '0.00'} ج.م`}
        </div>
      </div>

      {/* Tab bar */}
      <div className={styles.tabBar}>
        {TABS.map(t => (
          <button
            key={t.key}
            className={`${styles.tab} ${activeTab === t.key ? styles.tabActive : ''}`}
            onClick={() => setActiveTab(t.key)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {activeTab === 'enrollments' && (
        <EnrollmentsTab
          state={enrollments}
          retry={() => load(getMyEnrollments, setEnrollments)}
        />
      )}
      {activeTab === 'orders' && (
        <OrdersTab
          state={orders}
          retry={() => load(getOrders, setOrders)}
        />
      )}
      {activeTab === 'preferences' && (
        <PrefsTab
          state={prefs}
          onToggle={handleToggle}
          retry={() => load(getNotifPrefs, setPrefs)}
        />
      )}
      {activeTab === 'profile' && (
        <ProfileTab user={user} wallet={wallet} />
      )}
    </div>
  )
}
