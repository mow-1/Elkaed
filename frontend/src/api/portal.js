import { apiFetch } from './client'

export const getMyAttempts = () => apiFetch('/api/quizzes/my-attempts/')

export const getMaterials = (kind) => apiFetch(`/api/courses/materials/?kind=${kind}`)

export const getMyLessons = () => apiFetch('/api/courses/my-lessons/')

export const getWalletHistory = (params = {}) => {
  const qs = new URLSearchParams(params).toString()
  return apiFetch(`/api/commerce/wallet/history/${qs ? `?${qs}` : ''}`)
}

// shared video-launch mechanism — used by MaterialsTab / LessonsTab / MyCoursesTab
export const requestVideoToken = (lessonId) =>
  apiFetch(`/api/videos/lesson/${lessonId}/token/`, { method: 'POST' })
