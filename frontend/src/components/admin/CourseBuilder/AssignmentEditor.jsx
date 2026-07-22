import { useState } from 'react'
import { createAssignment } from '../../../api/courseBuilder'
import styles from '../../../pages/AdminPanelPage.module.css'

export default function AssignmentEditor({ topicId, onSaved, onCancel }) {
  const [title, setTitle] = useState('')
  const [instructions, setInstructions] = useState('')
  const [dueAt, setDueAt] = useState('')
  const [attachment, setAttachment] = useState(null)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(e) {
    e.preventDefault()
    setSaving(true)
    setError('')
    try {
      const fd = new FormData()
      fd.append('title_ar', title)
      fd.append('instructions', instructions)
      if (dueAt) fd.append('due_at', dueAt)
      if (attachment) fd.append('attachment', attachment)

      const res = await createAssignment(topicId, fd)
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        setError(Object.values(body).flat().join(' — ') || 'حدث خطأ')
        return
      }
      onSaved()
    } finally {
      setSaving(false)
    }
  }

  return (
    <form className={styles.form} onSubmit={handleSubmit} style={{ marginTop: 12 }}>
      <label className={styles.inputLabel}>عنوان الواجب
        <input className={styles.input} value={title} required onChange={e => setTitle(e.target.value)} />
      </label>

      <label className={styles.inputLabel}>التعليمات
        <textarea className={styles.textarea} value={instructions} onChange={e => setInstructions(e.target.value)} />
      </label>

      <label className={styles.inputLabel}>ملف مرفق (اختياري)
        <input type="file" onChange={e => setAttachment(e.target.files[0])} />
      </label>

      <label className={styles.inputLabel}>الموعد النهائي (اختياري)
        <input className={styles.input} type="datetime-local" value={dueAt} onChange={e => setDueAt(e.target.value)} />
      </label>

      {error && <p className={styles.errorText}>{error}</p>}

      <div className={styles.filterBar}>
        <button className={styles.btn} type="submit" disabled={saving}>{saving ? 'جارٍ الحفظ...' : 'حفظ الواجب'}</button>
        <button className={styles.chipBtn} type="button" onClick={onCancel}>إلغاء</button>
      </div>
    </form>
  )
}
