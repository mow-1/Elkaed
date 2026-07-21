import { useState, useEffect } from 'react'
import { getArrears } from '../../api/attendance'
import styles from '../../pages/AdminPanelPage.module.css'

export default function ArrearsTab() {
  const [rows, setRows]       = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getArrears()
      .then(r => r.ok ? r.json() : [])
      .then(d => setRows(Array.isArray(d) ? d : []))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div>
      <h3 className={styles.formHeading}>متأخرات — أرصدة سالبة</h3>
      {loading
        ? <p className={styles.muted}>جاري التحميل...</p>
        : (
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th className={styles.th}>الاسم</th>
                  <th className={styles.th}>الهاتف</th>
                  <th className={styles.th}>المجموعة</th>
                  <th className={styles.th}>الرصيد</th>
                </tr>
              </thead>
              <tbody>
                {rows.map(s => (
                  <tr key={s.id}>
                    <td className={styles.td}>{s.full_name}</td>
                    <td className={styles.td} dir="ltr">{s.phone}</td>
                    <td className={styles.td}>{s.group ?? '—'}</td>
                    <td className={styles.td} style={{ color: '#c0392b', fontWeight: 600 }}>{s.wallet_balance} جنيه</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {rows.length === 0 && <p className={styles.muted}>لا توجد متأخرات حالياً</p>}
          </div>
        )
      }
    </div>
  )
}
