import { useState, useEffect } from 'react'
import { getRevenueReport } from '../../api/attendance'
import styles from '../../pages/AdminPanelPage.module.css'

export default function RevenueReportTab() {
  const [granularity, setGranularity] = useState('day')
  const [rows, setRows]               = useState([])
  const [loading, setLoading]         = useState(true)

  useEffect(() => {
    setLoading(true)
    getRevenueReport(granularity)
      .then(r => r.ok ? r.json() : [])
      .then(d => setRows(Array.isArray(d) ? d : []))
      .finally(() => setLoading(false))
  }, [granularity])

  return (
    <div>
      <div className={styles.filterBar}>
        <select className={styles.select} value={granularity} onChange={e => setGranularity(e.target.value)}>
          <option value="day">يومي</option>
          <option value="week">أسبوعي</option>
          <option value="month">شهري</option>
        </select>
      </div>

      {loading
        ? <p className={styles.muted}>جاري التحميل...</p>
        : (
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th className={styles.th}>الفترة</th>
                  <th className={styles.th}>إجمالي حضوري</th>
                  <th className={styles.th}>خصومات حضوري</th>
                  <th className={styles.th}>صافي حضوري</th>
                  <th className={styles.th}>إجمالي أونلاين</th>
                  <th className={styles.th}>خصومات أونلاين</th>
                  <th className={styles.th}>صافي أونلاين</th>
                  <th className={styles.th}>مبالغ مستردة</th>
                </tr>
              </thead>
              <tbody>
                {rows.map(r => (
                  <tr key={r.period}>
                    <td className={styles.td}>{new Date(r.period).toLocaleDateString('ar-EG')}</td>
                    <td className={styles.td}>{r.physical.gross}</td>
                    <td className={styles.td}>{r.physical.discounts}</td>
                    <td className={styles.td}>{r.physical.net}</td>
                    <td className={styles.td}>{r.online.gross}</td>
                    <td className={styles.td}>{r.online.discounts}</td>
                    <td className={styles.td}>{r.online.net}</td>
                    <td className={styles.td}>{r.refunds}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {rows.length === 0 && <p className={styles.muted}>لا توجد بيانات إيرادات بعد</p>}
          </div>
        )
      }
    </div>
  )
}
