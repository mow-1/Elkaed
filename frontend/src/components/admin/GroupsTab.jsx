import { useState, useEffect } from 'react'
import { getGroups, createGroup } from '../../api/attendance'
import { getCustomers, setCustomerGroup } from '../../api/management'
import styles from '../../pages/AdminPanelPage.module.css'

const YEAR_LABELS = { '1st': 'أول ثانوي', '2nd': 'ثاني ثانوي', '3rd': 'ثالث ثانوي' }
const EMPTY_FORM = { name_ar: '', academic_year: '1st', schedule_description: '', lesson_price_override: '' }

export default function GroupsTab() {
  const [groups, setGroups]   = useState([])
  const [loading, setLoading] = useState(true)
  const [form, setForm]       = useState(EMPTY_FORM)
  const [saving, setSaving]   = useState(false)
  const [selected, setSelected] = useState(null)

  function load() {
    setLoading(true)
    getGroups()
      .then(r => r.ok ? r.json() : [])
      .then(d => setGroups(Array.isArray(d) ? d : (d?.results ?? [])))
      .finally(() => setLoading(false))
  }

  useEffect(load, [])

  async function handleCreate(e) {
    e.preventDefault()
    setSaving(true)
    const res = await createGroup({
      name_ar:               form.name_ar,
      academic_year:         form.academic_year,
      schedule_description:  form.schedule_description,
      lesson_price_override: form.lesson_price_override || null,
    })
    if (res.ok) {
      const ng = await res.json()
      setGroups(g => [ng, ...g])
      setForm(EMPTY_FORM)
    }
    setSaving(false)
  }

  return (
    <div>
      <form className={styles.form} onSubmit={handleCreate}>
        <h3 className={styles.formHeading}>إنشاء مجموعة جديدة</h3>
        <input className={styles.input} placeholder="اسم المجموعة" value={form.name_ar}
          onChange={e => setForm(f => ({ ...f, name_ar: e.target.value }))} required />
        <select className={styles.select} value={form.academic_year}
          onChange={e => setForm(f => ({ ...f, academic_year: e.target.value }))}>
          {Object.entries(YEAR_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <input className={styles.input} placeholder="ميعاد المجموعة (اختياري)" value={form.schedule_description}
          onChange={e => setForm(f => ({ ...f, schedule_description: e.target.value }))} />
        <input className={styles.input} type="number" min="0" step="0.01" placeholder="سعر الحصة (اختياري، بيستخدم السعر العام لو فاضي)"
          value={form.lesson_price_override} onChange={e => setForm(f => ({ ...f, lesson_price_override: e.target.value }))} />
        <button className={styles.btn} type="submit" disabled={saving}>{saving ? 'جاري الحفظ...' : 'إنشاء المجموعة'}</button>
      </form>

      {loading
        ? <p className={styles.muted}>جاري التحميل...</p>
        : (
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th className={styles.th}>اسم المجموعة</th>
                  <th className={styles.th}>الصف</th>
                  <th className={styles.th}>الميعاد</th>
                  <th className={styles.th}>عدد الطلاب</th>
                  <th className={styles.th}></th>
                </tr>
              </thead>
              <tbody>
                {groups.map(g => (
                  <tr key={g.id}>
                    <td className={styles.td}>{g.name_ar}</td>
                    <td className={styles.td}>{YEAR_LABELS[g.academic_year] ?? g.academic_year}</td>
                    <td className={styles.td}>{g.schedule_description || '—'}</td>
                    <td className={styles.td}>{g.student_count}</td>
                    <td className={styles.td}>
                      <button className={styles.chipBtn} onClick={() => setSelected(g)}>الطلاب</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {groups.length === 0 && <p className={styles.muted}>لا توجد مجموعات</p>}
          </div>
        )
      }

      {selected && (
        <GroupStudentsPanel group={selected} onClose={() => setSelected(null)} onChanged={load} />
      )}
    </div>
  )
}

function GroupStudentsPanel({ group, onClose, onChanged }) {
  const [students, setStudents] = useState(null)
  const [studentId, setStudentId] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  function load() {
    getCustomers({ group: group.id })
      .then(r => r.ok ? r.json() : null)
      .then(d => setStudents(d?.results ?? []))
  }

  useEffect(load, [group.id])

  async function handleAdd(e) {
    e.preventDefault()
    setBusy(true); setError('')
    const res = await setCustomerGroup(parseInt(studentId), group.id)
    if (res.ok) {
      setStudentId('')
      load()
      onChanged()
    } else {
      setError('تأكد من معرّف الطالب (يمكن العثور عليه من تبويب العملاء)')
    }
    setBusy(false)
  }

  async function handleRemove(id) {
    if (!confirm('إزالة الطالب من المجموعة؟')) return
    await setCustomerGroup(id, null)
    load()
    onChanged()
  }

  return (
    <>
      <div className={styles.overlay} onClick={onClose} />
      <div className={styles.panel}>
        <button className={styles.panelClose} onClick={onClose}>✕</button>
        <h2 className={styles.panelHeading}>طلاب: {group.name_ar}</h2>

        <form className={styles.form} onSubmit={handleAdd}>
          <p className={styles.muted}>أدخل معرّف الطالب (ID) لإضافته للمجموعة</p>
          <input className={styles.input} type="number" placeholder="معرّف الطالب (ID)"
            value={studentId} onChange={e => setStudentId(e.target.value)} required />
          {error && <p className={styles.errorText}>{error}</p>}
          <button className={styles.btn} type="submit" disabled={busy}>إضافة</button>
        </form>

        {students === null
          ? <p className={styles.muted}>جاري التحميل...</p>
          : students.map(s => (
            <div key={s.id} className={styles.miniRow}>
              <span>{s.full_name} <span dir="ltr">({s.phone})</span></span>
              <button className={styles.chipBtnDanger} onClick={() => handleRemove(s.id)}>إزالة</button>
            </div>
          ))
        }
        {students?.length === 0 && <p className={styles.muted}>لا يوجد طلاب في هذه المجموعة</p>}
      </div>
    </>
  )
}
