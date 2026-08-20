// Requests go through Vite's dev-server proxy (vite.config.js) instead of
// straight to http://127.0.0.1:8000. The backend has no CORS middleware and
// we're not allowed to touch app/ to add one, so a direct cross-origin fetch
// from the browser would be blocked. Proxying makes every request
// same-origin instead. If the backend ever moves, update the proxy target,
// not this constant.
export const API_BASE = '/api'

async function request(method, path, { body, token } = {}) {
  const headers = {}
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  if (token) headers['Authorization'] = `Bearer ${token}`

  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })

  if (!res.ok) {
    // detail is sometimes a plain string, sometimes {message, problems: [...]}
    // (see POST /orders oversell errors) — flatten either shape to one string.
    let message = res.statusText
    try {
      const data = await res.json()
      if (typeof data.detail === 'string') {
        message = data.detail
      } else if (data.detail?.message) {
        message = data.detail.message
        if (data.detail.problems) {
          message += ': ' + data.detail.problems.map((p) => p.error).join(', ')
        }
      }
    } catch {
      // not JSON — keep statusText
    }
    throw new Error(message)
  }

  if (res.status === 204) return null
  return res.json()
}

export const api = {
  get: (path, opts) => request('GET', path, opts),
  post: (path, body, opts) => request('POST', path, { ...opts, body }),
  put: (path, body, opts) => request('PUT', path, { ...opts, body }),
  patch: (path, body, opts) => request('PATCH', path, { ...opts, body }),
  del: (path, opts) => request('DELETE', path, opts),
}
