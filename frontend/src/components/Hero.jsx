import styles from './Hero.module.css'

export default function Hero({ data: _data }) {
  const data = _data ?? {}
  const eyebrow   = data.eyebrow        ?? 'منصة تعليم التاريخ للثانوية العامة'
  const heading   = data.heading        ?? 'اتعلّم التاريخ مع القائد..'
  const headingWh = data.heading_white  ?? 'ومن أي مكان'
  const para      = data.para           ?? 'مع أ/ مصطفى عرفة — تجربة تعليمية مرنة وسهلة الوصول: شرح، مراجعات نهائية، وامتحانات بنظام الثانوية العامة. كل الحصص في مكان واحد.'
  const cta1Text  = data.cta1_text      ?? 'تصفح الكورسات'
  const cta1Link  = data.cta1_link      ?? '#courses'
  const cta2Text  = data.cta2_text      ?? 'حسابي'
  const cta2Link  = data.cta2_link      ?? '#register'
  const stat1Num  = data.stat1_num      ?? '+12,000'
  const stat1Lbl  = data.stat1_label    ?? 'طالب وطالبة'
  const stat2Num  = data.stat2_num      ?? '+340'
  const stat2Lbl  = data.stat2_label    ?? 'حصة مسجلة'
  const stat3Num  = data.stat3_num      ?? '%94'
  const stat3Lbl  = data.stat3_label    ?? 'نسبة نجاح +85'

  return (
    <section id="hero" className={styles.hero}>
      <div className={styles.dots} aria-hidden="true" />

      <div className={styles.container}>
        {/* Text column */}
        <div className={styles.text}>
          <div className={styles.eyebrow}>
            <span className={styles.bullet} aria-hidden="true" />
            {eyebrow}
          </div>

          <h1 className={styles.heading}>
            {heading}
            <br />
            <span className={styles.headingWhite}>{headingWh}</span>
          </h1>

          <p className={styles.para}>{para}</p>

          <div className={styles.ctas}>
            <a href={cta1Link} className={styles.ctaGold}>{cta1Text}</a>
            <a href={cta2Link} className={styles.ctaGhost}>{cta2Text}</a>
          </div>

          <div className={styles.stats}>
            <div className={styles.stat}>
              <span className={styles.statNum}>{stat1Num}</span>
              <span className={styles.statLabel}>{stat1Lbl}</span>
            </div>
            <div className={styles.stat}>
              <span className={styles.statNum}>{stat2Num}</span>
              <span className={styles.statLabel}>{stat2Lbl}</span>
            </div>
            <div className={styles.stat}>
              <span className={styles.statNum}>{stat3Num}</span>
              <span className={styles.statLabel}>{stat3Lbl}</span>
            </div>
          </div>
        </div>

        {/* Cards column */}
        <div className={styles.cards} aria-hidden="true">
          {/* Card 1 */}
          <div className={`${styles.card} ${styles.card1}`}>
            <div className={styles.imgSlot}>
              <span className={styles.imgGlyph}>𓂀</span>
              <span className={styles.priceBadge}>70 جنيه</span>
            </div>
            <div className={styles.cardBody}>
              <div className={styles.teacherRow}>
                <div className={styles.teacherAvatar}>𓂀</div>
                <span className={styles.teacherName}>مصطفى عرفة</span>
              </div>
              <h3 className={styles.cardTitle}>الحصة الأولى — الصف الثالث الثانوي — تاريخ</h3>
              <div className={styles.cardFooter}>
                <span>👥 114 طالب</span>
                <span>حصة واحدة 📖</span>
              </div>
            </div>
          </div>

          {/* Card 2 — floating animation */}
          <div className={`${styles.card} ${styles.card2}`}>
            <div className={styles.imgSlot}>
              <span className={styles.imgGlyph}>𓂀</span>
              <span className={styles.priceBadge}>240 جنيه</span>
            </div>
            <div className={styles.cardBody}>
              <div className={styles.teacherRow}>
                <div className={styles.teacherAvatar}>𓂀</div>
                <span className={styles.teacherName}>مصطفى عرفة</span>
              </div>
              <h3 className={styles.cardTitle}>الشهر الأول — الصف الثالث الثانوي — تاريخ</h3>
              <div className={styles.cardFooter}>
                <span>👥 139 طالب</span>
                <span>4 حصص 📖</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className={styles.cutout} aria-hidden="true" />
    </section>
  )
}
