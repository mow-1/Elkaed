import { apiFetch } from './client'

export const sendOTP    = (phone, purpose) =>
  apiFetch('/api/auth/send-otp/', { method: 'POST', body: JSON.stringify({ phone, purpose }) })

export const verifyOTP  = (data) =>
  apiFetch('/api/auth/verify-otp/', { method: 'POST', body: JSON.stringify(data) })

export const loginPassword = (phone, password) =>
  apiFetch('/api/auth/login-password/', { method: 'POST', body: JSON.stringify({ phone, password }) })

export const getProfile = () => apiFetch('/api/auth/profile/')

export const updateProfile = (data) =>
  apiFetch('/api/auth/profile/', { method: 'PATCH', body: JSON.stringify(data) })

export const getAnalytics = () => apiFetch('/api/auth/analytics/')

export const getRegistrationSettings = () => apiFetch('/api/auth/registration-settings/')

export const changePassword = (newPassword) =>
  apiFetch('/api/auth/change-password/', { method: 'POST', body: JSON.stringify({ new_password: newPassword }) })

export const getMyQrCode = () => apiFetch('/api/auth/me/qr-code.png')

export const getMyIdCardPdf = () => apiFetch('/api/auth/me/id-card.pdf')
