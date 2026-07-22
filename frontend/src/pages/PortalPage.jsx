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
// "online only" framing from earlier plan drafts). Grouped so the tab bar
// reads as "my learning / discover / account" instead of one flat row.
const TAB_GROUPS = [
  {
    tabs: [
      { id: 'mycourses', label: 'كورساتي',   icon: '📚' },
      { id: 'lessons',   label: 'الدروس',    icon: '🎬' },
      { id: 'revisions', label: 'المراجعات', icon: '🔁' },
      { id: 'materials', label: 'الملفات',   icon: '📁' },
      { id: 'results',   label: 'النتائج',   icon: '📝' },
    ],
  },
  {
    tabs: [
      { id: 'feed',  label: 'الجديد', icon: '🆕' },
      { id: 'store', label: 'المتجر', icon: '🛍️' },
    ],
  },
  {
    tabs: [
      { id: 'account', label: 'حسابي', icon: '👤' },
    ],
  },
]

export default function PortalPage() {
  const { user, loading } = useAuth()
  const navigate = useNavigate()
  const [tab, setTab] = useState('mycourses')

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
        {TAB_GROUPS.map((group, gi) => (
          <div key={gi} style={{ display: 'contents' }}>
            {gi > 0 && <span className={styles.tabDivider} />}
            {group.tabs.map(t => (
              <button
                key={t.id}
                className={`${styles.tab} ${tab === t.id ? styles.tabActive : ''}`}
                onClick={() => setTab(t.id)}
              >
                {t.icon} {t.label}
              </button>
            ))}
          </div>
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
