import { BAND_POINTS } from '../data/courses'
import styles from './DarkBand.module.css'

export default function DarkBand({ data }) {
  const heading = data?.heading  ?? 'طوّر مستواك، واتعلم التاريخ من أي مكان — وخلّي نتيجتك للأعلى!'
  const body    = data?.body     ?? 'حصص مسجلة تقدر ترجعلها في أي وقت، امتحانات دورية بنظام البابل شيت، ومتابعة أول بأول لمستواك — كأنك قاعد في السنتر بالظبط.'
  const ctaText = data?.cta_text ?? 'شوف كل الكورسات'
  const ctaLink = data?.cta_link ?? '#courses'
  const checks  = data
    ? [data.check1, data.check2, data.check3, data.check4].filter(Boolean)
    : BAND_POINTS

  return (
    <section className={styles.section}>
      <div className={styles.goldStrip} />

      <div className={styles.container}>
        {/* Text column */}
        <div className={styles.textCol}>
          <h2 className={styles.heading}>{heading}</h2>
          <p className={styles.body}>{body}</p>

          <div className={styles.checklist}>
            {checks.map((pt) => (
              <div key={pt} className={styles.checkItem}>
                <span className={styles.bullet} />
                <span className={styles.checkText}>{pt}</span>
              </div>
            ))}
          </div>

          <a href={ctaLink} className={styles.cta}>{ctaText}</a>
        </div>

        {/* Photo collage */}
        <div className={styles.collage}>
          <div className={`${styles.cell} ${styles.cellTall}`}>
            <span className={styles.placeholderGlyph}>𓂀</span>
          </div>
          <div className={`${styles.cell} ${styles.cellSmall}`}>
            <span className={styles.placeholderGlyph}>𓉐</span>
          </div>
          <div className={`${styles.cell} ${styles.cellQuote}`}>
            <span className={styles.quoteGlyph}>𓋹</span>
            <span className={styles.quoteText}>
              التاريخ مش حفظ…<br />التاريخ فهم وحكاية
            </span>
          </div>
        </div>
      </div>
    </section>
  )
}
