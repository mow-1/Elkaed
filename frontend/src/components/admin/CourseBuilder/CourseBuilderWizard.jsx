import { useEffect, useState } from 'react'
import { getBuilderCourse } from '../../../api/courseBuilder'
import BasicsStep from './BasicsStep'
import CurriculumStep from './CurriculumStep'
import styles from '../../../pages/AdminPanelPage.module.css'

export default function CourseBuilderWizard({ courseId, onDone, onCancel }) {
  const [course, setCourse] = useState(null)
  const [step, setStep] = useState('basics')
  const [loading, setLoading] = useState(!!courseId)

  useEffect(() => {
    if (!courseId) return
    getBuilderCourse(courseId).then(r => r.ok ? r.json() : null).then(c => {
      setCourse(c)
      setLoading(false)
    })
  }, [courseId])

  if (loading) return <p className={styles.muted}>جاري التحميل...</p>

  return (
    <div>
      <div className={styles.filterBar}>
        <button className={styles.chipBtn} onClick={onCancel}>‹ رجوع لقائمة الكورسات</button>
      </div>

      <div className={styles.filterBar} style={{ marginBottom: 20 }}>
        <button
          className={styles.chipBtn}
          style={step === 'basics' ? { background: 'var(--primary)', color: 'white' } : undefined}
          onClick={() => setStep('basics')}
        >
          1. الأساسيات
        </button>
        <button
          className={styles.chipBtn}
          style={step === 'curriculum' ? { background: 'var(--primary)', color: 'white' } : undefined}
          disabled={!course}
          onClick={() => course && setStep('curriculum')}
        >
          2. المنهج
        </button>
      </div>

      {step === 'basics' && (
        <BasicsStep
          course={course}
          onSaved={savedCourse => { setCourse(savedCourse); setStep('curriculum') }}
        />
      )}
      {step === 'curriculum' && course && (
        <CurriculumStep course={course} onDone={onDone} />
      )}
    </div>
  )
}
