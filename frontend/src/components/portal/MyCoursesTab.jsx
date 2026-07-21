import { useState, useEffect } from 'react'
import { getMyEnrollments, getCourse } from '../../api/courses'
import { blank, load } from './shared'
import VideoModal from './VideoModal'
import styles from '../../pages/PortalPage.module.css'

const STATUS_AR = { active: 'نشط', expired: 'منتهي', cancelled: 'ملغي' }

function CourseLessons({ slug }) {
  const [detail, setDetail] = useState(blank())
  useEffect(() => { load(() => getCourse(slug), setDetail) }, [slug])

  if (detail.loading) return <p className={styles.loading}>جارٍ التحميل...</p>
  if (detail.error) return <p className={styles.errorRow}>تعذّر تحميل دروس الكورس</p>

  const topics = detail.data?.topics ?? []
  if (!topics.length) return <p className={styles.empty}>لا توجد دروس منشورة بعد.</p>

  return (
    <div className={styles.lessonSubList}>
      {topics.map(topic => (
        <div key={topic.id}>
          <p className={styles.topicHeading}>{topic.title}</p>
          {topic.lessons.map(lesson => <LessonRow key={lesson.id} lesson={lesson} />)}
        </div>
      ))}
    </div>
  )
}

function LessonRow({ lesson }) {
  const [watching, setWatching] = useState(false)
  return (
    <div className={styles.lessonRow}>
      <span>{lesson.title}</span>
      <button className={styles.openBtnSmall} onClick={() => setWatching(true)}>شاهد</button>
      {watching && <VideoModal lessonId={lesson.id} onClose={() => setWatching(false)} />}
    </div>
  )
}

export default function MyCoursesTab() {
  const [state, setState] = useState(blank())
  const [openId, setOpenId] = useState(null)

  useEffect(() => { load(getMyEnrollments, setState) }, [])

  if (state.loading) return <p className={styles.loading}>جارٍ التحميل...</p>
  if (state.error) return (
    <div className={styles.errorRow}>
      <span>حدث خطأ في تحميل البيانات</span>
      <button className={styles.retryBtn} onClick={() => load(getMyEnrollments, setState)}>إعادة المحاولة</button>
    </div>
  )

  const list = Array.isArray(state.data) ? state.data : (state.data?.results ?? [])
  if (!list.length) return <p className={styles.empty}>لم تسجّل في أي كورس بعد.</p>

  return (
    <div>
      {list.map(e => (
        <div key={e.id} className={styles.card} style={{ flexDirection: 'column', alignItems: 'stretch' }}>
          <div className={styles.cardHeaderRow}>
            <div>
              <p className={styles.courseTitle}>{e.course_title}</p>
              <p className={styles.courseStatus}>حالة: {STATUS_AR[e.status] ?? e.status}</p>
            </div>
            <button className={styles.openBtn} onClick={() => setOpenId(openId === e.id ? null : e.id)}>
              {openId === e.id ? 'إخفاء الدروس' : 'دروس الكورس'}
            </button>
          </div>
          {openId === e.id && <CourseLessons slug={e.course_slug} />}
        </div>
      ))}
    </div>
  )
}
