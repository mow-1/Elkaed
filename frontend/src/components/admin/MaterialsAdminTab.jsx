import { useState, useEffect } from 'react'
import { getAdminMaterials, createMaterial, updateMaterial, deleteMaterial } from '../../api/management'
import styles from '../../pages/AdminPanelPage.module.css'

const KIND_LABELS = { material: 'ملف', revision: 'مراجعة' }
const YEAR_LABELS = { '': 'كل السنوات', '1st': 'أول ثانوي', '2nd': 'ثاني ثانوي', '3rd': 'ثالث ثانوي' }
const VISIBILITY_LABELS = { '': 'الاثنين', center: 'سنتر', online: 'أونلاين' }

const EMPTY_FORM = { title_ar: '', title_en: '', kind: 'material', lesson: '', course: '', academic_year: '', visibility_student_type: '' }

export default function MaterialsAdminTab() {
  const [materials, setMaterials] = useState([])
  const [loading, setLoading]     = useState(true)
  const [form, setForm]           = useState(EMPTY_FORM)
  const [file, setFile]           = useState(null)
  const [saving, setSaving]       = useState(false)
  const [error, setError]         = useState('')

  function load() {
    setLoading(true)
    getAdminMaterials()
      .then(r => r.ok ? r.json() : [])
      .then(d => setMaterials(Array.isArray(d) ? d : (d?.results ?? [])))
      .finally(() => setLoading(false))
  }

  useEffect(load, [])

  async function handleCreate(e) {
    e.preventDefault()
    setSaving(true); setError('')
    const fd = new FormData()
    fd.append('title_ar', form.title_ar)
    if (form.title_en) fd.append('title_en', form.title_en)
    fd.append('kind', form.kind)
    if (form.lesson) fd.append('lesson', form.lesson)
    if (form.course) fd.append('course', form.course)
    fd.append('academic_year', form.academic_year)
    fd.append('visibility_student_type', form.visibility_student_type)
    fd.append('is_published', 'true')
    if (file) fd.append('file', file)

    const res = await createMaterial(fd)
    if (res.ok) {
      const nm = await res.json()
      setMaterials(m => [nm, ...m])
      setForm(EMPTY_FORM)
      setFile(null)
    } else {
      const d = await res.json().catch(() => null)
      setError(d?.detail ?? 'تحقق من البيانات المدخلة')
    }
    setSaving(false)
  }

  async function handleTogglePublish(m) {
    const res = await updateMaterial(m.id, { is_published: !m.is_published })
    if (res.ok) setMaterials(list => list.map(x => x.id === m.id ? { ...x, is_published: !x.is_published } : x))
  }

  async function handleDelete(id) {
    if (!confirm('حذف هذه المادة نهائياً؟')) return
    const res = await deleteMaterial(id)
    if (res.ok) setMaterials(list => list.filter(x => x.id !== id))
  }

  return (
    <div>
      <form className={styles.form} onSubmit={handleCreate}>
        <h3 className={styles.formHeading}>إضافة ملف / مراجعة</h3>
        <input className={styles.input} placeholder="العنوان" value={form.title_ar}
          onChange={e => setForm(f => ({ ...f, title_ar: e.target.value }))} required />
        <input className={styles.input} placeholder="العنوان بالإنجليزية (اختياري)" value={form.title_en}
          onChange={e => setForm(f => ({ ...f, title_en: e.target.value }))} />
        <select className={styles.select} value={form.kind} onChange={e => setForm(f => ({ ...f, kind: e.target.value }))}>
          {Object.entries(KIND_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <input className={styles.input} type="file" onChange={e => setFile(e.target.files[0])} />
        <p className={styles.muted}>لمراجعة فيديو: اترك الملف فارغاً وأدخل معرّف الدرس (Lesson ID) بدلاً من ذلك.</p>
        <input className={styles.input} type="number" placeholder="معرّف الدرس (اختياري، لمراجعات الفيديو)"
          value={form.lesson} onChange={e => setForm(f => ({ ...f, lesson: e.target.value }))} />
        <input className={styles.input} type="number" placeholder="معرّف الكورس (اختياري)"
          value={form.course} onChange={e => setForm(f => ({ ...f, course: e.target.value }))} />
        <select className={styles.select} value={form.academic_year} onChange={e => setForm(f => ({ ...f, academic_year: e.target.value }))}>
          {Object.entries(YEAR_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <select className={styles.select} value={form.visibility_student_type} onChange={e => setForm(f => ({ ...f, visibility_student_type: e.target.value }))}>
          {Object.entries(VISIBILITY_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        {error && <p className={styles.errorText}>{error}</p>}
        <button className={styles.btn} type="submit" disabled={saving}>{saving ? 'جاري الحفظ...' : 'إضافة'}</button>
      </form>

      {loading
        ? <p className={styles.muted}>جاري التحميل...</p>
        : (
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th className={styles.th}>العنوان</th>
                  <th className={styles.th}>النوع</th>
                  <th className={styles.th}>الصف</th>
                  <th className={styles.th}>الظهور</th>
                  <th className={styles.th}>الحالة</th>
                  <th className={styles.th}></th>
                </tr>
              </thead>
              <tbody>
                {materials.map(m => (
                  <tr key={m.id}>
                    <td className={styles.td}>{m.title_ar}</td>
                    <td className={styles.td}>{KIND_LABELS[m.kind] ?? m.kind}</td>
                    <td className={styles.td}>{YEAR_LABELS[m.academic_year] ?? m.academic_year}</td>
                    <td className={styles.td}>{VISIBILITY_LABELS[m.visibility_student_type] ?? m.visibility_student_type}</td>
                    <td className={styles.td}>
                      <button className={styles.chip} onClick={() => handleTogglePublish(m)}>
                        {m.is_published ? 'منشور' : 'غير منشور'}
                      </button>
                    </td>
                    <td className={styles.td}>
                      <button className={styles.chipBtnDanger} onClick={() => handleDelete(m.id)}>حذف</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {materials.length === 0 && <p className={styles.muted}>لا توجد ملفات بعد</p>}
          </div>
        )
      }
    </div>
  )
}
