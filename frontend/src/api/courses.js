import { apiFetch } from './client'

export const getCourses        = (params = '') => apiFetch(`/api/courses/?${params}`)
export const getInstructors    = ()            => apiFetch('/api/courses/instructors/')
export const getCourse         = (slug)        => apiFetch(`/api/courses/${slug}/`)
export const enrollCourse      = (id)          => apiFetch(`/api/courses/${id}/enroll/`, { method: 'POST' })
export const getMyEnrollments  = ()            => apiFetch('/api/courses/my-enrollments/')
export const getWatchlist      = ()            => apiFetch('/api/courses/watchlist/')
export const toggleWatchlist   = (lessonId)    => apiFetch(`/api/courses/watchlist/${lessonId}/`, { method: 'POST' })
