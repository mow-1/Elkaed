import { useState, useEffect, useRef, useCallback } from 'react'
import { Html5Qrcode } from 'html5-qrcode'
import { getGroups, getSessions, getChecklist, scanAttendance, markAttendance, searchSessionStudents } from '../../api/attendance'
import styles from '../../pages/AdminPanelPage.module.css'
import local from './ScanTab.module.css'

const RESULT_STYLES = {
  ok:                  local.cardGreen,
  already_present:     local.cardBlue,
  insufficient_balance: local.cardOrange,
  not_found:           local.cardRed,
  error:               local.cardRed,
  group_mismatch:      local.cardYellow,
}

export default function ScanTab() {
  const [groups, setGroups]     = useState([])
  const [sessions, setSessions] = useState([])
  const [groupId, setGroupId]   = useState('')
  const [sessionId, setSessionId] = useState('')
  const [checklist, setChecklist] = useState([])
  const [result, setResult]     = useState(null) // { kind, data }
  const [cameraOn, setCameraOn] = useState(false)
  const [showUnscanned, setShowUnscanned] = useState(false)
  const [inputVal, setInputVal] = useState('')
  const [query, setQuery]       = useState('')
  const [searchResults, setSearchResults] = useState([])

  const inputRef       = useRef(null)
  const searchInputRef = useRef(null)
  const qrRef          = useRef(null)
  const audioCtxRef    = useRef(null)
  const resultTimerRef = useRef(null)
  const lastTokenRef   = useRef('')
  const searchTimerRef = useRef(null)
  const handleScanRef  = useRef(() => {})

  useEffect(() => {
    getGroups().then(r => r.ok ? r.json() : []).then(d => setGroups(Array.isArray(d) ? d : (d?.results ?? [])))
    getSessions().then(r => r.ok ? r.json() : []).then(d => setSessions(Array.isArray(d) ? d : (d?.results ?? [])))
  }, [])

  const refreshChecklist = useCallback(() => {
    if (!sessionId) return
    getChecklist(sessionId).then(r => r.ok ? r.json() : []).then(d => setChecklist(Array.isArray(d) ? d : []))
  }, [sessionId])

  useEffect(() => {
    refreshChecklist()
    setResult(null)
    setShowUnscanned(false)
    inputRef.current?.focus()
  }, [sessionId, refreshChecklist])

  /* ---------------- audio beeps (single reused AudioContext) ---------------- */
  function playTone(freq, duration) {
    try {
      if (!audioCtxRef.current) audioCtxRef.current = new (window.AudioContext || window.webkitAudioContext)()
      const ctx = audioCtxRef.current
      const osc = ctx.createOscillator()
      const gain = ctx.createGain()
      osc.type = 'sine'
      osc.frequency.value = freq
      gain.gain.value = 0.15
      osc.connect(gain)
      gain.connect(ctx.destination)
      osc.start()
      osc.stop(ctx.currentTime + duration)
    } catch { /* audio not available, ignore */ }
  }
  const beepSuccess = () => playTone(880, 0.15)
  const beepError   = () => { playTone(220, 0.15); setTimeout(() => playTone(220, 0.15), 220) }

  /* ---------------- result card ---------------- */
  function showResult(kind, data, persist = false) {
    clearTimeout(resultTimerRef.current)
    setResult({ kind, data })
    if (!persist) resultTimerRef.current = setTimeout(() => setResult(null), 3000)
  }

  /* ---------------- core scan handler (shared by hardware input + camera) ---------------- */
  async function handleScan(token, resolution) {
    if (!sessionId) { alert('اختر الحصة أولاً'); return }
    const t = (token || '').trim()
    if (!t) return
    lastTokenRef.current = t
    try {
      const res = await scanAttendance({ token: t, session_id: sessionId, resolution })
      const data = await res.json().catch(() => ({}))
      if (res.status === 404) { showResult('not_found', data); beepError() }
      else if (res.status === 409) { showResult('group_mismatch', data, true); beepError() }
      else if (!res.ok) { showResult('error', data); beepError() }
      else if (data.insufficient_balance) { showResult('insufficient_balance', data); beepError() }
      else { showResult(data.result, data); beepSuccess() }
      if (res.ok) refreshChecklist()
    } catch {
      showResult('error', { detail: 'تعذر الاتصال بالخادم' })
      beepError()
    } finally {
      inputRef.current?.focus()
    }
  }
  useEffect(() => { handleScanRef.current = handleScan })

  function handleHardwareSubmit(e) {
    e.preventDefault()
    const token = inputVal
    setInputVal('')
    handleScan(token)
  }

  function handleInputBlur(e) {
    const next = e.relatedTarget
    if (next && (next.tagName === 'SELECT' || next === searchInputRef.current)) return
    setTimeout(() => inputRef.current?.focus(), 50)
  }

  /* ---------------- camera (html5-qrcode) ---------------- */
  useEffect(() => {
    if (!cameraOn) return
    const qr = new Html5Qrcode('qr-reader')
    qrRef.current = qr
    qr.start(
      { facingMode: 'environment' },
      { fps: 10, qrbox: 250 },
      (decodedText) => handleScanRef.current(decodedText),
      () => { /* per-frame scan miss, expected & noisy — ignore */ },
    ).catch(() => setCameraOn(false))

    return () => {
      const q = qrRef.current
      qrRef.current = null
      if (q && q.isScanning) {
        q.stop().then(() => q.clear()).catch(() => {})
      }
    }
  }, [cameraOn])

  /* ---------------- manual search fallback (uses markAttendance by student id, not token) ---------------- */
  useEffect(() => {
    clearTimeout(searchTimerRef.current)
    if (!query.trim() || !sessionId) { setSearchResults([]); return }
    searchTimerRef.current = setTimeout(() => {
      searchSessionStudents(sessionId, query)
        .then(r => r.ok ? r.json() : [])
        .then(d => setSearchResults(Array.isArray(d) ? d : []))
    }, 400)
    return () => clearTimeout(searchTimerRef.current)
  }, [query, sessionId])

  async function handleManualMark(student) {
    const res = await markAttendance(sessionId, student.id, 'present')
    if (res.ok) {
      const rec = await res.json()
      showResult('ok', { student: rec.student })
      beepSuccess()
      refreshChecklist()
      setQuery(''); setSearchResults([])
    } else {
      showResult('error', { detail: 'تعذر تسجيل الحضور' })
      beepError()
    }
    inputRef.current?.focus()
  }

  const groupSessions  = sessions.filter(s => String(s.group) === String(groupId))
  const totalStudents  = checklist.length
  const presentCount   = checklist.filter(r => r.status === 'present' || r.status === 'makeup').length
  const unscanned      = checklist.filter(r => r.status === null)

  return (
    <div>
      <div className={styles.filterBar}>
        <select className={styles.select} value={groupId} onChange={e => { setGroupId(e.target.value); setSessionId('') }}>
          <option value="">اختر المجموعة</option>
          {groups.map(g => <option key={g.id} value={g.id}>{g.name_ar}</option>)}
        </select>
        <select className={styles.select} value={sessionId} onChange={e => setSessionId(e.target.value)} disabled={!groupId}>
          <option value="">اختر الحصة</option>
          {groupSessions.map(s => <option key={s.id} value={s.id}>{s.title_ar} — {s.date}</option>)}
        </select>
      </div>

      {sessionId && (
        <>
          <div className={local.counter}>تم تسجيل {presentCount} من {totalStudents}</div>

          {/* Hidden hardware scanner input — always focused, "types" token + Enter */}
          <form onSubmit={handleHardwareSubmit} className={local.hiddenForm}>
            <input
              ref={inputRef}
              className={local.hiddenInput}
              value={inputVal}
              onChange={e => setInputVal(e.target.value)}
              onBlur={handleInputBlur}
              autoFocus
              aria-label="ماسح الحضور"
            />
          </form>

          <button
            type="button"
            className={styles.btn}
            onClick={() => setCameraOn(v => !v)}
            style={{ marginBottom: 12 }}
          >
            {cameraOn ? 'إيقاف الكاميرا' : 'تفعيل الكاميرا'}
          </button>

          {cameraOn && <div id="qr-reader" className={local.qrReader} />}

          {result && (
            <div className={`${local.resultCard} ${RESULT_STYLES[result.kind] ?? local.cardRed}`}>
              {result.kind === 'ok' && (
                <>
                  <div className={local.resultTitle}>تم تسجيل الحضور</div>
                  <div>{result.data.student?.full_name}</div>
                  {result.data.wallet_balance != null && <div>الرصيد: {result.data.wallet_balance} جنيه</div>}
                </>
              )}
              {result.kind === 'already_present' && (
                <>
                  <div className={local.resultTitle}>تم تسجيله من قبل</div>
                  <div>{result.data.student?.full_name}</div>
                  {result.data.wallet_balance != null && <div>الرصيد: {result.data.wallet_balance} جنيه</div>}
                </>
              )}
              {result.kind === 'insufficient_balance' && (
                <>
                  <div className={local.resultTitle}>الرصيد غير كافٍ — لم يتم الخصم</div>
                  <div>{result.data.student?.full_name}</div>
                  <div>الرصيد: {result.data.wallet_balance} جنيه</div>
                </>
              )}
              {result.kind === 'not_found' && (
                <div className={local.resultTitle}>{result.data.detail ?? 'الكود غير موجود'}</div>
              )}
              {result.kind === 'error' && (
                <div className={local.resultTitle}>{result.data.detail ?? 'حدث خطأ'}</div>
              )}
              {result.kind === 'group_mismatch' && (
                <>
                  <div className={local.resultTitle}>{result.data.student?.full_name} — ليس في هذه المجموعة</div>
                  <div>مجموعة الطالب: {result.data.student?.group ?? '—'}</div>
                  <div className={local.resultActions}>
                    <button className={styles.btn} onClick={() => handleScan(lastTokenRef.current, 'makeup')}>تسجيل كتعويض</button>
                    <button className={styles.btn} onClick={() => handleScan(lastTokenRef.current, 'add_anyway')}>تسجيل حضور بأي حال</button>
                  </div>
                </>
              )}
            </div>
          )}

          <div className={local.searchBox}>
            <input
              ref={searchInputRef}
              className={styles.input}
              placeholder="بحث بالاسم أو رقم الهاتف (نسيان البطاقة)..."
              value={query}
              onChange={e => setQuery(e.target.value)}
            />
            {searchResults.length > 0 && (
              <div className={local.searchResults}>
                {searchResults.map(s => (
                  <div key={s.id} className={local.searchRow}>
                    <span>{s.full_name} <span dir="ltr" className={local.phone}>({s.phone})</span></span>
                    <button className={styles.chipBtn} onClick={() => handleManualMark(s)}>تسجيل حضور</button>
                  </div>
                ))}
              </div>
            )}
          </div>

          <button className={styles.chipBtn} onClick={() => setShowUnscanned(v => !v)} style={{ marginTop: 16 }}>
            غير ممسوحين ({unscanned.length}) {showUnscanned ? '▲' : '▼'}
          </button>
          {showUnscanned && (
            <div className={local.unscannedList}>
              {unscanned.map(r => (
                <div key={r.student.id} className={local.unscannedRow}>
                  {r.student.full_name} — <span dir="ltr">{r.student.phone}</span>
                </div>
              ))}
              {unscanned.length === 0 && <p className={styles.muted}>الجميع تم مسحهم</p>}
            </div>
          )}
        </>
      )}
    </div>
  )
}
