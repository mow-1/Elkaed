import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { sendOTP, verifyOTP, loginPassword } from '../api/auth'
import styles from './LoginPage.module.css'

export default function LoginPage() {
  const [mode, setMode]       = useState('otp') // 'otp' | 'password' — center students (CSV-imported) log in with their WhatsApp'd password
  const [step, setStep]       = useState('phone')
  const [phone, setPhone]     = useState('')
  const [code, setCode]       = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState('')
  const { login }             = useAuth()
  const navigate              = useNavigate()

  async function handlePasswordLogin(e) {
    e.preventDefault()
    setLoading(true); setError('')
    try {
      const res  = await loginPassword(phone, password)
      const data = await res.json()
      if (res.ok) {
        login({ access: data.access, refresh: data.refresh }, data.user)
        navigate('/portal')
      } else {
        setError(data.detail ?? 'رقم الهاتف أو كلمة المرور غير صحيحة')
      }
    } catch {
      setError('فشل الاتصال بالسيرفر')
    } finally {
      setLoading(false)
    }
  }

  async function handlePhone(e) {
    e.preventDefault()
    setLoading(true); setError('')
    try {
      const res  = await sendOTP(phone, 'login')
      const data = await res.json()
      if (res.ok) setStep('otp')
      else setError(data.detail ?? 'حدث خطأ، حاول مرة أخرى')
    } catch {
      setError('فشل الاتصال بالسيرفر')
    } finally {
      setLoading(false)
    }
  }

  async function handleOTP(e) {
    e.preventDefault()
    setLoading(true); setError('')
    try {
      const res  = await verifyOTP({ phone, code, purpose: 'login' })
      const data = await res.json()
      if (res.ok) {
        login({ access: data.access, refresh: data.refresh }, data.user)
        navigate('/portal')
      } else {
        setError(data.detail ?? 'رمز خاطئ، حاول مرة أخرى')
      }
    } catch {
      setError('فشل الاتصال بالسيرفر')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={styles.page}>
      <div className={styles.card}>
        <Link to="/" className={styles.homeLink}>العودة للرئيسية &larr;</Link>

        <Link to="/" className={styles.logo}>
          <div className={styles.logoMark}>
            <div className={styles.logoTriangle} />
          </div>
          <span className={styles.logoText}>القائد</span>
        </Link>

        <h1 className={styles.heading}>تسجيل الدخول</h1>
        <p className={styles.subtext}>
          {mode === 'otp' ? 'أدخل رقم هاتفك وهنبعتلك رمز تحقق' : 'أدخل رقم هاتفك وكلمة المرور'}
        </p>

        {mode === 'password' ? (
          <form className={styles.form} onSubmit={handlePasswordLogin}>
            <div className={styles.field}>
              <label className={styles.label}>رقم الهاتف</label>
              <input
                className={styles.input}
                type="tel"
                placeholder="01XXXXXXXXX"
                value={phone}
                onChange={e => setPhone(e.target.value)}
                required
              />
            </div>
            <div className={styles.field}>
              <label className={styles.label}>كلمة المرور</label>
              <input
                className={styles.input}
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
              />
              {error && <p className={styles.error}>{error}</p>}
            </div>
            <button className={styles.btn} type="submit" disabled={loading}>
              {loading ? 'جاري الدخول...' : 'دخول'}
            </button>
            <p className={styles.footer}>
              <button type="button" className={styles.link} onClick={() => { setMode('otp'); setError('') }}>
                الدخول برمز واتساب بدلاً من ذلك
              </button>
            </p>
          </form>
        ) : step === 'phone' ? (
          <form className={styles.form} onSubmit={handlePhone}>
            <div className={styles.field}>
              <label className={styles.label}>رقم الهاتف</label>
              <input
                className={styles.input}
                type="tel"
                placeholder="01XXXXXXXXX"
                value={phone}
                onChange={e => setPhone(e.target.value)}
                required
              />
              {error && <p className={styles.error}>{error}</p>}
            </div>
            <button className={styles.btn} type="submit" disabled={loading}>
              {loading ? 'جاري الإرسال...' : 'إرسال رمز التحقق'}
            </button>
            <p className={styles.footer}>
              طالب سنتر ولديك كلمة مرور؟{' '}
              <button type="button" className={styles.link} onClick={() => { setMode('password'); setError('') }}>
                الدخول بكلمة المرور
              </button>
            </p>
            <p className={styles.footer}>
              ليس لديك حساب؟{' '}
              <Link to="/register" className={styles.link}>إنشاء حساب</Link>
            </p>
          </form>
        ) : (
          <div className={styles.step2}>
            <p className={styles.otpSent}>تم إرسال الرمز إلى {phone}</p>
            <form className={styles.form} onSubmit={handleOTP}>
              <div className={styles.field}>
                <label className={styles.label}>رمز التحقق</label>
                <input
                  className={`${styles.input} ${styles.inputOtp}`}
                  type="text"
                  inputMode="numeric"
                  maxLength={6}
                  placeholder="------"
                  value={code}
                  onChange={e => setCode(e.target.value)}
                  required
                />
                {error && <p className={styles.error}>{error}</p>}
              </div>
              <button className={styles.btn} type="submit" disabled={loading}>
                {loading ? 'جاري التحقق...' : 'دخول'}
              </button>
              <p className={styles.footer}>
                <button
                  type="button"
                  className={styles.link}
                  onClick={() => { setStep('phone'); setError(''); setCode('') }}
                >
                  تغيير الرقم
                </button>
              </p>
            </form>
          </div>
        )}
      </div>
    </div>
  )
}
