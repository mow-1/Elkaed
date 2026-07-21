import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useCart } from '../context/CartContext'
import styles from './Navbar.module.css'

function WalletAndCart() {
  const { user } = useAuth()
  const { items } = useCart()
  if (!user || user.role !== 'student') return null
  return (
    <>
      <span className={styles.walletChip} title="رصيد المحفظة">
        💰 {user.wallet_balance} ج.م
      </span>
      <Link to="/checkout" className={styles.cartLink} title="السلة">
        🛒
        {items.length > 0 && <span className={styles.cartBadge}>{items.length}</span>}
      </Link>
    </>
  )
}

export default function Navbar() {
  const [open, setOpen] = useState(false)
  const [scrolled, setScrolled] = useState(false)
  const { user, logout } = useAuth()

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20)
    window.addEventListener('scroll', onScroll)
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  return (
    <header className={`${styles.navbar} ${scrolled ? styles.scrolled : ''}`}>
      <div className={styles.container}>
        <a href="#hero" className={styles.logo}>
          <div className={styles.logoMark}>
            <div className={styles.triangle} />
          </div>
          <div className={styles.logoText}>
            <span className={styles.logoAr}>القائد</span>
            <span className={styles.logoEn}>EL-KAED</span>
          </div>
        </a>

        <nav className={`${styles.nav} ${open ? styles.open : ''}`}>
          <a href="#hero" className={`${styles.link} ${styles.active}`}>الرئيسية</a>
          <Link to="/courses" className={styles.link}>الكورسات</Link>
          <a href="#features" className={styles.link}>ليه القائد؟</a>
          <a href="#testimonials" className={styles.link}>آراء الطلاب</a>
          <div className={styles.mobileAuth}>
            {user ? (
              <>
                <WalletAndCart />
                <Link to="/portal" className={styles.link}>بوابة الطالب</Link>
                <Link to="/dashboard" className={styles.link}>لوحة التحكم</Link>
                {['admin', 'staff'].includes(user.role) && (
                  <Link to="/admin-panel" className={styles.link}>لوحة الإدارة</Link>
                )}
                <button className={styles.logoutBtn} onClick={logout}>خروج</button>
              </>
            ) : (
              <>
                <Link to="/login" className={styles.loginLink}>تسجيل الدخول</Link>
                <Link to="/register" className={styles.registerBtn}>حساب جديد</Link>
              </>
            )}
          </div>
        </nav>

        <div className={styles.auth}>
          {user ? (
            <>
              <div className={styles.userInfo}>
                <div className={styles.avatar}>{user.first_name?.[0] ?? '؟'}</div>
                <span className={styles.userName}>{user.first_name}</span>
              </div>
              <WalletAndCart />
              <Link to="/portal" className={styles.link}>بوابة الطالب</Link>
              <Link to="/dashboard" className={styles.link}>لوحة التحكم</Link>
              {['admin', 'staff'].includes(user.role) && (
                <Link to="/admin-panel" className={styles.link}>لوحة الإدارة</Link>
              )}
              <button className={styles.logoutBtn} onClick={logout}>خروج</button>
            </>
          ) : (
            <>
              <Link to="/login" className={styles.loginLink}>تسجيل الدخول</Link>
              <Link to="/register" className={styles.registerBtn}>حساب جديد</Link>
            </>
          )}
        </div>

        <button
          className={styles.hamburger}
          onClick={() => setOpen(o => !o)}
          aria-label="فتح القائمة"
          aria-expanded={open}
        >
          {open ? '✕' : '☰'}
        </button>
      </div>
    </header>
  )
}
