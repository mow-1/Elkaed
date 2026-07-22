import { apiFetch } from './client'

export const getMyAttempts = () => apiFetch('/api/quizzes/my-attempts/')

// quiz-taking
export const getQuiz          = (quizId) => apiFetch(`/api/quizzes/${quizId}/`)
export const startQuizAttempt = (quizId) => apiFetch(`/api/quizzes/${quizId}/start/`, { method: 'POST' })
export const submitQuizAttempt = (attemptId, answers) =>
  apiFetch(`/api/quizzes/attempts/${attemptId}/submit/`, { method: 'POST', body: JSON.stringify({ answers }) })
export const getAttemptResult = (attemptId) => apiFetch(`/api/quizzes/attempts/${attemptId}/`)

export const getMaterials = (kind) => apiFetch(`/api/courses/materials/?kind=${kind}`)

export const getMyLessons = () => apiFetch('/api/courses/my-lessons/')

export const getWalletHistory = (params = {}) => {
  const qs = new URLSearchParams(params).toString()
  return apiFetch(`/api/commerce/wallet/history/${qs ? `?${qs}` : ''}`)
}

// shared video-launch mechanism — used by MaterialsTab / LessonsTab / MyCoursesTab
export const requestVideoToken = (lessonId) =>
  apiFetch(`/api/videos/lesson/${lessonId}/token/`, { method: 'POST' })
