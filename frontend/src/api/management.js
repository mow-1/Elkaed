import { apiFetch } from './client'

// Customers
export const getCustomers     = (params = {}) => apiFetch(`/api/auth/customers/?${new URLSearchParams(params)}`)
export const getCustomerDetail = (id) => apiFetch(`/api/auth/customers/${id}/`)
export const setCustomerGroup  = (id, groupId) => apiFetch(`/api/auth/customers/${id}/`, { method: 'PATCH', body: JSON.stringify({ group: groupId }) })

// Analytics
export const getAdminAnalytics = () => apiFetch('/api/auth/analytics/')

// Banners
export const getAdminBanners = () => apiFetch('/api/notifications/banners/admin/')
export const createBanner    = (formData) => apiFetch('/api/notifications/banners/admin/', { method: 'POST', body: formData })
export const deleteBanner    = (id) => apiFetch(`/api/notifications/banners/${id}/`, { method: 'DELETE' })
export const toggleBanner    = (id, is_active) => apiFetch(`/api/notifications/banners/${id}/`, { method: 'PATCH', body: JSON.stringify({ is_active }) })

// Flash Sales
export const getAdminFlashSales = () => apiFetch('/api/commerce/admin/flash-sales/')
export const createFlashSale    = (data) => apiFetch('/api/commerce/admin/flash-sales/', { method: 'POST', body: JSON.stringify(data) })
export const deleteFlashSale    = (id) => apiFetch(`/api/commerce/admin/flash-sales/${id}/`, { method: 'DELETE' })

// Bundles
export const getAdminBundles = () => apiFetch('/api/commerce/admin/bundles/')
export const createBundle    = (data) => apiFetch('/api/commerce/admin/bundles/', { method: 'POST', body: JSON.stringify(data) })
export const deleteBundle    = (id) => apiFetch(`/api/commerce/admin/bundles/${id}/`, { method: 'DELETE' })

// Campaigns
export const getCampaigns   = () => apiFetch('/api/notifications/campaigns/')
export const createCampaign = (data) => apiFetch('/api/notifications/campaigns/', { method: 'POST', body: JSON.stringify(data) })
export const sendCampaign   = (id) => apiFetch(`/api/notifications/campaigns/${id}/send/`, { method: 'POST' })

// Courses (for flash sale / bundle pickers)
export const getAllCourses = () => apiFetch('/api/courses/')

// Reset customer password
export const resetCustomerPassword = (id) => apiFetch(`/api/auth/customers/${id}/reset-password/`, { method: 'POST' })

// CSV import (center students)
export const previewImport     = (formData) => apiFetch('/api/auth/admin/import/preview/', { method: 'POST', body: formData })
export const confirmImport     = (formData) => apiFetch('/api/auth/admin/import/confirm/', { method: 'POST', body: formData })
export const getImportBatches  = () => apiFetch('/api/auth/admin/import/')
export const getImportBatch    = (id) => apiFetch(`/api/auth/admin/import/${id}/`)
export const getImportTemplate = () => apiFetch('/api/auth/admin/import/template/')

// Materials / revisions (portal Materials/Revisions tabs are read-only — this is how content gets in)
export const getAdminMaterials   = () => apiFetch('/api/courses/admin/materials/')
export const createMaterial      = (formData) => apiFetch('/api/courses/admin/materials/', { method: 'POST', body: formData })
export const updateMaterial      = (id, data) => apiFetch(`/api/courses/admin/materials/${id}/`, { method: 'PATCH', body: JSON.stringify(data) })
export const deleteMaterial      = (id) => apiFetch(`/api/courses/admin/materials/${id}/`, { method: 'DELETE' })
