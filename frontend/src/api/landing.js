import { apiFetch } from './client'
export const getLandingContent = () => apiFetch('/api/notifications/landing/')
