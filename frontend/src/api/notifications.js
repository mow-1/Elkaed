import { apiFetch } from './client'

export const getBanners       = () => apiFetch('/api/notifications/banners/')
export const getNotifPrefs    = () => apiFetch('/api/notifications/preferences/')
export const updateNotifPrefs = (data) =>
  apiFetch('/api/notifications/preferences/', { method: 'PATCH', body: JSON.stringify(data) })
