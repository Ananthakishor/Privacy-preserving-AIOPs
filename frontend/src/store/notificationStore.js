/**
 * frontend/src/store/notificationStore.js
 * Zustand store for notification state including unread count.
 */
import { create } from 'zustand'

const useNotificationStore = create((set, get) => ({
  notifications: [],
  unreadCount: 0,

  setNotifications: (notifications) => set({
    notifications,
    unreadCount: notifications.filter(n => !n.is_read).length
  }),

  addNotification: (notification) => set((state) => ({
    notifications: [notification, ...state.notifications].slice(0, 100),
    unreadCount: state.unreadCount + (notification.is_read ? 0 : 1),
  })),

  markRead: (id) => set((state) => ({
    notifications: state.notifications.map(n =>
      n.id === id ? { ...n, is_read: true } : n
    ),
    unreadCount: Math.max(0, state.unreadCount - 1),
  })),

  markAllRead: () => set((state) => ({
    notifications: state.notifications.map(n => ({ ...n, is_read: true })),
    unreadCount: 0,
  })),

  setUnreadCount: (count) => set({ unreadCount: count }),
}))

export default useNotificationStore
