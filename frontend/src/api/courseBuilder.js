import { apiFetch } from './client'

export const getCategories = () => apiFetch('/api/courses/categories/')
export const getInstructorStats = () => apiFetch('/api/courses/instructor/')

// Courses
export const getMyBuilderCourses = () => apiFetch('/api/courses/admin/courses/')
export const getBuilderCourse    = (id) => apiFetch(`/api/courses/admin/courses/${id}/`)
export const createBuilderCourse = (data) => apiFetch('/api/courses/admin/courses/', { method: 'POST', body: data instanceof FormData ? data : JSON.stringify(data) })
export const updateBuilderCourse = (id, data) => apiFetch(`/api/courses/admin/courses/${id}/`, { method: 'PATCH', body: data instanceof FormData ? data : JSON.stringify(data) })
export const deleteBuilderCourse = (id) => apiFetch(`/api/courses/admin/courses/${id}/`, { method: 'DELETE' })

// Full curriculum — the admin course-detail endpoint (not the public one, which
// filters to is_published=True and would 404 for a draft course being built)
export const getCourseCurriculum = (courseId) => apiFetch(`/api/courses/admin/courses/${courseId}/`)

// Topics
export const createTopic = (courseId, data) => apiFetch(`/api/courses/admin/courses/${courseId}/topics/`, { method: 'POST', body: JSON.stringify(data) })
export const updateTopic = (id, data) => apiFetch(`/api/courses/admin/topics/${id}/`, { method: 'PATCH', body: JSON.stringify(data) })
export const deleteTopic = (id) => apiFetch(`/api/courses/admin/topics/${id}/`, { method: 'DELETE' })

// Lessons (accepts a plain object OR a FormData with a raw_file for video upload)
export const createLesson = (topicId, data) => apiFetch(`/api/courses/admin/topics/${topicId}/lessons/`, { method: 'POST', body: data instanceof FormData ? data : JSON.stringify(data) })
export const updateLesson = (id, data) => apiFetch(`/api/courses/admin/lessons/${id}/`, { method: 'PATCH', body: data instanceof FormData ? data : JSON.stringify(data) })
export const deleteLesson = (id) => apiFetch(`/api/courses/admin/lessons/${id}/`, { method: 'DELETE' })

// Quiz (one per topic — GET/PUT/DELETE by topic id)
export const getTopicQuiz    = (topicId) => apiFetch(`/api/quizzes/admin/topics/${topicId}/quiz/`)
export const saveTopicQuiz   = (topicId, data) => apiFetch(`/api/quizzes/admin/topics/${topicId}/quiz/`, { method: 'PUT', body: JSON.stringify(data) })
export const deleteTopicQuiz = (topicId) => apiFetch(`/api/quizzes/admin/topics/${topicId}/quiz/`, { method: 'DELETE' })

// Assignments
export const createAssignment = (topicId, data) => apiFetch(`/api/courses/admin/topics/${topicId}/assignments/`, { method: 'POST', body: data instanceof FormData ? data : JSON.stringify(data) })
export const updateAssignment = (id, data) => apiFetch(`/api/courses/admin/assignments/${id}/`, { method: 'PATCH', body: data instanceof FormData ? data : JSON.stringify(data) })
export const deleteAssignment = (id) => apiFetch(`/api/courses/admin/assignments/${id}/`, { method: 'DELETE' })

// Student-facing assignment submission
export const getMyAssignmentSubmission = (assignmentId) => apiFetch(`/api/courses/assignments/${assignmentId}/submit/`)
export const submitAssignment = (assignmentId, file) => {
  const fd = new FormData()
  fd.append('file', file)
  return apiFetch(`/api/courses/assignments/${assignmentId}/submit/`, { method: 'POST', body: fd })
}
