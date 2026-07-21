import { useState, useEffect } from 'react'
import { getDiscounts, createDiscount, updateDiscount } from '../../api/attendance'
import styles from '../../pages/AdminPanelPage.module.css'

const TYPE_LABELS  = { percentage: 'نسبة مئوية', fixed_amount: 'مبلغ ثابت', free: 'مجاني' }
const SCOPE_LABELS = { physical_only: 'حضوري فقط', online_only: 'أونلاين فقط', both: 'الاثنين' }

const EMPTY_FORM = { student_id: '', discount_type: 'percentage', value: '', scope: 'both', reason: '', starts_at: '', ends_at: '' }

export default function DiscountsTab() {
  const [discounts, setDiscounts] = useState([])
  const [loading, setLoading]     = useState(true)
  const [form, setForm]           = useState(EMPTY_FORM)
  const [saving, setSaving]       = useState(false)
  const [error, setError]         = useState('')

  function load() {
    setLoading(true)
    getDiscounts()
      .then(r => r.ok ? r.json() : [])
      .then(d => setDiscounts(Array.isArray(d) ? d : (d?.results ?? [])))
      .finally(() => setLoading(false))
  }

  useEffect(load, [])

  async function handleCreate(e) {
    e.preventDefault()
    setSaving(true); setError('')
    const res = await createDiscount({
      student_id:    parseInt(form.student_id),
      discount_type: form.discount_type,
      value:         form.value,
      scope:         form.scope,
      reason:        form.reason,
      starts_at:     form.starts_at || null,
      ends_at:       form.ends_at || null,
    })
    if (res.ok) {
      const nd = await res.json()
      setDiscounts(d => [nd, ...d])
      setForm(EMPTY_FORM)
    } else {
      const d = await res.json().catch(() => null)
      setError(d?.detail ?? 'تحقق من البيانات المدخلة (خاصة معرّف الطالب)')
    }
    setSaving(false)
  }

  async function handleRevoke(id) {
    if (!confirm('إلغاء هذا الخصم؟')) return
    const res = await updateDiscount(id, { active: false })
    if (res.ok) setDiscounts(d => d.map(x => x.id === id ? { ...x, active: false } : x))
  }

  return (
    <div>
      <form className={styles.form} onSubmit={handleCreate}>
        <h3 className={styles.formHeading}>إضافة خصم جديد</h3>
        <p className={styles.muted}>أدخل معرّف الطالب (ID) — يمكن العثور عليه من تبويب العملاء</p>
        <input className={styles.input} type="number" placeholder="معرّف الطالب (ID)"
          value={form.student_id} onChange={e => setForm(f => ({ ...f, student_id: e.target.value }))} required />
        <select className={styles.select} value={form.discount_type}
          onChange={e => setForm(f => ({ ...f, discount_type: e.target.value }))}>
          {Object.entries(TYPE_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <input className={styles.input} type="number" min="0" step="0.01" placeholder="القيمة"
          value={form.value} onChange={e => setForm(f => ({ ...f, value: e.target.value }))} required />
        <select className={styles.select} value={form.scope}
          onChange={e => setForm(f => ({ ...f, scope: e.target.value }))}>
          {Object.entries(SCOPE_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <textarea className={styles.textarea} placeholder="سبب الخصم" rows={3}
          value={form.reason} onChange={e => setForm(f => ({ ...f, reason: e.target.value }))} required />
        <label className={styles.inputLabel}>يبدأ في (اختياري)</label>
        <input className={styles.input} type="datetime-local"
          value={form.starts_at} onChange={e => setForm(f => ({ ...f, starts_at: e.target.value }))} />
        <label className={styles.inputLabel}>ينتهي في (اختياري)</label>
        <input className={styles.input} type="datetime-local"
          value={form.ends_at} onChange={e => setForm(f => ({ ...f, ends_at: e.target.value }))} />
        {error && <p className={styles.errorText}>{error}</p>}
        <button className={styles.btn} type="submit" disabled={saving}>{saving ? 'جاري الحفظ...' : 'إضافة الخصم'}</button>
      </form>

      {loading
        ? <p className={styles.muted}>جاري التحميل...</p>
        : (
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th className={styles.th}>الطالب</th>
                  <th className={styles.th}>النوع</th>
                  <th className={styles.th}>القيمة</th>
                  <th className={styles.th}>النطاق</th>
                  <th className={styles.th}>السبب</th>
                  <th className={styles.th}>الحالة</th>
                  <th className={styles.th}>بواسطة</th>
                  <th className={styles.th}>التاريخ</th>
                  <th className={styles.th}></th>
                </tr>
              </thead>
              <tbody>
                {discounts.map(d => (
                  <tr key={d.id}>
                    <td className={styles.td}>{d.student?.full_name} <span dir="ltr">({d.student?.phone})</span></td>
                    <td className={styles.td}>{TYPE_LABELS[d.discount_type] ?? d.discount_type}</td>
                    <td className={styles.td}>{d.value}</td>
                    <td className={styles.td}>{SCOPE_LABELS[d.scope] ?? d.scope}</td>
                    <td className={styles.td}>{d.reason}</td>
                    <td className={styles.td}><span className={styles.chip}>{d.active ? 'فعال' : 'ملغي'}</span></td>
                    <td className={styles.td}>{d.created_by?.full_name ?? '—'}</td>
                    <td className={styles.td}>{new Date(d.created_at).toLocaleDateString('ar-EG')}</td>
                    <td className={styles.td}>
                      {d.active && <button className={styles.chipBtnDanger} onClick={() => handleRevoke(d.id)}>إلغاء</button>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {discounts.length === 0 && <p className={styles.muted}>لا توجد خصومات</p>}
          </div>
        )
      }
    </div>
  )
}
