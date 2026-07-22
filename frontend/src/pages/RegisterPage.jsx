import { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { sendOTP, verifyOTP, getRegistrationSettings } from '../api/auth'
import styles from './RegisterPage.module.css'

const ACADEMIC_YEARS   = [['1st', 'الأول الثانوي'], ['2nd', 'الثاني الثانوي'], ['3rd', 'الثالث الثانوي']]

export default function RegisterPage() {
  const [step, setStep]               = useState('phone')
  const [phone, setPhone]             = useState('')
  const [code, setCode]               = useState('')
  const [firstName, setFirstName]     = useState('')
  const [lastName, setLastName]       = useState('')
  const [guardianPhone, setGuardianPhone] = useState('')
  const [governorate, setGovernorate] = useState('')
  const [schoolName, setSchoolName]   = useState('')
  const [academicYear, setAcademicYear] = useState('3rd')
  const [loading, setLoading]         = useState(false)
  const [error, setError]             = useState('')
  const [fields, setFields]           = useState({ show_governorate_field: true, show_school_field: true })
  const { login }                     = useAuth()
  const navigate                      = useNavigate()

  useEffect(() => {
    getRegistrationSettings()
      .then(r => r.ok ? r.json() : null)
      .then(d => { if (d) setFields(d) })
      .catch(() => {})
  }, [])

  async function handlePhone(e) {
    e.preventDefault()
    setLoading(true); setError('')
    try {
      const res  = await sendOTP(phone, 'register')
      const data = await res.json()
      if (res.ok) setStep('otp')
      else setError(data.detail ?? 'حدث خطأ، حاول مرة أخرى')
    } catch {
      setError('فشل الاتصال بالسيرفر')
    } finally {
      setLoading(false)
    }
  }

  function handleOTP(e) {
    e.preventDefault()
    setError('')
    setStep('profile')
  }

  async function handleProfile(e) {
    e.preventDefault()
    setLoading(true); setError('')
    try {
      const res  = await verifyOTP({
        phone,
        code,
        purpose:        'register',
        first_name:     firstName,
        last_name:      lastName,
        academic_year:  academicYear,
        guardian_phone: guardianPhone,
        governorate,
        school_name:    schoolName,
      })
      const data = await res.json()
      if (res.ok) {
        login({ access: data.access, refresh: data.refresh }, data.user)
        navigate('/portal')
      } else {
        setError(data.detail ?? 'حدث خطأ، حاول مرة أخرى')
      }
    } catch {
      setError('فشل الاتصال بالسيرفر')
    } finally {
      setLoading(false)
    }
  }

  const headings = {
    phone:   'إنشاء حساب جديد',
    otp:     'تأكيد رقم الهاتف',
    profile: 'أكمل بياناتك',
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

        <h1 className={styles.heading}>{headings[step]}</h1>
        <p className={styles.subtext}>أدخل رقم هاتفك وهنبعتلك رمز تحقق</p>

        {step === 'phone' && (
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
              لديك حساب بالفعل؟{' '}
              <Link to="/login" className={styles.link}>تسجيل الدخول</Link>
            </p>
          </form>
        )}

        {step === 'otp' && (
          <div className={styles.stepIn}>
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
              <button className={styles.btn} type="submit">
                التالي
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

        {step === 'profile' && (
          <div className={styles.stepIn}>
            <form className={styles.form} onSubmit={handleProfile}>
              <div className={styles.row}>
                <div className={styles.field}>
                  <label className={styles.label}>الاسم الأول</label>
                  <input
                    className={styles.input}
                    type="text"
                    placeholder="اسمك"
                    value={firstName}
                    onChange={e => setFirstName(e.target.value)}
                    required
                  />
                </div>
                <div className={styles.field}>
                  <label className={styles.label}>اسم العائلة</label>
                  <input
                    className={styles.input}
                    type="text"
                    placeholder="اسم العائلة"
                    value={lastName}
                    onChange={e => setLastName(e.target.value)}
                    required
                  />
                </div>
              </div>

              <div className={styles.field}>
                <label className={styles.label}>هاتف ولي الأمر</label>
                <input
                  className={styles.input}
                  type="tel"
                  placeholder="01XXXXXXXXX"
                  value={guardianPhone}
                  onChange={e => setGuardianPhone(e.target.value)}
                  required
                />
              </div>

              <div className={styles.field}>
                <label className={styles.label}>الصف الدراسي</label>
                <select
                  className={styles.select}
                  value={academicYear}
                  onChange={e => setAcademicYear(e.target.value)}
                >
                  {ACADEMIC_YEARS.map(([val, label]) => (
                    <option key={val} value={val}>{label}</option>
                  ))}
                </select>
              </div>

              {fields.show_governorate_field && (
                <div className={styles.field}>
                  <label className={styles.label}>المحافظة</label>
                  <input
                    className={styles.input}
                    type="text"
                    placeholder="المحافظة (اختياري)"
                    value={governorate}
                    onChange={e => setGovernorate(e.target.value)}
                  />
                </div>
              )}

              {fields.show_school_field && (
                <div className={styles.field}>
                  <label className={styles.label}>المدرسة</label>
                  <input
                    className={styles.input}
                    type="text"
                    placeholder="اسم المدرسة (اختياري)"
                    value={schoolName}
                    onChange={e => setSchoolName(e.target.value)}
                  />
                </div>
              )}

              {error && <p className={styles.error}>{error}</p>}

              <button className={styles.btn} type="submit" disabled={loading}>
                {loading ? 'جاري الإنشاء...' : 'إنشاء الحساب'}
              </button>
            </form>
          </div>
        )}
      </div>
    </div>
  )
}
