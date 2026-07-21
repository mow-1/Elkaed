import { useState, useEffect } from 'react'
import { getAuditLogs } from '../../api/audit'
import styles from '../../pages/AdminPanelPage.module.css'

const ACTION_LABELS = {
  created:             'إنشاء',
  updated:             'تعديل',
  deleted:             'حذف',
  overridden:          'تجاوز',
  refunded:            'استرداد',
  discount_granted:    'منح خصم',
  discount_revoked:    'سحب خصم',
  attendance_changed:  'تعديل حضور',
  csv_imported:        'استيراد CSV',
  access_granted:      'منح صلاحية',
  access_revoked:      'سحب صلاحية',
  debited:             'خصم من المحفظة',
  credited:            'إيداع في المحفظة',
}

function pageFromUrl(url) {
  if (!url) return null
  try { return new URL(url).searchParams.get('page') } catch { return null }
}

export default function ActivityLogTab() {
  const [actor, setActor]     = useState('')
  const [action, setAction]   = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo]   = useState('')
  const [page, setPage]       = useState(null)
  const [data, setData]       = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setLoading(true)
    const params = {}
    if (actor)    params.actor = actor
    if (action)   params.action = action
    if (dateFrom) params.created_at__gte = dateFrom
    if (dateTo)   params.created_at__lte = dateTo
    if (page)     params.page = page
    getAuditLogs(params)
      .then(r => r.ok ? r.json() : null)
      .then(d => { if (d) setData(d) })
      .finally(() => setLoading(false))
  }, [actor, action, dateFrom, dateTo, page])

  return (
    <div>
      <div className={styles.filterBar}>
        <input
          className={styles.input}
          placeholder="معرّف الفاعل (ID)"
          value={actor}
          onChange={e => { setActor(e.target.value); setPage(null) }}
        />
        <select className={styles.select} value={action} onChange={e => { setAction(e.target.value); setPage(null) }}>
          <option value="">كل العمليات</option>
          {Object.entries(ACTION_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <input className={styles.input} type="date" value={dateFrom} onChange={e => { setDateFrom(e.target.value); setPage(null) }} />
        <input className={styles.input} type="date" value={dateTo} onChange={e => { setDateTo(e.target.value); setPage(null) }} />
      </div>

      {loading
        ? <p className={styles.muted}>جاري التحميل...</p>
        : data && (
          <>
            <p className={styles.muted}>{data.count} عملية</p>
            <div className={styles.tableWrap}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th className={styles.th}>التاريخ</th>
                    <th className={styles.th}>الفاعل</th>
                    <th className={styles.th}>العملية</th>
                    <th className={styles.th}>الهدف</th>
                    <th className={styles.th}>ملاحظة</th>
                  </tr>
                </thead>
                <tbody>
                  {data.results.map(log => (
                    <tr key={log.id} className={styles.td}>
                      <td className={styles.td}>{new Date(log.created_at).toLocaleString('ar-EG')}</td>
                      <td className={styles.td}>{log.actor ? `${log.actor.full_name} (${log.actor.phone})` : '—'}</td>
                      <td className={styles.td}><span className={styles.chip}>{ACTION_LABELS[log.action] ?? log.action}</span></td>
                      <td className={styles.td}>{log.target_repr ?? '—'}</td>
                      <td className={styles.td}>{log.note || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {data.results.length === 0 && <p className={styles.muted}>لا توجد عمليات مطابقة</p>}
            </div>
            <div className={styles.pagination}>
              <button className={styles.pageBtn} disabled={!data.previous} onClick={() => setPage(pageFromUrl(data.previous) ?? null)}>السابق</button>
              <button className={styles.pageBtn} disabled={!data.next} onClick={() => setPage(pageFromUrl(data.next))}>التالي</button>
            </div>
          </>
        )
      }
    </div>
  )
}
