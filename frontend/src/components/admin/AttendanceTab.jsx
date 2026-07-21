import { useState, useEffect } from 'react'
import { getGroups, getSessions, createSession, getChecklist, markAttendance, markAllPresent,
         revokeAccess, resendWhatsapp } from '../../api/attendance'
import styles from '../../pages/AdminPanelPage.module.css'
import local from './AttendanceTab.module.css'

const STATUS_LABELS = { present: 'حاضر', absent: 'غائب', absent_excused: 'غائب بعذر', makeup: 'تعويض' }
const STATUS_KEYS   = ['present', 'absent', 'absent_excused', 'makeup']

export default function AttendanceTab() {
  const [groups, setGroups]           = useState([])
  const [sessions, setSessions]       = useState([])
  const [groupId, setGroupId]         = useState('')
  const [sessionId, setSessionId]     = useState('')
  const [newSession, setNewSession]   = useState({ date: '', title_ar: '' })
  const [creating, setCreating]       = useState(false)
  const [checklist, setChecklist]     = useState([])
  const [loading, setLoading]         = useState(false)
  const [marking, setMarking]         = useState(null)

  useEffect(() => {
    getGroups().then(r => r.ok ? r.json() : []).then(d => setGroups(Array.isArray(d) ? d : (d?.results ?? [])))
    getSessions().then(r => r.ok ? r.json() : []).then(d => setSessions(Array.isArray(d) ? d : (d?.results ?? [])))
  }, [])

  function loadChecklist(id) {
    if (!id) { setChecklist([]); return }
    setLoading(true)
    getChecklist(id)
      .then(r => r.ok ? r.json() : [])
      .then(d => setChecklist(Array.isArray(d) ? d : []))
      .finally(() => setLoading(false))
  }

  useEffect(() => { loadChecklist(sessionId) }, [sessionId])

  const groupSessions = sessions.filter(s => String(s.group) === String(groupId))

  async function handleCreateSession(e) {
    e.preventDefault()
    if (!groupId) return
    setCreating(true)
    const res = await createSession({ group: parseInt(groupId), date: newSession.date, title_ar: newSession.title_ar })
    if (res.ok) {
      const s = await res.json()
      setSessions(prev => [s, ...prev])
      setSessionId(String(s.id))
      setNewSession({ date: '', title_ar: '' })
    }
    setCreating(false)
  }

  async function handleMark(studentId, status) {
    setMarking(studentId)
    const res = await markAttendance(sessionId, studentId, status)
    if (res.ok) {
      const rec = await res.json()
      setChecklist(list => list.map(row =>
        row.student.id === studentId ? { ...row, status: rec.status, record: rec } : row
      ))
    }
    setMarking(null)
  }

  async function handleMarkAllPresent() {
    if (!confirm('تحديد جميع الطلاب حاضرين؟')) return
    const res = await markAllPresent(sessionId)
    if (res.ok) loadChecklist(sessionId)
  }

  async function handleRevokeAccess(recordId) {
    if (!confirm('سحب صلاحية مشاهدة الدرس التعويضي؟')) return
    const res = await revokeAccess(recordId)
    if (res.ok) alert('تم سحب الصلاحية')
  }

  async function handleResendWhatsapp(recordId) {
    const res = await resendWhatsapp(recordId)
    if (res.ok) alert('تم إعادة إرسال رسالة واتساب')
  }

  return (
    <div>
      <div className={styles.filterBar}>
        <select className={styles.select} value={groupId} onChange={e => { setGroupId(e.target.value); setSessionId('') }}>
          <option value="">اختر المجموعة</option>
          {groups.map(g => <option key={g.id} value={g.id}>{g.name_ar} ({g.student_count})</option>)}
        </select>
        <select className={styles.select} value={sessionId} onChange={e => setSessionId(e.target.value)} disabled={!groupId}>
          <option value="">اختر الحصة</option>
          {groupSessions.map(s => <option key={s.id} value={s.id}>{s.title_ar} — {s.date}</option>)}
        </select>
      </div>

      {groupId && (
        <form className={styles.form} onSubmit={handleCreateSession} style={{ maxWidth: 480 }}>
          <h3 className={styles.formHeading}>إنشاء حصة جديدة</h3>
          <input className={styles.input} type="date" value={newSession.date}
            onChange={e => setNewSession(f => ({ ...f, date: e.target.value }))} required />
          <input className={styles.input} placeholder="عنوان الحصة" value={newSession.title_ar}
            onChange={e => setNewSession(f => ({ ...f, title_ar: e.target.value }))} required />
          <button className={styles.btn} type="submit" disabled={creating}>{creating ? 'جاري الإنشاء...' : 'إنشاء الحصة'}</button>
        </form>
      )}

      {sessionId && (
        <>
          <button className={styles.btn} onClick={handleMarkAllPresent} disabled={loading} style={{ marginBottom: 16 }}>
            تحديد الكل حاضر
          </button>

          {loading
            ? <p className={styles.muted}>جاري التحميل...</p>
            : (
              <div className={local.cards}>
                {checklist.map(row => (
                  <div key={row.student.id} className={local.card}>
                    <div className={local.cardInfo}>
                      <span className={local.name}>{row.student.full_name}</span>
                      <span className={local.phone} dir="ltr">{row.student.phone}</span>
                      <span className={styles.chip}>{STATUS_LABELS[row.status] ?? 'لم يتم التحديد'}</span>
                    </div>
                    <div className={local.cardActions}>
                      {STATUS_KEYS.map(k => (
                        <button
                          key={k}
                          className={row.status === k ? local.statusBtnActive : local.statusBtn}
                          disabled={marking === row.student.id}
                          onClick={() => handleMark(row.student.id, k)}
                        >
                          {STATUS_LABELS[k]}
                        </button>
                      ))}
                    </div>
                    {row.status === 'absent' && row.record && (
                      <div className={local.cardActions}>
                        <button className={local.statusBtn} onClick={() => handleRevokeAccess(row.record.id)}>
                          سحب صلاحية الدرس
                        </button>
                        <button className={local.statusBtn} onClick={() => handleResendWhatsapp(row.record.id)}>
                          إعادة إرسال واتساب
                        </button>
                      </div>
                    )}
                  </div>
                ))}
                {checklist.length === 0 && <p className={styles.muted}>لا يوجد طلاب في هذه المجموعة</p>}
              </div>
            )
          }
        </>
      )}
    </div>
  )
}
