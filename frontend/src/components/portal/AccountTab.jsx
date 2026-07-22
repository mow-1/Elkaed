import { useEffect, useRef, useState } from 'react'
import { changePassword, getMyQrCode, getMyIdCardPdf } from '../../api/auth'
import { getWallet } from '../../api/commerce'
import { getWalletHistory } from '../../api/portal'
import { useAuth } from '../../context/AuthContext'
import { blank, load } from './shared'
import ProfileForm from '../ProfileForm'
import styles from '../../pages/PortalPage.module.css'

function pageFromUrl(url) {
  if (!url) return null
  try { return new URL(url).searchParams.get('page') } catch { return null }
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
