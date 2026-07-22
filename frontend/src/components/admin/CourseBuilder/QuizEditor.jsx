import { useState } from 'react'
import { saveTopicQuiz } from '../../../api/courseBuilder'
import styles from '../../../pages/AdminPanelPage.module.css'

const EMPTY_CHOICE = () => ({ text: '', is_correct: false })
const EMPTY_QUESTION = () => ({ text: '', question_type: 'mcq', mark: '1', choices: [EMPTY_CHOICE(), EMPTY_CHOICE()] })

export default function QuizEditor({ topicId, onSaved, onCancel }) {
  const [title, setTitle] = useState('')
  const [timeLimit, setTimeLimit] = useState('')
  const [passMark, setPassMark] = useState('50')
  const [attemptsAllowed, setAttemptsAllowed] = useState('0')
  const [questions, setQuestions] = useState([EMPTY_QUESTION()])
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  function updateQuestion(qi, patch) {
    setQuestions(qs => qs.map((q, i) => i === qi ? { ...q, ...patch } : q))
  }
  function updateChoice(qi, ci, patch) {
    setQuestions(qs => qs.map((q, i) => i === qi
      ? { ...q, choices: q.choices.map((c, j) => j === ci ? { ...c, ...patch } : c) }
      : q))
  }
  function markCorrect(qi, ci) {
    // mcq/tf: exactly one correct choice
    setQuestions(qs => qs.map((q, i) => i === qi
      ? { ...q, choices: q.choices.map((c, j) => ({ ...c, is_correct: j === ci })) }
      : q))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setSaving(true)
    setError('')
    try {
      const res = await saveTopicQuiz(topicId, {
        title, time_limit: timeLimit || null, pass_mark: passMark, attempts_allowed: attemptsAllowed,
        questions: questions.map(q => ({ ...q, mark: q.mark || '1' })),
      })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        setError(JSON.stringify(body))
        return
      }
      onSaved()
    } finally {
      setSaving(false)
    }
  }

  return (
    <form className={styles.form} onSubmit={handleSubmit} style={{ marginTop: 12 }}>
      <label className={styles.inputLabel}>عنوان الاختبار
        <input className={styles.input} value={title} required onChange={e => setTitle(e.target.value)} />
      </label>

      <div className={styles.filterBar}>
        <label className={styles.inputLabel}>الوقت المسموح (دقائق)
          <input className={styles.input} type="number" min="0" value={timeLimit} onChange={e => setTimeLimit(e.target.value)} />
        </label>
        <label className={styles.inputLabel}>درجة النجاح (%)
          <input className={styles.input} type="number" min="0" max="100" value={passMark} onChange={e => setPassMark(e.target.value)} />
        </label>
        <label className={styles.inputLabel}>عدد المحاولات (0 = غير محدود)
          <input className={styles.input} type="number" min="0" value={attemptsAllowed} onChange={e => setAttemptsAllowed(e.target.value)} />
        </label>
      </div>

      {questions.map((q, qi) => (
        <div key={qi} className={styles.panel} style={{ position: 'static', marginBottom: 12 }}>
          <div className={styles.miniRow}>
            <strong>سؤال {qi + 1}</strong>
            {questions.length > 1 && (
              <button type="button" className={styles.chipBtnDanger}
                onClick={() => setQuestions(qs => qs.filter((_, i) => i !== qi))}>حذف السؤال</button>
            )}
          </div>

          <label className={styles.inputLabel}>نص السؤال
            <input className={styles.input} value={q.text} required
              onChange={e => updateQuestion(qi, { text: e.target.value })} />
          </label>

          <div className={styles.filterBar}>
            <label className={styles.inputLabel}>نوع السؤال
              <select className={styles.select} value={q.question_type}
                onChange={e => updateQuestion(qi, { question_type: e.target.value })}>
                <option value="mcq">اختيار متعدد</option>
                <option value="tf">صح أو خطأ</option>
              </select>
            </label>
            <label className={styles.inputLabel}>الدرجة
              <input className={styles.input} type="number" step="0.5" min="0" value={q.mark}
                onChange={e => updateQuestion(qi, { mark: e.target.value })} />
            </label>
          </div>

          <p className={styles.muted}>الاختيارات (اختر الإجابة الصحيحة):</p>
          {q.choices.map((c, ci) => (
            <div key={ci} className={styles.miniRow}>
              <input type="radio" name={`correct-${qi}`} checked={c.is_correct} onChange={() => markCorrect(qi, ci)} />
              <input className={styles.input} value={c.text} required
                onChange={e => updateChoice(qi, ci, { text: e.target.value })} />
              {q.choices.length > 2 && (
                <button type="button" className={styles.chipBtnDanger}
                  onClick={() => updateQuestion(qi, { choices: q.choices.filter((_, j) => j !== ci) })}>حذف</button>
              )}
            </div>
          ))}
          <button type="button" className={styles.chipBtn}
            onClick={() => updateQuestion(qi, { choices: [...q.choices, EMPTY_CHOICE()] })}>+ إضافة اختيار</button>
        </div>
      ))}

      <button type="button" className={styles.chipBtn} onClick={() => setQuestions(qs => [...qs, EMPTY_QUESTION()])}>+ إضافة سؤال</button>

      {error && <p className={styles.errorText}>{error}</p>}

      <div className={styles.filterBar}>
        <button className={styles.btn} type="submit" disabled={saving}>{saving ? 'جارٍ الحفظ...' : 'حفظ الاختبار'}</button>
        <button className={styles.chipBtn} type="button" onClick={onCancel}>إلغاء</button>
      </div>
    </form>
  )
}
