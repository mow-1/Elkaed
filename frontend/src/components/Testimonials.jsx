import { TESTIMONIALS } from '../data/courses'
import styles from './Testimonials.module.css'

export default function Testimonials({ testimonials }) {
  const list = testimonials?.length
    ? testimonials.map(t => ({ name: t.author_name, grade: t.grade, quote: t.text, initial: t.author_name?.[0] ?? '؟' }))
    : TESTIMONIALS
  return (
    <section id="testimonials" className={styles.section}>
      <div className={styles.container}>
        <div className={styles.header}>
          <h2 className={styles.title}>طلاب القائد بيقولوا إيه؟</h2>
          <div className={styles.bar} />
        </div>

        <div className={styles.grid}>
          {list.map((t) => (
            <div key={t.name} className={styles.card}>
              <div className={styles.quoteMark}>"</div>
              <p className={styles.quoteText}>{t.quote}</p>
              <div className={styles.author}>
                <div className={styles.avatar}>{t.initial}</div>
                <div>
                  <div className={styles.name}>{t.name}</div>
                  <div className={styles.grade}>{t.grade}</div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
