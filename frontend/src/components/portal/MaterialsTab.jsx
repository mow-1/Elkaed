import { useEffect, useState } from 'react'
import { getMaterials } from '../../api/portal'
import { blank, load } from './shared'
import VideoModal from './VideoModal'
import styles from '../../pages/PortalPage.module.css'

// Reused as-is (kind="revision" prop) for the المراجعات tab — thin wrapper, no duplication.
export default function MaterialsTab({ kind = 'material' }) {
  const [state, setState] = useState(blank())
  const [watchLessonId, setWatchLessonId] = useState(null)

  useEffect(() => { load(() => getMaterials(kind), setState) }, [kind])

  if (state.loading) return <p className={styles.loading}>جارٍ التحميل...</p>
  if (state.error) return (
    <div className={styles.errorRow}>
      <span>حدث خطأ في تحميل البيانات</span>
      <button className={styles.retryBtn} onClick={() => load(() => getMaterials(kind), setState)}>إعادة المحاولة</button>
    </div>
  )

  const list = Array.isArray(state.data) ? state.data : (state.data?.results ?? [])
  if (!list.length) return (
    <p className={styles.empty}>{kind === 'revision' ? 'لا توجد مراجعات متاحة حالياً.' : 'لا توجد ملفات متاحة حالياً.'}</p>
  )

  return (
    <div>
      {list.map(m => (
        <div key={m.id} className={styles.card}>
          <div>
            <p className={styles.courseTitle}>{m.title_ar || m.title_en}</p>
            {m.course_slug && <p className={styles.courseStatus}>{m.course_slug}</p>}
          </div>
          <div className={styles.cardActions}>
            {m.file && (
              <a href={m.file} target="_blank" rel="noreferrer" className={styles.openBtn}>تحميل</a>
            )}
            {m.lesson_id && (
              <button className={styles.openBtn} onClick={() => setWatchLessonId(m.lesson_id)}>شاهد الفيديو</button>
            )}
          </div>
        </div>
      ))}
      {watchLessonId && (
        <VideoModal lessonId={watchLessonId} onClose={() => setWatchLessonId(null)} />
      )}
    </div>
  )
}
