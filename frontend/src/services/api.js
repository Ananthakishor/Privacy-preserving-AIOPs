/**
 * frontend/src/services/api.js
 * Axios instance with JWT auth interceptor and base URL.
 */
import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 15000,
})

// Attach JWT token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('sentinel_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Handle 401 by redirecting to login
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('sentinel_token')
      localStorage.removeItem('sentinel_user')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default api
