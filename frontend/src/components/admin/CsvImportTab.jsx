import { useState, useEffect, useRef } from 'react'
import { previewImport, confirmImport, getImportBatches, getImportBatch, getImportTemplate } from '../../api/management'
import styles from '../../pages/AdminPanelPage.module.css'

const STATUS_AR = { pending: 'قيد الانتظار', processing: 'جاري التنفيذ', done: 'مكتمل', failed: 'فشل' }

export default function CsvImportTab() {
  const [file, setFile]         = useState(null)
  const [preview, setPreview]   = useState(null)
  const [previewing, setPreviewing] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const [batch, setBatch]       = useState(null)
  const [batches, setBatches]   = useState([])
  const pollRef = useRef(null)

  function loadBatches() {
    getImportBatches()
      .then(r => r.ok ? r.json() : [])
      .then(d => setBatches(Array.isArray(d) ? d : []))
  }

  useEffect(() => {
    loadBatches()
    return () => clearInterval(pollRef.current)
  }, [])

  async function handleDownloadTemplate() {
    const res = await getImportTemplate()
    if (!res.ok) return
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'import_template.csv'
    a.click()
    URL.revokeObjectURL(url)
  }

  async function handlePreview() {
    if (!file) return
    setPreviewing(true); setPreview(null)
    const fd = new FormData()
    fd.append('file', file)
    const res = await previewImport(fd)
    if (res.ok) setPreview(await res.json())
    setPreviewing(false)
  }

  async function handleConfirm() {
    if (!file) return
    setConfirming(true)
    const fd = new FormData()
    fd.append('file', file)
    const res = await confirmImport(fd)
    if (res.ok) {
      const b = await res.json()
      startPolling(b.id)
    }
    setConfirming(false)
  }

  function startPolling(id) {
    clearInterval(pollRef.current)
    const tick = () => {
      getImportBatch(id)
        .then(r => r.ok ? r.json() : null)
        .then(d => {
          if (!d) return
          setBatch(d)
          if (d.status === 'done' || d.status === 'failed') {
            clearInterval(pollRef.current)
            loadBatches()
          }
        })
    }
    tick()
    pollRef.current = setInterval(tick, 3000)
  }

  const hasErrors = preview && preview.error_count > 0

  return (
    <div>
      <div className={styles.form}>
        <h3 className={styles.formHeading}>استيراد طلاب السنتر عبر CSV</h3>
        <button type="button" className={styles.chipBtn} style={{ alignSelf: 'flex-start' }} onClick={handleDownloadTemplate}>
          تحميل نموذج CSV
        </button>
        <input
          className={styles.input}
          type="file"
          accept=".csv"
          onChange={e => { setFile(e.target.files[0]); setPreview(null); setBatch(null) }}
        />
        <button className={styles.btn} type="button" disabled={!file || previewing} onClick={handlePreview}>
          {previewing ? 'جاري المعاينة...' : 'معاينة'}
        </button>
      </div>

      {preview && (
        <div className={styles.tableWrap}>
          <p className={styles.muted}>
            إجمالي الصفوف: {preview.total_rows} — صحيح: {preview.valid_count} — أخطاء: {preview.error_count}
          </p>
          <table className={styles.table}>
            <thead>
              <tr>
                <th className={styles.th}>الصف</th>
                <th className={styles.th}>الهاتف</th>
                <th className={styles.th}>الحالة</th>
                <th className={styles.th}>الأخطاء</th>
              </tr>
            </thead>
            <tbody>
              {preview.rows.map(r => (
                <tr key={r.row} className={r.status === 'ok' ? styles.rowOk : styles.rowError}>
                  <td className={styles.td}>{r.row}</td>
                  <td className={styles.td} dir="ltr">{r.phone}</td>
                  <td className={styles.td}>{r.status === 'ok' ? 'صحيح' : 'خطأ'}</td>
                  <td className={styles.td}>{r.errors?.join('، ') || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>

          {!hasErrors && !batch && (
            <button className={styles.btn} type="button" disabled={confirming} onClick={handleConfirm}>
              {confirming ? 'جاري بدء الاستيراد...' : 'تأكيد الاستيراد'}
            </button>
          )}
        </div>
      )}

      {batch && (
        <div className={styles.listItem}>
          <div>
            <div className={styles.listTitle}>دفعة #{batch.id} — {STATUS_AR[batch.status] ?? batch.status}</div>
            <div className={styles.listMeta}>
              تم استيراد {batch.imported_count ?? 0} — فشل {batch.failed_count ?? 0} — من إجمالي {batch.total_rows}
            </div>
          </div>
        </div>
      )}

      <h3 className={styles.sectionHeading} style={{ marginTop: 24 }}>الدفعات السابقة</h3>
      <div className={styles.listItems}>
        {batches.map(b => (
          <div key={b.id} className={styles.listItem}>
            <div>
              <div className={styles.listTitle}>دفعة #{b.id} — {STATUS_AR[b.status] ?? b.status}</div>
              <div className={styles.listMeta}>
                استورد {b.imported_count ?? 0} / فشل {b.failed_count ?? 0} من {b.total_rows} — {new Date(b.created_at).toLocaleString('ar-EG')}
              </div>
            </div>
          </div>
        ))}
        {batches.length === 0 && <p className={styles.muted}>لا توجد دفعات سابقة</p>}
      </div>
    </div>
  )
}
