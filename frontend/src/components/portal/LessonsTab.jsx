import { useEffect, useState } from 'react'
import { getMyLessons } from '../../api/portal'
import { blank, load } from './shared'
import VideoModal from './VideoModal'
import styles from '../../pages/PortalPage.module.css'

export default function LessonsTab() {
  const [state, setState] = useState(blank())
  const [watchLessonId, setWatchLessonId] = useState(null)

  useEffect(() => { load(getMyLessons, setState) }, [])

  if (state.loading) return <p className={styles.loading}>جارٍ التحميل...</p>
  if (state.error) return (
    <div className={styles.errorRow}>
      <span>حدث خطأ في تحميل البيانات</span>
      <button className={styles.retryBtn} onClick={() => load(getMyLessons, setState)}>إعادة المحاولة</button>
    </div>
  )

  const list = Array.isArray(state.data) ? state.data : []
  if (!list.length) return <p className={styles.empty}>لا توجد دروس متاحة بعد.</p>

  return (
    <div>
      {list.map(l => (
        <div key={l.id} className={styles.card}>
          <div>
            <p className={styles.courseTitle}>
              {l.title}{' '}
              {l.source === 'absence_grant' && <span className={styles.badgeGold}>درس تعويضي</span>}
            </p>
            <p className={styles.courseStatus}>
              {l.course_title} — {l.view_limit > 0 ? `${l.view_count} / ${l.view_limit} مشاهدات` : 'مشاهدات غير محدودة'}
            </p>
          </div>
          <button className={styles.openBtn} onClick={() => setWatchLessonId(l.id)}>شاهد</button>
        </div>
      ))}
      {watchLessonId && (
        <VideoModal lessonId={watchLessonId} onClose={() => setWatchLessonId(null)} />
      )}
    </div>
  )
}
