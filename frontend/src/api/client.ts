import axios from 'axios'

const rawBaseUrl = (import.meta.env.VITE_API_URL || '').trim()
const cleanedBaseUrl = rawBaseUrl.replace(/\/+$/, '')
const baseURL = cleanedBaseUrl
  ? (cleanedBaseUrl.endsWith('/api') ? cleanedBaseUrl : `${cleanedBaseUrl}/api`)
  : '/api'

const api = axios.create({
  baseURL,
  headers: {
    'Content-Type': 'application/json',
  },
})

export default api
