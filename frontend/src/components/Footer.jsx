import styles from './Footer.module.css'

export default function Footer() {
  return (
    <footer className={styles.footer}>
      <div className={styles.container}>
        <div className={styles.grid}>
          {/* Brand */}
          <div className={styles.brand}>
            <div className={styles.logoRow}>
              <div className={styles.logoMark}>
                <div className={styles.triangle} />
              </div>
              <span className={styles.logoName}>القائد</span>
            </div>
            <p className={styles.brandText}>
              منصة الأستاذ مصطفى عرفة لتعليم التاريخ لطلاب المرحلة الثانوية — شرح، مراجعات، وامتحانات أونلاين.
            </p>
          </div>

          {/* Quick links */}
          <div className={styles.col}>
            <h4 className={styles.colHeading}>روابط سريعة</h4>
            <a href="#courses" className={styles.colLink}>الكورسات</a>
            <a href="#features" className={styles.colLink}>ليه القائد؟</a>
            <a href="#register" className={styles.colLink}>إنشاء حساب</a>
          </div>

          {/* Contact */}
          <div className={styles.col}>
            <h4 className={styles.colHeading}>تواصل معانا</h4>
            <a
              href="https://www.facebook.com/MostafaArafaOfficial1"
              target="_blank"
              rel="noreferrer"
              className={styles.colLink}
            >
              صفحة الفيسبوك
            </a>
            <a href="#" className={styles.colLink}>واتساب: 01000000000</a>
          </div>
        </div>

        <div className={styles.bottom}>
          <span>© 2026 منصة القائد — أ/ مصطفى عرفة</span>
          <span className={styles.tagline}>التاريخ حكاية… والقائد راويها</span>
        </div>
      </div>
    </footer>
  )
}
