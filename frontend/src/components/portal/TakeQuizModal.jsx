import { useEffect, useState } from 'react'
import { getQuiz, startQuizAttempt, submitQuizAttempt } from '../../api/portal'
import styles from '../../pages/PortalPage.module.css'

export default function TakeQuizModal({ quizId, onClose }) {
  const [quiz, setQuiz] = useState(null)
  const [attempt, setAttempt] = useState(null) // { attempt_id, time_limit }
  const [answers, setAnswers] = useState({})
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    getQuiz(quizId)
      .then(async r => {
        const body = await r.json().catch(() => ({}))
        if (!r.ok) { setError(body.detail || 'تعذّر تحميل الاختبار'); return }
        setQuiz(body)
      })
      .finally(() => setLoading(false))
  }, [quizId])

  async function handleStart() {
    setError('')
    const res = await startQuizAttempt(quizId)
    const body = await res.json().catch(() => ({}))
    if (!res.ok) { setError(body.detail || 'تعذّر بدء الاختبار'); return }
    setAttempt(body)
  }

  async function handleSubmit() {
    setSubmitting(true)
    setError('')
    try {
      const payload = Object.entries(answers).map(([question_id, given_answer]) => ({
        question_id: Number(question_id), given_answer,
      }))
      const res = await submitQuizAttempt(attempt.attempt_id, payload)
      const body = await res.json().catch(() => ({}))
      if (!res.ok) { setError(body.detail || 'تعذّر تسليم الاختبار'); return }
      setResult(body)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className={styles.modalOverlay} onClick={onClose}>
      <div className={styles.modalBox} style={{ background: 'white', color: 'var(--text)', maxHeight: '85vh', overflowY: 'auto' }} onClick={e => e.stopPropagation()}>
        <button className={styles.modalClose} onClick={onClose}>✕</button>

        {loading && <p className={styles.loading}>جارٍ التحميل...</p>}
        {error && <p className={styles.errorRow}>{error}</p>}

        {!loading && quiz && !attempt && !result && (
          <div>
            <h3 className={styles.sectionHeading}>{quiz.title}</h3>
            <p className={styles.courseStatus}>
              {quiz.time_limit ? `الوقت المسموح: ${quiz.time_limit} دقيقة — ` : ''}
              عدد الأسئلة: {quiz.questions.length}
              {quiz.attempts_allowed > 0 ? ` — المحاولات المسموح بها: ${quiz.attempts_allowed}` : ''}
            </p>
            <button className={styles.openBtn} onClick={handleStart}>ابدأ الاختبار</button>
          </div>
        )}

        {attempt && !result && quiz && (
          <div>
            <h3 className={styles.sectionHeading}>{quiz.title}</h3>
            {quiz.questions.map((q, qi) => (
              <div key={q.id} className={styles.formBox} style={{ marginBottom: 12 }}>
                <p className={styles.fieldValue}>{qi + 1}. {q.text}</p>
                {q.choices.map(c => (
                  <label key={c.id} className={styles.formLabel} style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
                    <input
                      type="radio"
                      name={`q-${q.id}`}
                      checked={answers[q.id] === String(q.question_type === 'mcq' ? c.id : c.text)}
                      onChange={() => setAnswers(a => ({ ...a, [q.id]: String(q.question_type === 'mcq' ? c.id : c.text) }))}
                    />
                    {c.text}
                  </label>
                ))}
              </div>
            ))}
            <button className={styles.openBtn} disabled={submitting} onClick={handleSubmit}>
              {submitting ? 'جارٍ التسليم...' : 'تسليم الاختبار'}
            </button>
          </div>
        )}

        {result && (
          <div>
            <h3 className={styles.sectionHeading}>نتيجة الاختبار</h3>
            <p className={styles.walletBalanceInline}>
              الدرجة: {result.earned_marks} / {result.total_marks}
            </p>
            <span className={result.result === 'pass' ? styles.badgeGreen : styles.badgeRed}>
              {result.result === 'pass' ? 'ناجح' : 'راسب'}
            </span>
          </div>
        )}
      </div>
    </div>
  )
}
