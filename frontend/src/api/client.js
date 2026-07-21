const BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

async function _refresh() {
  const refresh = localStorage.getItem('refresh')
  if (!refresh) return false
  const res = await fetch(`${BASE}/api/auth/token/refresh/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh }),
  })
  if (!res.ok) return false
  const { access } = await res.json()
  localStorage.setItem('access', access)
  return access
}

export async function apiFetch(path, options = {}) {
  const token = localStorage.getItem('access')
  const isFormData = options.body instanceof FormData
  const headers = {
    ...(!isFormData && { 'Content-Type': 'application/json' }),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  }

  let res = await fetch(`${BASE}${path}`, { ...options, headers })

  if (res.status === 401) {
    const newToken = await _refresh()
    if (newToken) {
      headers.Authorization = `Bearer ${newToken}`
      res = await fetch(`${BASE}${path}`, { ...options, headers })
    } else {
      localStorage.removeItem('access')
      localStorage.removeItem('refresh')
      window.dispatchEvent(new Event('auth:logout'))
    }
  }

  return res
}
