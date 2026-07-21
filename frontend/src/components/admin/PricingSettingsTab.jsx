import { useState, useEffect } from 'react'
import { getPricingSettings, updatePricingSettings } from '../../api/attendance'
import styles from '../../pages/AdminPanelPage.module.css'

const NUMBER_FIELDS = [
  ['single_lesson_price',   'سعر الحصة الواحدة (جنيه)'],
  ['monthly_package_price', 'سعر الباقة الشهرية (جنيه)'],
  ['package_lesson_count',  'عدد حصص الباقة'],
]

const BOOL_FIELDS = [
  ['allow_negative_balance',     'السماح برصيد سالب في المحفظة'],
  ['notify_guardian_on_absence', 'إشعار ولي الأمر عند الغياب'],
  ['show_governorate_field',     'إظهار حقل المحافظة عند التسجيل'],
  ['show_school_field',          'إظهار حقل المدرسة عند التسجيل'],
]

export default function PricingSettingsTab() {
  const [form, setForm]       = useState(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving]   = useState(false)
  const [msg, setMsg]         = useState('')

  useEffect(() => {
    getPricingSettings()
      .then(r => r.ok ? r.json() : null)
      .then(d => { if (d) setForm(d) })
      .finally(() => setLoading(false))
  }, [])

  async function handleSubmit(e) {
    e.preventDefault()
    setSaving(true); setMsg('')
    const res = await updatePricingSettings({
      single_lesson_price:   form.single_lesson_price,
      monthly_package_price: form.monthly_package_price,
      package_lesson_count:  form.package_lesson_count,
      allow_negative_balance:     form.allow_negative_balance,
      notify_guardian_on_absence: form.notify_guardian_on_absence,
      show_governorate_field:    form.show_governorate_field,
      show_school_field:         form.show_school_field,
    })
    if (res.ok) {
      setForm(await res.json())
      setMsg('تم الحفظ بنجاح')
    } else {
      setMsg('حدث خطأ أثناء الحفظ')
    }
    setSaving(false)
  }

  if (loading) return <p className={styles.muted}>جاري التحميل...</p>
  if (!form)   return <p className={styles.muted}>خطأ في تحميل الإعدادات</p>

  return (
    <form className={styles.form} onSubmit={handleSubmit} style={{ maxWidth: 480 }}>
      <h3 className={styles.formHeading}>إعدادات التسعير</h3>

      {NUMBER_FIELDS.map(([key, label]) => (
        <div key={key}>
          <label className={styles.inputLabel}>{label}</label>
          <input
            className={styles.input}
            type="number"
            min="0"
            step={key === 'package_lesson_count' ? '1' : '0.01'}
            value={form[key]}
            onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))}
            required
          />
        </div>
      ))}

      {BOOL_FIELDS.map(([key, label]) => (
        <label key={key} className={styles.checkRow}>
          <input
            type="checkbox"
            checked={!!form[key]}
            onChange={e => setForm(f => ({ ...f, [key]: e.target.checked }))}
          />
          {label}
        </label>
      ))}

      {msg && <p className={styles.muted}>{msg}</p>}
      <button className={styles.btn} type="submit" disabled={saving}>{saving ? 'جاري الحفظ...' : 'حفظ'}</button>
    </form>
  )
}
