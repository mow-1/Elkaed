import { useEffect, useState } from 'react'
import { getCourses, getInstructors } from '../api/courses'
import { GRADES } from '../data/courses'
import CourseCard, { SkeletonCard } from '../components/CourseCard'
import styles from '../components/Courses.module.css'

const GRADE_TO_YEAR = { 'الأول الثانوي': '1st', 'الثاني الثانوي': '2nd', 'الثالث الثانوي': '3rd' }

function mapApiCourse(c) {
  return {
    id: c.id,
    slug: c.slug,
    title: c.title,
    grade: c.category_name ?? '—',
    instructorName: c.instructor_name,
    price: `${c.price} جنيه`,
    students: 0,
    lessons: '—',
    img: c.thumbnail ?? null,
  }
}

function pageFromUrl(url) {
  if (!url) return null
  try { return new URL(url).searchParams.get('page') } catch { return null }
}

export default function CoursesListPage() {
  const [activeGrade, setActiveGrade] = useState('الكل')
  const [activeTeacher, setActiveTeacher] = useState('all')
  const [teachers, setTeachers] = useState([])
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(null)
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getInstructors()
      .then(r => r.ok ? r.json() : [])
      .then(d => setTeachers(Array.isArray(d) ? d : (d?.results ?? [])))
      .catch(() => {})
  }, [])

  useEffect(() => {
    setLoading(true)
    const params = new URLSearchParams()
    if (search.trim()) params.set('search', search.trim())
    if (GRADE_TO_YEAR[activeGrade]) params.set('category__academic_year', GRADE_TO_YEAR[activeGrade])
    if (activeTeacher !== 'all') params.set('instructor', activeTeacher)
    if (page) params.set('page', page)
    getCourses(params.toString())
      .then(res => res.ok ? res.json() : null)
      .then(d => { if (d) setData(d) })
      .finally(() => setLoading(false))
  }, [activeGrade, activeTeacher, search, page])

  const courses = (data?.results ?? []).map(mapApiCourse)

  return (
    <section className={styles.section}>
      <div className={styles.container}>
        <div className={styles.header}>
          <p className={styles.eyebrow}>كل الكورسات</p>
          <h2 className={styles.title}>تصفّح كورسات القائد</h2>
          <p className={styles.subtitle}>
            دوّر بالاسم أو اختار صفّك — كل كورسات القائد في مكان واحد.
          </p>
        </div>

        <div style={{ maxWidth: 420, margin: '0 auto 24px' }}>
          <input
            type="text"
            placeholder="دوّر عن كورس..."
            value={search}
            onChange={e => { setSearch(e.target.value); setPage(null) }}
            style={{
              width: '100%', padding: '12px 16px', borderRadius: 999,
              border: '1.5px solid var(--sand-border)', fontSize: 15,
            }}
          />
        </div>

        <div className={styles.pills}>
          {GRADES.map(grade => (
            <button
              key={grade}
              className={`${styles.pill} ${activeGrade === grade ? styles.pillActive : ''}`}
              onClick={() => { setActiveGrade(grade); setPage(null) }}
            >
              {grade === 'الكل' ? 'كل الصفوف' : 'الصف ' + grade}
            </button>
          ))}
        </div>

        {teachers.length > 1 && (
          <div className={styles.pills} style={{ marginTop: 10 }}>
            <button
              className={`${styles.pill} ${activeTeacher === 'all' ? styles.pillActive : ''}`}
              onClick={() => { setActiveTeacher('all'); setPage(null) }}
            >
              كل المدرسين
            </button>
            {teachers.map(t => (
              <button
                key={t.id}
                className={`${styles.pill} ${activeTeacher === String(t.id) ? styles.pillActive : ''}`}
                onClick={() => { setActiveTeacher(String(t.id)); setPage(null) }}
              >
                {t.full_name}
              </button>
            ))}
          </div>
        )}

        <div className={styles.grid}>
          {loading
            ? [0, 1, 2].map(i => <SkeletonCard key={i} />)
            : courses.map(c => <CourseCard key={c.id} course={c} />)
          }
        </div>

        {!loading && courses.length === 0 && (
          <p style={{ textAlign: 'center', color: 'var(--text-muted)', marginTop: 24 }}>
            لا توجد كورسات مطابقة.
          </p>
        )}

        {data && (data.next || data.previous) && (
          <div style={{ display: 'flex', justifyContent: 'center', gap: 12, marginTop: 32 }}>
            <button
              className={styles.pill}
              disabled={!data.previous}
              onClick={() => setPage(pageFromUrl(data.previous))}
            >
              السابق
            </button>
            <button
              className={styles.pill}
              disabled={!data.next}
              onClick={() => setPage(pageFromUrl(data.next))}
            >
              التالي
            </button>
          </div>
        )}
      </div>
    </section>
  )
}
