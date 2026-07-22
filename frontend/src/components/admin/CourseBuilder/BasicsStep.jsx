import { useEffect, useState } from 'react'
import { getCategories, createBuilderCourse, updateBuilderCourse } from '../../../api/courseBuilder'
import styles from '../../../pages/AdminPanelPage.module.css'

function slugify(text) {
  // Django's SlugField (and the <slug:slug> URL converter) is ASCII-only, and
  // course titles here are always Arabic — so a transliteration-free slugify
  // strips non-Latin characters and falls back to a random suffix rather than
  // producing a slug the backend will reject outright.
  const base = text.trim().toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '')
  return base.length >= 3 ? base : `course-${Math.random().toString(36).slice(2, 8)}`
}

export default function BasicsStep({ course, onSaved }) {
  const [categories, setCategories] = useState([])
  const [form, setForm] = useState({
    title: course?.title ?? '',
    slug: course?.slug ?? '',
    description: course?.description ?? '',
    price: course?.price ?? '',
    category: course?.category ?? '',
    is_published: course?.is_published ?? false,
  })
  const [thumbnail, setThumbnail] = useState(null)
  const [slugTouched, setSlugTouched] = useState(!!course)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    getCategories()
      .then(r => r.ok ? r.json() : [])
      .then(d => setCategories(Array.isArray(d) ? d : (d?.results ?? [])))
  }, [])

  function handleTitleChange(value) {
    setForm(f => ({ ...f, title: value, slug: slugTouched ? f.slug : slugify(value) }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setSaving(true)
    setError('')
    try {
      const fd = new FormData()
      Object.entries(form).forEach(([k, v]) => fd.append(k, v))
      if (thumbnail) fd.append('thumbnail', thumbnail)

      const res = course
        ? await updateBuilderCourse(course.id, fd)
        : await createBuilderCourse(fd)

      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        setError(Object.values(body).flat().join(' — ') || 'حدث خطأ')
        return
      }
      onSaved(await res.json())
    } finally {
      setSaving(false)
    }
  }

  return (
    <form className={styles.form} onSubmit={handleSubmit}>
      <label className={styles.inputLabel}>عنوان الكورس
        <input className={styles.input} value={form.title} required
          onChange={e => handleTitleChange(e.target.value)} />
      </label>

      <label className={styles.inputLabel}>رابط الكورس (slug) — حروف إنجليزية وأرقام وشرطات فقط
        <input className={styles.input} dir="ltr" value={form.slug} required
          onChange={e => { setSlugTouched(true); setForm(f => ({ ...f, slug: e.target.value })) }} />
      </label>

      <label className={styles.inputLabel}>الوصف
        <textarea className={styles.textarea} value={form.description} required
          onChange={e => setForm(f => ({ ...f, description: e.target.value }))} />
      </label>

      <label className={styles.inputLabel}>الصورة المصغرة
        <input type="file" accept="image/*" onChange={e => setThumbnail(e.target.files[0])} />
      </label>

      <label className={styles.inputLabel}>السعر (جنيه)
        <input className={styles.input} type="number" step="0.01" min="0" required
          value={form.price} onChange={e => setForm(f => ({ ...f, price: e.target.value }))} />
      </label>

      <label className={styles.inputLabel}>الفئة (الصف / النوع)
        <select className={styles.select} value={form.category}
          onChange={e => setForm(f => ({ ...f, category: e.target.value }))}>
          <option value="">بدون فئة</option>
          {categories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
      </label>

      <label className={styles.inputLabel} style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
        <input type="checkbox" checked={form.is_published}
          onChange={e => setForm(f => ({ ...f, is_published: e.target.checked }))} />
        نشر الكورس
      </label>

      {error && <p className={styles.errorText}>{error}</p>}

      <button className={styles.btn} type="submit" disabled={saving}>
        {saving ? 'جارٍ الحفظ...' : 'حفظ ومتابعة للمنهج ›'}
      </button>
    </form>
  )
}
