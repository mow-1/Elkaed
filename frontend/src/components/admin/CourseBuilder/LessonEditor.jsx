import { useState } from 'react'
import { createLesson } from '../../../api/courseBuilder'
import styles from '../../../pages/AdminPanelPage.module.css'

export default function LessonEditor({ topicId, onSaved, onCancel }) {
  const [title, setTitle] = useState('')
  const [videoSource, setVideoSource] = useState('self_hosted')
  const [videoFile, setVideoFile] = useState(null)
  const [youtubeId, setYoutubeId] = useState('')
  const [isFreePreview, setIsFreePreview] = useState(false)
  const [viewLimit, setViewLimit] = useState(10)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(e) {
    e.preventDefault()
    setSaving(true)
    setError('')
    try {
      const fd = new FormData()
      fd.append('title', title)
      fd.append('video_source', videoSource)
      fd.append('is_free_preview', isFreePreview)
      fd.append('view_limit', viewLimit)
      if (videoSource === 'self_hosted' && videoFile) fd.append('raw_file', videoFile)
      if (videoSource === 'youtube') fd.append('youtube_id', youtubeId)

      const res = await createLesson(topicId, fd)
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
      <label className={styles.inputLabel}>عنوان الدرس
        <input className={styles.input} value={title} required onChange={e => setTitle(e.target.value)} />
      </label>

      <label className={styles.inputLabel}>مصدر الفيديو
        <select className={styles.select} value={videoSource} onChange={e => setVideoSource(e.target.value)}>
          <option value="self_hosted">رفع فيديو</option>
          <option value="youtube">يوتيوب</option>
        </select>
      </label>

      {videoSource === 'self_hosted' ? (
        <label className={styles.inputLabel}>ملف الفيديو
          <input type="file" accept="video/*" onChange={e => setVideoFile(e.target.files[0])} />
        </label>
      ) : (
        <label className={styles.inputLabel}>معرف فيديو يوتيوب
          <input className={styles.input} dir="ltr" value={youtubeId} onChange={e => setYoutubeId(e.target.value)} />
        </label>
      )}

      <label className={styles.inputLabel}>حد المشاهدات (0 = غير محدود)
        <input className={styles.input} type="number" min="0" value={viewLimit} onChange={e => setViewLimit(e.target.value)} />
      </label>

      <label className={styles.inputLabel} style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
        <input type="checkbox" checked={isFreePreview} onChange={e => setIsFreePreview(e.target.checked)} />
        معاينة مجانية
      </label>

      {error && <p className={styles.errorText}>{error}</p>}

      <div className={styles.filterBar}>
        <button className={styles.btn} type="submit" disabled={saving}>{saving ? 'جارٍ الحفظ...' : 'حفظ الدرس'}</button>
        <button className={styles.chipBtn} type="button" onClick={onCancel}>إلغاء</button>
      </div>
    </form>
  )
}
