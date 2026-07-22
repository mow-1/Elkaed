import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import {
  getCustomers, getCustomerDetail, getAdminAnalytics,
  getAdminBanners, createBanner, deleteBanner, toggleBanner,
  getAdminFlashSales, createFlashSale, deleteFlashSale,
  getAdminBundles, createBundle, deleteBundle,
  getCampaigns, createCampaign, sendCampaign, getAllCourses,
  resetCustomerPassword,
} from '../api/management'
import ActivityLogTab from '../components/admin/ActivityLogTab'
import PricingSettingsTab from '../components/admin/PricingSettingsTab'
import DiscountsTab from '../components/admin/DiscountsTab'
import CsvImportTab from '../components/admin/CsvImportTab'
import AttendanceTab from '../components/admin/AttendanceTab'
import GroupsTab from '../components/admin/GroupsTab'
import ScanTab from '../components/admin/ScanTab'
import ArrearsTab from '../components/admin/ArrearsTab'
import RevenueReportTab from '../components/admin/RevenueReportTab'
import MaterialsAdminTab from '../components/admin/MaterialsAdminTab'
import styles from './AdminPanelPage.module.css'

const BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

const ADMIN_TABS = [
  { id: 'customers', label: 'العملاء' },
  { id: 'analytics', label: 'الإحصائيات' },
  { id: 'banners', label: 'البانرات' },
  { id: 'offers', label: 'العروض' },
  { id: 'campaigns', label: 'الحملات' },
  { id: 'activity', label: 'سجل العمليات' },
  { id: 'pricing', label: 'إعدادات التسعير' },
  { id: 'discounts', label: 'خصومات الطلاب' },
  { id: 'import', label: 'استيراد طلاب السنتر' },
  { id: 'groups', label: 'مجاميع السنتر' },
  { id: 'attendance', label: 'الحضور' },
  { id: 'scan', label: 'مسح الحضور' },
  { id: 'arrears', label: 'متأخرات' },
  { id: 'revenue', label: 'تقرير الإيرادات' },
  { id: 'materials', label: 'الملفات والمراجعات' },
]

const ASSISTANT_TABS = [
  { id: 'import', label: 'استيراد طلاب السنتر' },
  { id: 'attendance', label: 'الحضور' },
  { id: 'scan', label: 'مسح الحضور' },
]

const YEAR_LABELS = { '1st': 'أول ثانوي', '2nd': 'ثاني ثانوي', '3rd': 'ثالث ثانوي' }
const SEGMENT_LABELS = { all: 'الكل', students: 'الطلاب', center: 'السنتر', online: 'الأونلاين', '1st': 'أول ثانوي', '2nd': 'ثاني ثانوي', '3rd': 'ثالث ثانوي' }
const STATUS_AR = { draft: 'مسودة', sending: 'جاري الإرسال', done: 'مكتمل' }

export default function AdminPanelPage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [tab, setTab] = useState('customers')

  useEffect(() => {
    if (user && !['admin', 'staff', 'assistant'].includes(user.role)) navigate('/')
  }, [user, navigate])

  useEffect(() => {
    if (user?.role === 'assistant') setTab('import')
  }, [user])

  if (!user || !['admin', 'staff', 'assistant'].includes(user.role)) return null

  const TABS = user.role === 'assistant' ? ASSISTANT_TABS : ADMIN_TABS

  return (
    <div className={styles.page}>
      <h1 className={styles.heading}>لوحة الإدارة</h1>
      <div className={styles.tabBar}>
        {TABS.map(t => (
          <button
            key={t.id}
            className={`${styles.tab} ${tab === t.id ? styles.activeTab : ''}`}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>
      <div className={styles.content}>
        {tab === 'customers'  && <CustomersTab />}
        {tab === 'analytics'  && <AnalyticsTab />}
        {tab === 'banners'    && <BannersTab />}
        {tab === 'offers'     && <OffersTab />}
        {tab === 'campaigns'  && <CampaignsTab />}
        {tab === 'activity'   && <ActivityLogTab />}
        {tab === 'pricing'    && <PricingSettingsTab />}
        {tab === 'discounts'  && <DiscountsTab />}
        {tab === 'import'     && <CsvImportTab />}
        {tab === 'groups'     && <GroupsTab />}
        {tab === 'attendance' && <AttendanceTab />}
        {tab === 'scan'       && <ScanTab />}
        {tab === 'arrears'    && <ArrearsTab />}
        {tab === 'revenue'    && <RevenueReportTab />}
        {tab === 'materials'  && <MaterialsAdminTab />}
      </div>
    </div>
  )
}

/* ------------------------------------------------------------------ */
/* Customers Tab                                                         */
/* ------------------------------------------------------------------ */
function CustomersTab() {
  const [search, setSearch]         = useState('')
  const [year, setYear]             = useState('')
  const [type, setType]             = useState('')
  const [page, setPage]             = useState(1)
  const [data, setData]             = useState(null)
  const [loading, setLoading]       = useState(false)
  const [detail, setDetail]         = useState(null)
  const [detailLoading, setDL]      = useState(false)

  useEffect(() => {
    setLoading(true)
    const params = { page }
    if (search) params.search = search
    if (year)   params.year   = year
    if (type)   params.type   = type
    getCustomers(params)
      .then(r => r.ok ? r.json() : null)
      .then(d => { if (d) setData(d) })
      .finally(() => setLoading(false))
  }, [search, year, type, page])

  function openDetail(id) {
    setDetail({})
    setDL(true)
    getCustomerDetail(id)
      .then(r => r.ok ? r.json() : null)
      .then(d => { if (d) setDetail(d) })
      .finally(() => setDL(false))
  }

  async function handleResetPassword(id) {
    if (!confirm('إعادة تعيين كلمة المرور وإرسالها عبر واتساب؟')) return
    const res = await resetCustomerPassword(id)
    const d = await res.json().catch(() => null)
    alert(d?.detail ?? (res.ok ? 'تم بنجاح' : 'حدث خطأ'))
  }

  return (
    <div>
      <div className={styles.filterBar}>
        <input
          className={styles.input}
          placeholder="بحث باسم أو رقم هاتف..."
          value={search}
          onChange={e => { setSearch(e.target.value); setPage(1) }}
        />
        <select className={styles.select} value={year} onChange={e => { setYear(e.target.value); setPage(1) }}>
          <option value="">كل الصفوف</option>
          <option value="1st">أول ثانوي</option>
          <option value="2nd">ثاني ثانوي</option>
          <option value="3rd">ثالث ثانوي</option>
        </select>
        <select className={styles.select} value={type} onChange={e => { setType(e.target.value); setPage(1) }}>
          <option value="">كل الأنواع</option>
          <option value="center">سنتر</option>
          <option value="online">أونلاين</option>
        </select>
      </div>

      {loading
        ? <p className={styles.muted}>جاري التحميل...</p>
        : data && (
          <>
            <p className={styles.muted}>{data.count} طالب</p>
            <div className={styles.tableWrap}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th className={styles.th}>الاسم</th>
                    <th className={styles.th}>الهاتف</th>
                    <th className={styles.th}>الصف</th>
                    <th className={styles.th}>النوع</th>
                    <th className={styles.th}>الكورسات</th>
                    <th className={styles.th}>تاريخ التسجيل</th>
                  </tr>
                </thead>
                <tbody>
                  {data.results.map(c => (
                    <tr key={c.id} className={styles.tr} onClick={() => openDetail(c.id)}>
                      <td className={styles.td}>{c.full_name}</td>
                      <td className={styles.td} dir="ltr">{c.phone}</td>
                      <td className={styles.td}>{YEAR_LABELS[c.academic_year] ?? c.academic_year}</td>
                      <td className={styles.td}>{c.student_type === 'center' ? 'سنتر' : 'أونلاين'}</td>
                      <td className={styles.td}>{c.enrollment_count}</td>
                      <td className={styles.td}>{new Date(c.date_joined).toLocaleDateString('ar-EG')}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className={styles.pagination}>
              <button className={styles.pageBtn} disabled={page <= 1} onClick={() => setPage(p => p - 1)}>السابق</button>
              <span className={styles.muted}>صفحة {page} من {Math.ceil(data.count / data.per_page) || 1}</span>
              <button className={styles.pageBtn} disabled={page * data.per_page >= data.count} onClick={() => setPage(p => p + 1)}>التالي</button>
            </div>
          </>
        )
      }

      {detail !== null && (
        <>
          <div className={styles.overlay} onClick={() => setDetail(null)} />
          <div className={styles.panel}>
            <button className={styles.panelClose} onClick={() => setDetail(null)}>✕</button>
            {detailLoading
              ? <p className={styles.muted}>جاري التحميل...</p>
              : <>
                  <h2 className={styles.panelHeading}>{detail.full_name}</h2>
                  {[
                    ['الهاتف', <span dir="ltr">{detail.phone}</span>],
                    ['البريد', detail.email || '—'],
                    ['الصف', YEAR_LABELS[detail.academic_year] ?? detail.academic_year],
                    ['النوع', detail.student_type === 'center' ? 'سنتر' : 'أونلاين'],
                    ['المحفظة', `${detail.wallet_balance} جنيه`],
                    ['الدور', detail.role],
                    ['الحالة', detail.is_active ? 'نشط' : 'موقوف'],
                  ].map(([label, val]) => (
                    <p key={label} className={styles.detailRow}>
                      <span>{label}</span><span>{val}</span>
                    </p>
                  ))}

                  <button className={styles.chipBtn} onClick={() => handleResetPassword(detail.id)}>
                    إعادة تعيين كلمة المرور
                  </button>

                  <h3 className={styles.panelSub}>الكورسات ({detail.enrollments?.length ?? 0})</h3>
                  {detail.enrollments?.map(e => (
                    <div key={e.id} className={styles.miniRow}>
                      <span>{e.course__title}</span>
                      <span className={styles.chip}>{e.status}</span>
                    </div>
                  ))}

                  <h3 className={styles.panelSub}>الطلبات ({detail.orders?.length ?? 0})</h3>
                  {detail.orders?.map(o => (
                    <div key={o.id} className={styles.miniRow}>
                      <span>#{o.id} — {o.total_price} جنيه</span>
                      <span className={styles.chip}>{o.status}</span>
                    </div>
                  ))}
                </>
            }
          </div>
        </>
      )}
    </div>
  )
}

/* ------------------------------------------------------------------ */
/* Analytics Tab                                                         */
/* ------------------------------------------------------------------ */
function AnalyticsTab() {
  const [data, setData]     = useState(null)
  const [loading, setLoad]  = useState(true)

  useEffect(() => {
    getAdminAnalytics()
      .then(r => r.ok ? r.json() : null)
      .then(d => { if (d) setData(d) })
      .finally(() => setLoad(false))
  }, [])

  if (loading) return <p className={styles.muted}>جاري التحميل...</p>
  if (!data)   return <p className={styles.muted}>خطأ في تحميل الإحصائيات</p>

  return (
    <div>
      <div className={styles.statsGrid}>
        <div className={styles.statCard}>
          <div className={styles.statNum}>{data.total_students?.toLocaleString('ar-EG')}</div>
          <div className={styles.statLabel}>إجمالي الطلاب</div>
        </div>
        <div className={styles.statCard}>
          <div className={styles.statNum}>{Number(data.total_revenue_egp).toLocaleString('ar-EG')} ج</div>
          <div className={styles.statLabel}>إجمالي الإيرادات</div>
        </div>
        <div className={styles.statCard}>
          <div className={styles.statNum}>{data.active_enrollments?.toLocaleString('ar-EG')}</div>
          <div className={styles.statLabel}>التسجيلات النشطة</div>
        </div>
      </div>

      <div className={styles.analyticsGrid}>
        <div className={styles.analyticsCard}>
          <h3 className={styles.analyticsSub}>نوع الطالب</h3>
          {Object.entries(data.by_student_type ?? {}).map(([k, v]) => (
            <div key={k} className={styles.barRow}>
              <span>{k === 'center' ? 'سنتر' : 'أونلاين'}</span>
              <span className={styles.barCount}>{v}</span>
            </div>
          ))}
        </div>
        <div className={styles.analyticsCard}>
          <h3 className={styles.analyticsSub}>الصف الدراسي</h3>
          {Object.entries(data.by_academic_year ?? {}).map(([k, v]) => (
            <div key={k} className={styles.barRow}>
              <span>{YEAR_LABELS[k] ?? k}</span>
              <span className={styles.barCount}>{v}</span>
            </div>
          ))}
        </div>
        <div className={styles.analyticsCard}>
          <h3 className={styles.analyticsSub}>أكثر الكورسات تسجيلاً</h3>
          {(data.top_courses ?? []).map((c, i) => (
            <div key={i} className={styles.barRow}>
              <span>{c.course__title}</span>
              <span className={styles.barCount}>{c.count}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

/* ------------------------------------------------------------------ */
/* Banners Tab                                                           */
/* ------------------------------------------------------------------ */
function BannersTab() {
  const [banners, setBanners] = useState([])
  const [loading, setLoad]    = useState(true)
  const [form, setForm]       = useState({ title_ar: '', title_en: '', link_url: '' })
  const [file, setFile]       = useState(null)
  const [saving, setSaving]   = useState(false)

  useEffect(() => {
    getAdminBanners()
      .then(r => r.ok ? r.json() : [])
      .then(d => setBanners(Array.isArray(d) ? d : []))
      .finally(() => setLoad(false))
  }, [])

  async function handleCreate(e) {
    e.preventDefault()
    if (!file) return
    setSaving(true)
    const fd = new FormData()
    fd.append('image', file)
    fd.append('title_ar', form.title_ar)
    if (form.title_en) fd.append('title_en', form.title_en)
    if (form.link_url) fd.append('link_url', form.link_url)
    const res = await createBanner(fd)
    if (res.ok) {
      const nb = await res.json()
      setBanners(b => [...b, nb])
      setForm({ title_ar: '', title_en: '', link_url: '' })
      setFile(null)
      e.target.reset()
    }
    setSaving(false)
  }

  async function handleDelete(id) {
    if (!confirm('حذف البانر؟')) return
    await deleteBanner(id)
    setBanners(b => b.filter(x => x.id !== id))
  }

  async function handleToggle(id, is_active) {
    await toggleBanner(id, !is_active)
    setBanners(b => b.map(x => x.id === id ? { ...x, is_active: !is_active } : x))
  }

  if (loading) return <p className={styles.muted}>جاري التحميل...</p>

  return (
    <div>
      <form className={styles.form} onSubmit={handleCreate}>
        <h3 className={styles.formHeading}>إضافة بانر جديد</h3>
        <input type="file" accept="image/*" className={styles.input} onChange={e => setFile(e.target.files[0])} required />
        <input className={styles.input} placeholder="العنوان بالعربي *" value={form.title_ar} onChange={e => setForm(f => ({ ...f, title_ar: e.target.value }))} required />
        <input className={styles.input} placeholder="العنوان بالإنجليزي" value={form.title_en} onChange={e => setForm(f => ({ ...f, title_en: e.target.value }))} />
        <input className={styles.input} placeholder="رابط الانتقال عند النقر (اختياري)" value={form.link_url} onChange={e => setForm(f => ({ ...f, link_url: e.target.value }))} />
        <button className={styles.btn} type="submit" disabled={saving}>{saving ? 'جاري الرفع...' : 'رفع البانر'}</button>
      </form>

      <div className={styles.bannersGrid}>
        {banners.map(b => (
          <div key={b.id} className={`${styles.bannerCard} ${!b.is_active ? styles.bannerInactive : ''}`}>
            <img
              src={b.image?.startsWith('http') ? b.image : `${BASE}${b.image}`}
              alt={b.title_ar}
              className={styles.bannerImg}
            />
            <div className={styles.bannerInfo}>
              <span className={styles.bannerTitle}>{b.title_ar}</span>
              <div className={styles.bannerActions}>
                <button className={styles.chipBtn} onClick={() => handleToggle(b.id, b.is_active)}>
                  {b.is_active ? 'إخفاء' : 'إظهار'}
                </button>
                <button className={styles.chipBtnDanger} onClick={() => handleDelete(b.id)}>حذف</button>
              </div>
            </div>
          </div>
        ))}
        {banners.length === 0 && <p className={styles.muted}>لا توجد بانرات حتى الآن</p>}
      </div>
    </div>
  )
}

/* ------------------------------------------------------------------ */
/* Offers Tab (Flash Sales + Bundles)                                    */
/* ------------------------------------------------------------------ */
function OffersTab() {
  const [flashSales, setFlashSales] = useState([])
  const [bundles, setBundles]       = useState([])
  const [courses, setCourses]       = useState([])
  const [loading, setLoad]          = useState(true)
  const [fsForm, setFsForm]         = useState({ course: '', discount_pct: '', starts_at: '', ends_at: '' })
  const [bdForm, setBdForm]         = useState({ title: '', price: '', course_ids: [] })
  const [saving, setSaving]         = useState(false)

  useEffect(() => {
    Promise.all([
      getAdminFlashSales().then(r => r.ok ? r.json() : []),
      getAdminBundles().then(r => r.ok ? r.json() : []),
      getAllCourses().then(r => r.ok ? r.json() : []),
    ]).then(([fs, bd, co]) => {
      setFlashSales(Array.isArray(fs) ? fs : [])
      setBundles(Array.isArray(bd) ? bd : [])
      const list = Array.isArray(co) ? co : (co?.results ?? [])
      setCourses(list)
    }).finally(() => setLoad(false))
  }, [])

  async function handleCreateFlashSale(e) {
    e.preventDefault()
    setSaving(true)
    const res = await createFlashSale({
      course:       parseInt(fsForm.course),
      discount_pct: parseFloat(fsForm.discount_pct),
      starts_at:    fsForm.starts_at,
      ends_at:      fsForm.ends_at,
    })
    if (res.ok) {
      const nfs = await res.json()
      setFlashSales(f => [nfs, ...f])
      setFsForm({ course: '', discount_pct: '', starts_at: '', ends_at: '' })
    }
    setSaving(false)
  }

  async function handleDeleteFlashSale(id) {
    if (!confirm('حذف العرض؟')) return
    await deleteFlashSale(id)
    setFlashSales(f => f.filter(x => x.id !== id))
  }

  async function handleCreateBundle(e) {
    e.preventDefault()
    setSaving(true)
    const res = await createBundle({
      title:      bdForm.title,
      price:      parseFloat(bdForm.price),
      course_ids: bdForm.course_ids.map(Number),
    })
    if (res.ok) {
      const nb = await res.json()
      setBundles(b => [nb, ...b])
      setBdForm({ title: '', price: '', course_ids: [] })
    }
    setSaving(false)
  }

  async function handleDeleteBundle(id) {
    if (!confirm('حذف الباقة؟')) return
    await deleteBundle(id)
    setBundles(b => b.filter(x => x.id !== id))
  }

  function toggleCourse(id) {
    setBdForm(f => ({
      ...f,
      course_ids: f.course_ids.includes(id)
        ? f.course_ids.filter(x => x !== id)
        : [...f.course_ids, id],
    }))
  }

  if (loading) return <p className={styles.muted}>جاري التحميل...</p>

  return (
    <div className={styles.offersGrid}>
      {/* Flash Sales */}
      <section>
        <h2 className={styles.sectionHeading}>العروض المؤقتة</h2>
        <form className={styles.form} onSubmit={handleCreateFlashSale}>
          <select className={styles.select} value={fsForm.course} onChange={e => setFsForm(f => ({ ...f, course: e.target.value }))} required>
            <option value="">اختر الكورس</option>
            {courses.map(c => <option key={c.id} value={c.id}>{c.title}</option>)}
          </select>
          <input className={styles.input} type="number" placeholder="نسبة الخصم %" min="1" max="100" step="0.01"
            value={fsForm.discount_pct} onChange={e => setFsForm(f => ({ ...f, discount_pct: e.target.value }))} required />
          <label className={styles.inputLabel}>من</label>
          <input className={styles.input} type="datetime-local"
            value={fsForm.starts_at} onChange={e => setFsForm(f => ({ ...f, starts_at: e.target.value }))} required />
          <label className={styles.inputLabel}>إلى</label>
          <input className={styles.input} type="datetime-local"
            value={fsForm.ends_at} onChange={e => setFsForm(f => ({ ...f, ends_at: e.target.value }))} required />
          <button className={styles.btn} type="submit" disabled={saving}>إضافة عرض</button>
        </form>

        <div className={styles.listItems}>
          {flashSales.map(fs => (
            <div key={fs.id} className={styles.listItem}>
              <div>
                <div className={styles.listTitle}>{fs.course_title}</div>
                <div className={styles.listMeta}>خصم {fs.discount_pct}% — {fs.sale_price} ج (كان {fs.original_price} ج)</div>
              </div>
              <button className={styles.chipBtnDanger} onClick={() => handleDeleteFlashSale(fs.id)}>حذف</button>
            </div>
          ))}
          {flashSales.length === 0 && <p className={styles.muted}>لا توجد عروض</p>}
        </div>
      </section>

      {/* Bundles */}
      <section>
        <h2 className={styles.sectionHeading}>الباقات</h2>
        <form className={styles.form} onSubmit={handleCreateBundle}>
          <input className={styles.input} placeholder="اسم الباقة" value={bdForm.title}
            onChange={e => setBdForm(f => ({ ...f, title: e.target.value }))} required />
          <input className={styles.input} type="number" placeholder="السعر بالجنيه" value={bdForm.price}
            onChange={e => setBdForm(f => ({ ...f, price: e.target.value }))} required />
          <div className={styles.courseCheckList}>
            <p className={styles.muted}>اختر الكورسات ({bdForm.course_ids.length} محددة):</p>
            {courses.map(c => (
              <label key={c.id} className={styles.checkRow}>
                <input type="checkbox" checked={bdForm.course_ids.includes(c.id)} onChange={() => toggleCourse(c.id)} />
                {c.title}
              </label>
            ))}
          </div>
          <button className={styles.btn} type="submit" disabled={saving || bdForm.course_ids.length === 0}>إنشاء باقة</button>
        </form>

        <div className={styles.listItems}>
          {bundles.map(b => (
            <div key={b.id} className={styles.listItem}>
              <div>
                <div className={styles.listTitle}>{b.title}</div>
                <div className={styles.listMeta}>{b.price} جنيه — {b.courses?.length ?? 0} كورس</div>
              </div>
              <button className={styles.chipBtnDanger} onClick={() => handleDeleteBundle(b.id)}>حذف</button>
            </div>
          ))}
          {bundles.length === 0 && <p className={styles.muted}>لا توجد باقات</p>}
        </div>
      </section>
    </div>
  )
}

/* ------------------------------------------------------------------ */
/* Campaigns Tab                                                         */
/* ------------------------------------------------------------------ */
function CampaignsTab() {
  const [campaigns, setCampaigns] = useState([])
  const [loading, setLoad]        = useState(true)
  const [form, setForm]           = useState({ subject: '', body_html: '', segment: 'all' })
  const [saving, setSaving]       = useState(false)
  const [sending, setSending]     = useState(null)

  useEffect(() => {
    getCampaigns()
      .then(r => r.ok ? r.json() : [])
      .then(d => setCampaigns(Array.isArray(d) ? d : []))
      .finally(() => setLoad(false))
  }, [])

  async function handleCreate(e) {
    e.preventDefault()
    setSaving(true)
    const res = await createCampaign(form)
    if (res.ok) {
      const nc = await res.json()
      setCampaigns(c => [nc, ...c])
      setForm({ subject: '', body_html: '', segment: 'all' })
    }
    setSaving(false)
  }

  async function handleSend(id) {
    if (!confirm('إرسال الحملة الآن؟')) return
    setSending(id)
    const res = await sendCampaign(id)
    if (res.ok) setCampaigns(c => c.map(x => x.id === id ? { ...x, status: 'sending' } : x))
    setSending(null)
  }

  if (loading) return <p className={styles.muted}>جاري التحميل...</p>

  return (
    <div>
      <form className={styles.form} onSubmit={handleCreate}>
        <h3 className={styles.formHeading}>حملة بريدية جديدة</h3>
        <input className={styles.input} placeholder="موضوع البريد *" value={form.subject}
          onChange={e => setForm(f => ({ ...f, subject: e.target.value }))} required />
        <select className={styles.select} value={form.segment}
          onChange={e => setForm(f => ({ ...f, segment: e.target.value }))}>
          {Object.entries(SEGMENT_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <textarea className={styles.textarea} placeholder="محتوى البريد (يمكن HTML)..." rows={6}
          value={form.body_html} onChange={e => setForm(f => ({ ...f, body_html: e.target.value }))} required />
        <button className={styles.btn} type="submit" disabled={saving}>{saving ? 'جاري الحفظ...' : 'حفظ كمسودة'}</button>
      </form>

      <div className={styles.listItems}>
        {campaigns.map(c => (
          <div key={c.id} className={styles.listItem}>
            <div>
              <div className={styles.listTitle}>{c.subject}</div>
              <div className={styles.listMeta}>{SEGMENT_LABELS[c.segment] ?? c.segment} — أُرسل لـ {c.sent_count ?? 0} شخص</div>
            </div>
            <div className={styles.campaignActions}>
              <span className={styles.chip}>{STATUS_AR[c.status] ?? c.status}</span>
              {c.status === 'draft' && (
                <button className={styles.btn} onClick={() => handleSend(c.id)} disabled={sending === c.id}>
                  {sending === c.id ? 'جاري...' : 'إرسال'}
                </button>
              )}
            </div>
          </div>
        ))}
        {campaigns.length === 0 && <p className={styles.muted}>لا توجد حملات حتى الآن</p>}
      </div>
    </div>
  )
}
