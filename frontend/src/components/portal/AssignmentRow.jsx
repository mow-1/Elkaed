import { useEffect, useState } from 'react'
import { getMyAssignmentSubmission, submitAssignment } from '../../api/courseBuilder'
import styles from '../../pages/PortalPage.module.css'

export default function AssignmentRow({ item }) {
  const [submission, setSubmission] = useState(undefined) // undefined = loading, null = none yet
  const [file, setFile] = useState(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    getMyAssignmentSubmission(item.id)
      .then(r => r.ok ? r.json() : null)
      .then(setSubmission)
  }, [item.id])

  async function handleSubmit() {
    if (!file) return
    setSaving(true)
    try {
      const res = await submitAssignment(item.id, file)
      if (res.ok) setSubmission(await res.json())
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className={styles.lessonRow} style={{ flexDirection: 'column', alignItems: 'stretch', gap: 8 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
        <span>{item.title}</span>
        {item.due_at && <span className={styles.courseStatus}>الموعد النهائي: {new Date(item.due_at).toLocaleString('ar-EG')}</span>}
      </div>
      {submission === undefined ? null : submission ? (
        <span className={styles.badgeGreen}>تم التسليم بتاريخ {new Date(submission.submitted_at).toLocaleDateString('ar-EG')}</span>
      ) : (
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <input type="file" onChange={e => setFile(e.target.files[0])} />
          <button className={styles.openBtnSmall} disabled={!file || saving} onClick={handleSubmit}>
            {saving ? 'جارٍ الرفع...' : 'تسليم'}
          </button>
        </div>
      )}
    </div>
  )
}
