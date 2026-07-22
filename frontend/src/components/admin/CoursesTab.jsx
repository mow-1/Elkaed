import { useEffect, useState } from 'react'
import { getMyBuilderCourses, deleteBuilderCourse } from '../../api/courseBuilder'
import CourseBuilderWizard from './CourseBuilder/CourseBuilderWizard'
import styles from '../../pages/AdminPanelPage.module.css'

export default function CoursesTab() {
  const [courses, setCourses] = useState(null)
  const [editingId, setEditingId] = useState(null) // null = list, 'new' = create, <id> = edit

  function reload() {
    setCourses(null)
    getMyBuilderCourses()
      .then(r => r.ok ? r.json() : [])
      .then(d => setCourses(Array.isArray(d) ? d : (d?.results ?? [])))
  }

  useEffect(reload, [])

  if (editingId !== null) {
    return (
      <CourseBuilderWizard
        courseId={editingId === 'new' ? null : editingId}
        onDone={() => { setEditingId(null); reload() }}
        onCancel={() => setEditingId(null)}
      />
    )
  }

  async function handleDelete(id) {
    if (!confirm('حذف هذا الكورس نهائياً؟')) return
    const res = await deleteBuilderCourse(id)
    if (!res.ok) {
      const body = await res.json().catch(() => ({}))
      alert(body.detail || 'تعذّر حذف الكورس')
      return
    }
    reload()
  }

  return (
    <div>
      <div className={styles.filterBar}>
        <button className={styles.btn} onClick={() => setEditingId('new')}>+ كورس جديد</button>
      </div>

      {!courses ? (
        <p className={styles.muted}>جاري التحميل...</p>
      ) : courses.length === 0 ? (
        <p className={styles.muted}>لا توجد كورسات بعد.</p>
      ) : (
        <div className={styles.tableWrap}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th className={styles.th}>العنوان</th>
                <th className={styles.th}>السعر</th>
                <th className={styles.th}>الحالة</th>
                <th className={styles.th}></th>
              </tr>
            </thead>
            <tbody>
              {courses.map(c => (
                <tr key={c.id} className={styles.tr}>
                  <td className={styles.td}>{c.title || 'بدون عنوان'}</td>
                  <td className={styles.td}>{c.price} جنيه</td>
                  <td className={styles.td}>
                    <span className={styles.chip} style={{ background: c.is_published ? '#D1FAE5' : '#FEF3C7', color: c.is_published ? '#065F46' : '#92400E' }}>
                      {c.is_published ? 'منشور' : 'مسودة'}
                    </span>
                  </td>
                  <td className={styles.td}>
                    <button className={styles.chipBtn} onClick={() => setEditingId(c.id)}>تعديل</button>
                    {' '}
                    <button className={styles.chipBtnDanger} onClick={() => handleDelete(c.id)}>حذف</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
