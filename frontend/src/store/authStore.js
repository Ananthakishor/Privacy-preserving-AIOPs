/**
 * frontend/src/store/authStore.js
 * Zustand store for authentication state.
 */
import { create } from 'zustand'

const useAuthStore = create((set) => ({
  token: localStorage.getItem('sentinel_token') || null,
  user: JSON.parse(localStorage.getItem('sentinel_user') || 'null'),

  login: (token, user) => {
    localStorage.setItem('sentinel_token', token)
    localStorage.setItem('sentinel_user', JSON.stringify(user))
    set({ token, user })
  },

  logout: () => {
    localStorage.removeItem('sentinel_token')
    localStorage.removeItem('sentinel_user')
    set({ token: null, user: null })
  },

  isAuthenticated: () => !!localStorage.getItem('sentinel_token'),
}))

export default useAuthStore
