import styles from './RegisterCTA.module.css'

export default function RegisterCTA({ data }) {
  const glyph   = data?.glyph    ?? '𓂀'
  const heading = data?.heading  ?? 'هتحس إنك قاعد في الفصل بالظبط!'
  const body    = data?.body     ?? 'اعمل حسابك في دقيقة واحدة، واختار كورس صفّك، وابدأ أول حصة النهاردة. أول حصة تجريبية مجانًا!'
  const ctaText = data?.cta_text ?? 'إنشاء حساب جديد'
  const ctaLink = data?.cta_link ?? '/register'

  return (
    <section id="register" className={styles.section}>
      <div className={styles.container}>
        <div className={styles.card}>
          <div className={styles.goldStrip} />
          <div className={styles.dotOverlay} />

          <div className={styles.content}>
            <div className={styles.glyph}>{glyph}</div>
            <h2 className={styles.heading}>{heading}</h2>
            <p className={styles.body}>{body}</p>
            <a href={ctaLink} className={styles.cta}>{ctaText}</a>
          </div>
        </div>
      </div>
    </section>
  )
}
