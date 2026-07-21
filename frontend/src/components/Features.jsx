import { FEATURES } from '../data/courses'
import styles from './Features.module.css'

export default function Features({ features }) {
  const list = features?.length ? features : FEATURES
  return (
    <section id="features" className={styles.section}>
      <div className={styles.container}>
        <div className={styles.header}>
          <p className={styles.eyebrow}>اتعلّم بالأسلوب اللي يناسبك</p>
          <h2 className={styles.title}>ليه تذاكر التاريخ مع القائد؟</h2>
          <div className={styles.underline} />
        </div>

        <div className={styles.grid}>
          {list.map((f) => (
            <div key={f.title} className={styles.card}>
              <div className={styles.glyph}>{f.glyph}</div>
              <h3 className={styles.cardTitle}>{f.title}</h3>
              <p className={styles.cardBody}>{f.body}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
