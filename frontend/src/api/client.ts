import axios from 'axios'

function resolveApiBaseUrl(rawValue?: string): string {
  let value = (rawValue || '').trim()

  // Defensive normalization for malformed env inputs from CLI/CI.
  value = value.replace(/^['"]|['"]$/g, '')
  value = value.replace(/\\n/g, '').replace(/\n/g, '').replace(/\s+/g, '')
  value = value.replace(/^http:\/\//i, 'https://')

  if (value && value.startsWith('/')) {
    return value.endsWith('/api') ? value : `${value}/api`
  }

  if (value) {
    try {
      const parsed = new URL(value)
      parsed.protocol = 'https:'
      parsed.hash = ''
      const cleaned = parsed.toString().replace(/\/+$/, '')
      return cleaned.endsWith('/api') ? cleaned : `${cleaned}/api`
    } catch {
      // Fall through to production/dev defaults below.
    }
  }

  if (import.meta.env.PROD) {
    return 'https://3pl-dash-production.up.railway.app/api'
  }
  return '/api'
}

const baseURL = resolveApiBaseUrl(import.meta.env.VITE_API_URL)

const api = axios.create({
  baseURL,
  headers: {
    'Content-Type': 'application/json',
  },
})

export default api
