import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { COURSES } from '../data/courses'
import { getCourses } from '../api/courses'
import CourseCard, { SkeletonCard } from './CourseCard'
import styles from './Courses.module.css'

const PREVIEW_COUNT = 6

function mapApiCourse(c) {
  return {
    id: c.id,
    slug: c.slug,
    title: c.title,
    grade: c.category_name ?? '—',
    price: `${c.price} جنيه`,
    students: 0,
    lessons: '—',
    img: c.thumbnail ?? null,
  }
}

// Homepage teaser only — a handful of newest courses with a link to the full
// catalog page (/courses), which has the real filtering/search/pagination.
// Keeping the homepage from growing without bound as the catalog grows.
export default function Courses() {
  const [courses, setCourses] = useState(COURSES.slice(0, PREVIEW_COUNT))
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getCourses('ordering=-created_at')
      .then(res => res.ok ? res.json() : Promise.reject())
      .then(data => {
        if (data.results?.length) setCourses(data.results.slice(0, PREVIEW_COUNT).map(mapApiCourse))
      })
      .catch(() => { /* static fallback already in state */ })
      .finally(() => setLoading(false))
  }, [])

  return (
    <section id="courses" className={styles.section}>
      <div className={styles.container}>
        <div className={styles.header}>
          <p className={styles.eyebrow}>اتعلّم بالأسلوب اللي يناسبك</p>
          <h2 className={styles.title}>أشهر كورسات القائد</h2>
          <p className={styles.subtitle}>
            تصفّح الكورسات واختار اللي يناسب صفّك وهدفك. ابدأ المذاكرة معانا، وخلّي هدفك أقرب كل يوم!
          </p>
        </div>

        <div className={styles.grid}>
          {loading
            ? [0, 1, 2].map(i => <SkeletonCard key={i} />)
            : courses.map(c => <CourseCard key={c.id} course={c} />)
          }
        </div>

        <div className={styles.bottomLink}>
          <Link to="/courses" className={styles.link}>تصفّح كل الكورسات ←</Link>
        </div>
      </div>
    </section>
  )
}
