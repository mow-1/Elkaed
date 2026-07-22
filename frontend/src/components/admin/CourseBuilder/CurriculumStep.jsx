import { useEffect, useState } from 'react'
import { getCourseCurriculum, createTopic, deleteTopic, deleteLesson, deleteTopicQuiz, deleteAssignment } from '../../../api/courseBuilder'
import LessonEditor from './LessonEditor'
import QuizEditor from './QuizEditor'
import AssignmentEditor from './AssignmentEditor'
import styles from '../../../pages/AdminPanelPage.module.css'

const ITEM_ICON = { lesson: '🎬', quiz: '📝', assignment: '📄' }
const ITEM_LABEL = { lesson: 'درس', quiz: 'اختبار', assignment: 'واجب' }

export default function CurriculumStep({ course, onDone }) {
  const [topics, setTopics] = useState(null)
  const [newTopicTitle, setNewTopicTitle] = useState('')
  const [savingTopic, setSavingTopic] = useState(false)
  // { topicId: 'lesson' | 'quiz' | 'assignment' } — which add-form is open per topic
  const [activeEditor, setActiveEditor] = useState({})

  function reload() {
    getCourseCurriculum(course.id).then(r => r.ok ? r.json() : null).then(d => {
      if (d) setTopics(d.topics)
    })
  }

  useEffect(reload, [course.id])

  async function handleAddTopic(e) {
    e.preventDefault()
    if (!newTopicTitle.trim()) return
    setSavingTopic(true)
    try {
      const res = await createTopic(course.id, { title: newTopicTitle.trim() })
      if (res.ok) { setNewTopicTitle(''); reload() }
    } finally {
      setSavingTopic(false)
    }
  }

  async function handleDeleteTopic(id) {
    if (!confirm('حذف هذا الموضوع وكل محتواه؟')) return
    await deleteTopic(id)
    reload()
  }

  async function handleDeleteItem(item) {
    if (!confirm('حذف هذا العنصر؟')) return
    if (item.type === 'lesson') await deleteLesson(item.id)
    else if (item.type === 'quiz') await deleteTopicQuiz(item.topicId)
    else await deleteAssignment(item.id)
    reload()
  }

  if (!topics) return <p className={styles.muted}>جاري التحميل...</p>

  return (
    <div>
      <form className={styles.filterBar} onSubmit={handleAddTopic}>
        <input
          className={styles.input}
          placeholder="عنوان موضوع جديد..."
          value={newTopicTitle}
          onChange={e => setNewTopicTitle(e.target.value)}
        />
        <button className={styles.btn} type="submit" disabled={savingTopic}>+ إضافة موضوع</button>
      </form>

      {topics.length === 0 && <p className={styles.muted}>لا توجد مواضيع بعد — أضف موضوعاً أولاً.</p>}

      {topics.map(topic => (
        <div key={topic.id} className={styles.panel} style={{ position: 'static', marginBottom: 16 }}>
          <div className={styles.miniRow}>
            <h3 className={styles.panelHeading}>{topic.title}</h3>
            <button className={styles.chipBtnDanger} onClick={() => handleDeleteTopic(topic.id)}>حذف الموضوع</button>
          </div>

          {topic.items.map(item => (
            <div key={`${item.type}-${item.id}`} className={styles.detailRow}>
              <span>{ITEM_ICON[item.type]} {item.title} <span className={styles.muted}>({ITEM_LABEL[item.type]})</span></span>
              <button className={styles.chipBtnDanger} onClick={() => handleDeleteItem({ ...item, topicId: topic.id })}>حذف</button>
            </div>
          ))}

          {activeEditor[topic.id] === 'lesson' && (
            <LessonEditor topicId={topic.id}
              onSaved={() => { setActiveEditor(s => ({ ...s, [topic.id]: null })); reload() }}
              onCancel={() => setActiveEditor(s => ({ ...s, [topic.id]: null }))} />
          )}
          {activeEditor[topic.id] === 'quiz' && (
            <QuizEditor topicId={topic.id}
              onSaved={() => { setActiveEditor(s => ({ ...s, [topic.id]: null })); reload() }}
              onCancel={() => setActiveEditor(s => ({ ...s, [topic.id]: null }))} />
          )}
          {activeEditor[topic.id] === 'assignment' && (
            <AssignmentEditor topicId={topic.id}
              onSaved={() => { setActiveEditor(s => ({ ...s, [topic.id]: null })); reload() }}
              onCancel={() => setActiveEditor(s => ({ ...s, [topic.id]: null }))} />
          )}

          {!activeEditor[topic.id] && (
            <div className={styles.filterBar} style={{ marginTop: 12 }}>
              <button className={styles.chipBtn} onClick={() => setActiveEditor(s => ({ ...s, [topic.id]: 'lesson' }))}>+ درس</button>
              <button className={styles.chipBtn} onClick={() => setActiveEditor(s => ({ ...s, [topic.id]: 'quiz' }))}>+ اختبار</button>
              <button className={styles.chipBtn} onClick={() => setActiveEditor(s => ({ ...s, [topic.id]: 'assignment' }))}>+ واجب</button>
            </div>
          )}
        </div>
      ))}

      <button className={styles.btn} onClick={onDone}>إنهاء</button>
    </div>
  )
}
