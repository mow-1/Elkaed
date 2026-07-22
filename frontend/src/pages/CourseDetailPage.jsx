import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { getCourse, enrollCourse } from '../api/courses'
import { useAuth } from '../context/AuthContext'
import { useCart } from '../context/CartContext'
import styles from './CourseDetailPage.module.css'

function formatDuration(secs) {
  return Math.floor(secs / 60).toString().padStart(2, '0') + ':' + (secs % 60).toString().padStart(2, '0')
}

export default function CourseDetailPage() {
  const { slug } = useParams()
  const { user } = useAuth()
  const { addItem, has } = useCart()
  const [course, setCourse] = useState(null)
  const [loading, setLoading] = useState(true)
  const [notFound, setNotFound] = useState(false)
  const [openTopics, setOpenTopics] = useState({})
  const [enrollState, setEnrollState] = useState('idle') // idle | loading | success | enrolled

  useEffect(() => {
    setLoading(true)
    setNotFound(false)
    setCourse(null)
    getCourse(slug)
      .then(res => {
        if (res.status === 404) { setNotFound(true); return null }
        if (!res.ok) throw new Error()
        return res.json()
      })
      .then(data => { if (data) setCourse(data) })
      .catch(() => setNotFound(true))
      .finally(() => setLoading(false))
  }, [slug])

  const toggleTopic = (id) => setOpenTopics(prev => ({ ...prev, [id]: !prev[id] }))

  const handleEnroll = async () => {
    setEnrollState('loading')
    try {
      const res = await enrollCourse(course.id)
      if (res.ok) {
        setEnrollState('success')
      } else {
        setEnrollState(res.status === 400 ? 'enrolled' : 'idle')
      }
    } catch {
      setEnrollState('idle')
    }
  }

  if (loading) {
    return (
      <div className={styles.center}>
        <div className={styles.spinner} />
      </div>
    )
  }

  if (notFound || !course) {
    return (
      <div className={styles.center}>
        <p className={styles.notFoundText}>الكورس غير موجود</p>
        <Link to="/" className={styles.backLink}>← العودة للرئيسية</Link>
      </div>
    )
  }

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <div className={styles.thumbnail}>
          {course.thumbnail
            ? <img src={course.thumbnail} alt={course.title} />
            : <div className={styles.thumbPlaceholder}><span>𓂀</span></div>
          }
        </div>

        <div className={styles.info}>
          <p className={styles.breadcrumb}>
            <Link to="/">الكورسات</Link> / {course.category?.name}
          </p>
          <h1 className={styles.title}>{course.title}</h1>
          <div className={styles.instructorRow}>
            <span className={styles.instructorAvatar}>𓂀</span>
            <span className={styles.instructorName}>{course.instructor_name}</span>
          </div>
          <p className={styles.price}>{course.price} ج.م</p>

          <div className={styles.enrollWrap}>
            {enrollState === 'success' && <p className={styles.enrollMsg}>✓ تم التسجيل بنجاح</p>}
            {enrollState === 'enrolled' && <p className={styles.enrollMsg}>أنت مشترك بالفعل</p>}
            {!user ? (
              <Link to="/login" className={styles.enrollBtn}>سجّل الدخول للتسجيل</Link>
            ) : (
              <>
                <button
                  className={styles.enrollBtn}
                  onClick={handleEnroll}
                  disabled={enrollState === 'loading' || enrollState === 'success'}
                >
                  {enrollState === 'loading' ? 'جاري التسجيل...' : 'اشترك الآن'}
                </button>
                <button
                  className={styles.cartBtn}
                  disabled={has(course.id) || enrollState === 'success'}
                  onClick={() => addItem({ id: course.id, title: course.title, price: course.price })}
                >
                  {has(course.id) ? '✓ في السلة' : 'أضف للسلة'}
                </button>
              </>
            )}
          </div>
        </div>
      </div>

      {course.topics?.length > 0 && (
        <div className={styles.topics}>
          <h2 className={styles.topicsHeading}>محتوى الكورس</h2>
          {course.topics.map(topic => (
            <div key={topic.id} className={styles.topicBlock}>
              <button
                className={styles.topicRow}
                onClick={() => toggleTopic(topic.id)}
                aria-expanded={!!openTopics[topic.id]}
              >
                <span className={styles.topicTitle}>{topic.title}</span>
                <span className={styles.topicMeta}>
                  {(topic.items ?? []).length} عنصر {openTopics[topic.id] ? '▲' : '▼'}
                </span>
              </button>
              {openTopics[topic.id] && (
                <ul className={styles.lessonList}>
                  {(topic.items ?? []).map(item => (
                    <li key={`${item.type}-${item.id}`} className={styles.lessonItem}>
                      <span className={styles.lessonTitle}>
                        {item.type === 'quiz' ? '📝 ' : item.type === 'assignment' ? '📄 ' : ''}
                        {item.title}
                      </span>
                      <span className={styles.lessonMeta}>
                        {item.type === 'lesson' && (
                          item.is_free_preview
                            ? <span className={styles.freeChip}>مجاني</span>
                            : <span>🔒</span>
                        )}
                        {item.type === 'lesson' && <span className={styles.duration}>{formatDuration(item.duration_seconds)}</span>}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
