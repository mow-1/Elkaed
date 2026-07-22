import { useState, useEffect } from 'react'
import { getPackages, createPackage, applyPackage } from '../../api/attendance'
import styles from '../../pages/AdminPanelPage.module.css'

const EMPTY_FORM = { name: '', lesson_count: '', price: '' }

export default function PackagesTab() {
  const [packages, setPackages] = useState([])
  const [loading, setLoading]   = useState(true)
  const [form, setForm]         = useState(EMPTY_FORM)
  const [saving, setSaving]     = useState(false)
  const [applyState, setApplyState] = useState({}) // { [packageId]: { studentId, busy, msg } }

  function load() {
    setLoading(true)
    getPackages()
      .then(r => r.ok ? r.json() : [])
      .then(d => setPackages(Array.isArray(d) ? d : (d?.results ?? [])))
      .finally(() => setLoading(false))
  }

  useEffect(load, [])

  async function handleCreate(e) {
    e.preventDefault()
    setSaving(true)
    const res = await createPackage({
      name:         form.name,
      lesson_count: parseInt(form.lesson_count),
      price:        form.price,
    })
    if (res.ok) {
      const np = await res.json()
      setPackages(p => [...p, np])
      setForm(EMPTY_FORM)
    }
    setSaving(false)
  }

  function setApplyField(packageId, field, value) {
    setApplyState(s => ({ ...s, [packageId]: { ...s[packageId], [field]: value } }))
  }

  async function handleApply(packageId) {
    const studentId = applyState[packageId]?.studentId
    if (!studentId) return
    setApplyField(packageId, 'busy', true)
    setApplyField(packageId, 'msg', '')
    const res = await applyPackage(packageId, parseInt(studentId))
    const body = await res.json().catch(() => ({}))
    if (res.ok) {
      setApplyField(packageId, 'msg', `تم — الرصيد: ${body.wallet_balance} ج.م، حصص متبقية: ${body.prepaid_lessons_remaining}`)
      setApplyField(packageId, 'studentId', '')
    } else {
      setApplyField(packageId, 'msg', body.detail ?? 'تحقق من معرّف الطالب أو الرصيد')
    }
    setApplyField(packageId, 'busy', false)
  }

  return (
    <div>
      <form className={styles.form} onSubmit={handleCreate}>
        <h3 className={styles.formHeading}>إنشاء باقة حصص جديدة</h3>
        <input className={styles.input} placeholder="اسم الباقة (مثال: باقة 8 حصص)" value={form.name}
          onChange={e => setForm(f => ({ ...f, name: e.target.value }))} required />
        <input className={styles.input} type="number" min="1" placeholder="عدد الحصص"
          value={form.lesson_count} onChange={e => setForm(f => ({ ...f, lesson_count: e.target.value }))} required />
        <input className={styles.input} type="number" min="0" step="0.01" placeholder="السعر بالجنيه"
          value={form.price} onChange={e => setForm(f => ({ ...f, price: e.target.value }))} required />
        <button className={styles.btn} type="submit" disabled={saving}>{saving ? 'جاري الحفظ...' : 'إنشاء الباقة'}</button>
      </form>

      {loading
        ? <p className={styles.muted}>جاري التحميل...</p>
        : (
          <div className={styles.listItems}>
            {packages.map(p => (
              <div key={p.id} className={styles.listItem}>
                <div>
                  <div className={styles.listTitle}>{p.name}</div>
                  <div className={styles.listMeta}>{p.lesson_count} حصة — {p.price} جنيه</div>
                </div>
                <div>
                  <input
                    className={styles.input}
                    type="number"
                    placeholder="معرّف الطالب (ID)"
                    value={applyState[p.id]?.studentId ?? ''}
                    onChange={e => setApplyField(p.id, 'studentId', e.target.value)}
                  />
                  <button className={styles.chipBtn} disabled={applyState[p.id]?.busy || !applyState[p.id]?.studentId}
                    onClick={() => handleApply(p.id)}>
                    تطبيق على طالب
                  </button>
                  {applyState[p.id]?.msg && <p className={styles.muted}>{applyState[p.id].msg}</p>}
                </div>
              </div>
            ))}
            {packages.length === 0 && <p className={styles.muted}>لا توجد باقات</p>}
          </div>
        )
      }
    </div>
  )
}
