import { apiFetch } from './client'

// Pricing settings (singleton)
export const getPricingSettings    = () => apiFetch('/api/attendance/pricing-settings/')
export const updatePricingSettings = (data) => apiFetch('/api/attendance/pricing-settings/', { method: 'PATCH', body: JSON.stringify(data) })

// Student discounts
export const getDiscounts   = (params = {}) => apiFetch(`/api/attendance/discounts/?${new URLSearchParams(params)}`)
export const createDiscount = (data) => apiFetch('/api/attendance/discounts/', { method: 'POST', body: JSON.stringify(data) })
export const updateDiscount = (id, data) => apiFetch(`/api/attendance/discounts/${id}/`, { method: 'PATCH', body: JSON.stringify(data) })

// Lesson packages
export const getPackages   = () => apiFetch('/api/attendance/packages/')
export const createPackage = (data) => apiFetch('/api/attendance/packages/', { method: 'POST', body: JSON.stringify(data) })
export const updatePackage = (id, data) => apiFetch(`/api/attendance/packages/${id}/`, { method: 'PATCH', body: JSON.stringify(data) })
export const applyPackage  = (id, studentId) => apiFetch(`/api/attendance/packages/${id}/apply/`, { method: 'POST', body: JSON.stringify({ student_id: studentId }) })

// Groups & sessions
export const getGroups         = () => apiFetch('/api/attendance/groups/')
export const createGroup       = (data) => apiFetch('/api/attendance/groups/', { method: 'POST', body: JSON.stringify(data) })
export const updateGroup       = (id, data) => apiFetch(`/api/attendance/groups/${id}/`, { method: 'PATCH', body: JSON.stringify(data) })
export const getSessions       = () => apiFetch('/api/attendance/sessions/')
export const createSession     = (data) => apiFetch('/api/attendance/sessions/', { method: 'POST', body: JSON.stringify(data) })
export const getChecklist      = (sessionId) => apiFetch(`/api/attendance/sessions/${sessionId}/checklist/`)
export const markAttendance    = (sessionId, studentId, status) => apiFetch(`/api/attendance/sessions/${sessionId}/mark/`, { method: 'POST', body: JSON.stringify({ student_id: studentId, status }) })
export const markAllPresent    = (sessionId) => apiFetch(`/api/attendance/sessions/${sessionId}/mark-all-present/`, { method: 'POST' })
export const scanAttendance    = ({ token, session_id, resolution }) => apiFetch('/api/attendance/scan/', { method: 'POST', body: JSON.stringify({ token, session_id, resolution }) })
export const searchSessionStudents = (sessionId, q) => apiFetch(`/api/attendance/sessions/${sessionId}/search/?${new URLSearchParams({ q })}`)

// Override tools
export const revokeAccess   = (recordId) => apiFetch(`/api/attendance/records/${recordId}/revoke-access/`, { method: 'POST' })
export const resendWhatsapp = (recordId) => apiFetch(`/api/attendance/records/${recordId}/resend-whatsapp/`, { method: 'POST' })

// Arrears & revenue report
export const getArrears       = () => apiFetch('/api/attendance/arrears/')
export const getRevenueReport = (granularity = 'day') => apiFetch(`/api/attendance/revenue-report/?${new URLSearchParams({ granularity })}`)
