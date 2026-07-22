import { useEffect, useRef, useState } from 'react'
import { getProfile, updateProfile, changePassword, getMyQrCode, getMyIdCardPdf } from '../../api/auth'
import { getWallet, topUpWallet } from '../../api/commerce'
import { getWalletHistory } from '../../api/portal'
import { useAuth } from '../../context/AuthContext'
import { blank, load } from './shared'
import styles from '../../pages/PortalPage.module.css'

function pageFromUrl(url) {
  if (!url) return null
  try { return new URL(url).searchParams.get('page') } catch { return null }
}

function ProfileForm() {
  const { reload } = useAuth()
  const [profile, setProfile] = useState(blank())
  const [form, setForm] = useState({ first_name: '', last_name: '', guardian_phone: '' })
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState('')

  useEffect(() => {
    getProfile()
      .then(r => r.ok ? r.json() : null)
      .then(d => {
        if (!d) { setProfile({ data: null, loading: false, error: true }); return }
        setProfile({ data: d, loading: false, error: false })
        setForm({ first_name: d.first_name ?? '', last_name: d.last_name ?? '', guardian_phone: d.guardian_phone ?? '' })
      })
      .catch(() => setProfile({ data: null, loading: false, error: true }))
  }, [])

  async function handleSubmit(e) {
    e.preventDefault()
    setSaving(true)
    setMsg('')
    try {
      const r = await updateProfile(form)
      if (!r.ok) throw new Error()
      setMsg('تم حفظ البيانات بنجاح')
      reload()
    } catch {
      setMsg('حدث خطأ أثناء الحفظ')
    } finally {
      setSaving(false)
    }
  }

  if (profile.loading) return <p className={styles.loading}>جارٍ التحميل...</p>
  if (profile.error) return <p className={styles.errorRow}>تعذّر تحميل بياناتك</p>

  return (
    <form className={styles.formBox} onSubmit={handleSubmit}>
      <h3 className={styles.sectionHeading}>بياناتي</h3>
      <label className={styles.formLabel}>الاسم الأول
        <input className={styles.input} value={form.first_name}
          onChange={e => setForm(f => ({ ...f, first_name: e.target.value }))} />
      </label>
      <label className={styles.formLabel}>الاسم الأخير
        <input className={styles.input} value={form.last_name}
          onChange={e => setForm(f => ({ ...f, last_name: e.target.value }))} />
      </label>
      <label className={styles.formLabel}>رقم هاتف ولي الأمر
        <input className={styles.input} dir="ltr" value={form.guardian_phone}
          onChange={e => setForm(f => ({ ...f, guardian_phone: e.target.value }))} />
      </label>
      <button className={styles.openBtn} disabled={saving} type="submit">
        {saving ? 'جارٍ الحفظ...' : 'حفظ'}
      </button>
      {msg && <p className={styles.formMsg}>{msg}</p>}
    </form>
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
      <ProfileForm />
      {!user?.must_change_password && <ChangePasswordForm forced={false} />}
      <WalletHistoryTable />
      <QrAndIdCard />
    </div>
  )
}
