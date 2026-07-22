import { useEffect, useState } from 'react'
import { getProfile, updateProfile } from '../api/auth'
import { useAuth } from '../context/AuthContext'
import { blank } from './portal/shared'
import styles from '../pages/PortalPage.module.css'

// Shared editable profile form (name + guardian phone) — used by both /portal's
// Account tab and /dashboard's Profile tab, so there's exactly one place students
// can actually edit their info, not a read-only display on one page and a working
// form on the other.
export default function ProfileForm() {
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
