import { apiFetch } from './client'

export const getAuditLogs = (params = {}) => apiFetch(`/api/audit/logs/?${new URLSearchParams(params)}`)
