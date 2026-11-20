/**
 * frontend/src/components/NotificationBell.jsx
 * Notification bell icon with unread count badge and slide-out panel.
 */
import React, { useState, useEffect, useRef } from 'react'
import { Bell, X, CheckCheck, AlertTriangle, Info, CheckCircle } from 'lucide-react'
import useNotificationStore from '../store/notificationStore'
import api from '../services/api'
import { formatTimestamp, getSeverityConfig } from '../utils/health'

const SEVERITY_ICONS = {
  critical: <AlertTriangle size={14} className="text-red-400" />,
  warning: <AlertTriangle size={14} className="text-yellow-400" />,
  info: <Info size={14} className="text-blue-400" />,
  resolved: <CheckCircle size={14} className="text-green-400" />,
}

export default function NotificationBell() {
  const [open, setOpen] = useState(false)
  const [filter, setFilter] = useState('all')
  const { notifications, unreadCount, setNotifications, markRead, markAllRead, setUnreadCount } = useNotificationStore()
  const panelRef = useRef(null)

  // Load notifications on mount and periodically
  const loadNotifications = async () => {
    try {
      const { data } = await api.get('/notifications/?limit=50')
      setNotifications(data)
    } catch (e) {}
    try {
      const { data } = await api.get('/notifications/unread-count')
      setUnreadCount(data.count)
    } catch (e) {}
  }

  useEffect(() => {
    loadNotifications()
    const interval = setInterval(loadNotifications, 15000)
    return () => clearInterval(interval)
  }, [])

  // Close panel when clicking outside
  useEffect(() => {
    const handler = (e) => {
      if (panelRef.current && !panelRef.current.contains(e.target)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const handleMarkRead = async (id) => {
    await api.post(`/notifications/${id}/read`)
    markRead(id)
  }

  const handleMarkAllRead = async () => {
    await api.post('/notifications/read-all')
    markAllRead()
  }

  const filtered = filter === 'all'
    ? notifications
    : notifications.filter(n => n.severity === filter)

  return (
    <div className="relative" ref={panelRef}>
      {/* Bell button */}
      <button
        onClick={() => setOpen(!open)}
        className="relative p-2 rounded-lg text-gray-400 hover:text-white hover:bg-gray-800 transition-colors"
        title="Notifications"
      >
        <Bell size={20} />
        {unreadCount > 0 && (
          <span className="absolute -top-1 -right-1 min-w-[18px] h-[18px] flex items-center justify-center rounded-full bg-red-500 text-white text-[10px] font-bold px-1">
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>

      {/* Notification panel */}
      {open && (
        <div className="absolute right-0 top-12 w-96 max-h-[80vh] flex flex-col bg-gray-900 border border-gray-700 rounded-xl shadow-2xl z-50 overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700">
            <div className="flex items-center gap-2">
              <Bell size={16} className="text-cyan-400" />
              <span className="font-semibold text-sm">Notifications</span>
              {unreadCount > 0 && (
                <span className="px-2 py-0.5 rounded-full bg-red-500/20 text-red-400 text-xs font-medium">
                  {unreadCount} unread
                </span>
              )}
            </div>
            <div className="flex items-center gap-2">
              {unreadCount > 0 && (
                <button
                  onClick={handleMarkAllRead}
                  className="flex items-center gap-1 text-xs text-gray-400 hover:text-cyan-400 transition-colors"
                  title="Mark all as read"
                >
                  <CheckCheck size={14} />
                  All read
                </button>
              )}
              <button onClick={() => setOpen(false)} className="text-gray-400 hover:text-white">
                <X size={16} />
              </button>
            </div>
          </div>

          {/* Severity filter */}
          <div className="flex gap-1 px-3 py-2 border-b border-gray-800">
            {['all', 'critical', 'warning', 'info', 'resolved'].map(f => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-2 py-1 rounded text-xs capitalize transition-colors ${
                  filter === f
                    ? 'bg-cyan-500/20 text-cyan-400'
                    : 'text-gray-500 hover:text-gray-300'
                }`}
              >
                {f}
              </button>
            ))}
          </div>

          {/* Notification list */}
          <div className="overflow-y-auto flex-1">
            {filtered.length === 0 ? (
              <div className="text-center text-gray-500 text-sm py-8">
                No notifications
              </div>
            ) : (
              filtered.map(n => (
                <div
                  key={n.id}
                  onClick={() => handleMarkRead(n.id)}
                  className={`px-4 py-3 border-b border-gray-800 cursor-pointer hover:bg-gray-800/50 transition-colors ${
                    !n.is_read ? 'bg-gray-800/30' : ''
                  }`}
                >
                  <div className="flex items-start gap-2">
                    <div className="mt-0.5 flex-shrink-0">
                      {SEVERITY_ICONS[n.severity] || SEVERITY_ICONS.info}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-semibold text-gray-200 truncate">{n.title}</span>
                        {!n.is_read && (
                          <span className="w-2 h-2 rounded-full bg-cyan-400 flex-shrink-0" />
                        )}
                      </div>
                      <p className="text-xs text-gray-400 mt-0.5 line-clamp-2">{n.description}</p>
                      {n.recommended_action && (
                        <p className="text-xs text-cyan-400/70 mt-1 italic line-clamp-1">
                          {n.recommended_action}
                        </p>
                      )}
                      <span className="text-[10px] text-gray-600 mt-1 block">
                        {formatTimestamp(n.utc_timestamp)}
                      </span>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  )
}
