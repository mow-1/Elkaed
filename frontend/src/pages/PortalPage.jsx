import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import ResultsTab from '../components/portal/ResultsTab'
import MaterialsTab from '../components/portal/MaterialsTab'
import LessonsTab from '../components/portal/LessonsTab'
import AccountTab from '../components/portal/AccountTab'
import FeedTab from '../components/portal/FeedTab'
import StoreTab from '../components/portal/StoreTab'
import MyCoursesTab from '../components/portal/MyCoursesTab'
import styles from './PortalPage.module.css'

// All tabs are visible regardless of student_type (deliberate — overrides any
// "online only" framing from earlier plan drafts).
const TABS = [
  { id: 'results',   label: 'النتائج' },
  { id: 'materials', label: 'الملفات' },
  { id: 'lessons',   label: 'الدروس' },
  { id: 'revisions', label: 'المراجعات' },
  { id: 'account',   label: 'حسابي' },
  { id: 'feed',      label: 'الجديد' },
  { id: 'store',     label: 'المتجر' },
  { id: 'mycourses', label: 'كورساتي' },
]

export default function PortalPage() {
  const { user, loading } = useAuth()
  const navigate = useNavigate()
  const [tab, setTab] = useState('results')

  useEffect(() => {
    if (!loading && !user) navigate('/login', { replace: true })
  }, [user, loading, navigate])

  if (loading) {
    return (
      <div className={styles.spinnerWrap}>
        <div className={styles.spinner} />
      </div>
    )
  }
  if (!user) return null

  return (
    <div className={styles.page}>
      <h1 className={styles.heading}>بوابة الطالب</h1>

      <div className={styles.tabBar}>
        {TABS.map(t => (
          <button
            key={t.id}
            className={`${styles.tab} ${tab === t.id ? styles.tabActive : ''}`}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className={styles.content}>
        {tab === 'results'   && <ResultsTab />}
        {tab === 'materials' && <MaterialsTab kind="material" />}
        {tab === 'lessons'   && <LessonsTab />}
        {tab === 'revisions' && <MaterialsTab kind="revision" />}
        {tab === 'account'   && <AccountTab />}
        {tab === 'feed'      && <FeedTab />}
        {tab === 'store'     && <StoreTab />}
        {tab === 'mycourses' && <MyCoursesTab />}
      </div>
    </div>
  )
}
