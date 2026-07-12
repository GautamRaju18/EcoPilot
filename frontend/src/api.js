// Tiny fetch wrapper. Token is kept in localStorage and attached to every call.
const TOKEN_KEY = 'ecopilot_token'

export const getToken = () => localStorage.getItem(TOKEN_KEY)
export const setToken = (t) => localStorage.setItem(TOKEN_KEY, t)
export const clearToken = () => localStorage.removeItem(TOKEN_KEY)

async function request(path, { method = 'GET', body, form, isForm } = {}) {
  const headers = {}
  const token = getToken()
  if (token) headers['Authorization'] = `Bearer ${token}`

  let payload
  if (isForm) {
    payload = form // FormData or URLSearchParams — browser sets content-type
  } else if (body !== undefined) {
    headers['Content-Type'] = 'application/json'
    payload = JSON.stringify(body)
  }

  const res = await fetch(`/api${path}`, { method, headers, body: payload })
  if (res.status === 401) {
    clearToken()
    if (!location.pathname.startsWith('/login')) location.href = '/login'
    throw new Error('Unauthorized')
  }
  const text = await res.text()
  const data = text ? JSON.parse(text) : null
  if (!res.ok) throw new Error(data?.detail || `Request failed (${res.status})`)
  return data
}

export const api = {
  get: (p) => request(p),
  post: (p, body) => request(p, { method: 'POST', body }),
  put: (p, body) => request(p, { method: 'PUT', body }),
  del: (p) => request(p, { method: 'DELETE' }),

  // login uses OAuth2 form encoding
  login: (email, password) => {
    const form = new URLSearchParams({ username: email, password })
    return request('/auth/login', { method: 'POST', form, isForm: true })
  },
  // multipart (proof upload)
  postForm: (p, formData) => request(p, { method: 'POST', form: formData, isForm: true }),
}
