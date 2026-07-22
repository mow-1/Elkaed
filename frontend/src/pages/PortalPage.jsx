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
import DashboardShell from '../components/DashboardShell'
import styles from './PortalPage.module.css'

// All tabs are visible regardless of student_type (deliberate — overrides any
// "online only" framing from earlier plan drafts). Grouped so the sidebar
// reads as "my learning / discover / account" instead of one flat list.
const TAB_SECTIONS = [
  {
    label: 'التعلّم',
    items: [
      { id: 'mycourses', label: 'كورساتي',   icon: '📚' },
      { id: 'lessons',   label: 'الدروس',    icon: '🎬' },
      { id: 'revisions', label: 'المراجعات', icon: '🔁' },
      { id: 'materials', label: 'الملفات',   icon: '📁' },
      { id: 'results',   label: 'النتائج',   icon: '📝' },
    ],
  },
  {
    label: 'اكتشف',
    items: [
      { id: 'feed',  label: 'الجديد', icon: '🆕' },
      { id: 'store', label: 'المتجر', icon: '🛍️' },
    ],
  },
  {
    label: 'الحساب',
    items: [
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
    <DashboardShell title="بوابة الطالب" sections={TAB_SECTIONS} activeId={tab} onSelect={setTab}>
      {tab === 'results'   && <ResultsTab />}
      {tab === 'materials' && <MaterialsTab kind="material" />}
      {tab === 'lessons'   && <LessonsTab />}
      {tab === 'revisions' && <MaterialsTab kind="revision" />}
      {tab === 'account'   && <AccountTab />}
      {tab === 'feed'      && <FeedTab />}
      {tab === 'store'     && <StoreTab />}
      {tab === 'mycourses' && <MyCoursesTab />}
    </DashboardShell>
  )
}
