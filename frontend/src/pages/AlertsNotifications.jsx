/**
 * frontend/src/pages/AlertsNotifications.jsx
 */
import React, { useState, useEffect } from 'react'
import { Bell, Filter, Search, CheckCheck, AlertTriangle, Info, CheckCircle } from 'lucide-react'
import api from '../services/api'
import { formatTimestamp } from '../utils/health'
import useNotificationStore from '../store/notificationStore'

export default function AlertsNotifications() {
  const [search, setSearch] = useState('')
  const [severityFilter, setSeverityFilter] = useState('all')
  const { notifications, setNotifications, markRead, markAllRead } = useNotificationStore()

  const load = async () => {
    try {
      const { data } = await api.get('/notifications/?limit=100')
      setNotifications(data)
    } catch (e) {}
  }

  useEffect(() => { load(); const t = setInterval(load, 10000); return () => clearInterval(t) }, [])

  const handleMarkRead = async (id) => {
    await api.post(`/notifications/${id}/read`).catch(() => {})
    markRead(id)
  }

  const handleMarkAllRead = async () => {
    await api.post('/notifications/read-all').catch(() => {})
    markAllRead()
  }

  const filtered = notifications.filter(n => {
    const matchSev = severityFilter === 'all' || n.severity === severityFilter
    const matchSearch = !search || n.title.toLowerCase().includes(search.toLowerCase()) ||
      n.description.toLowerCase().includes(search.toLowerCase())
    return matchSev && matchSearch
  })

  const severityIcon = (s) => ({
    critical: <AlertTriangle size={14} className="text-red-400" />,
    warning: <AlertTriangle size={14} className="text-yellow-400" />,
    info: <Info size={14} className="text-blue-400" />,
    resolved: <CheckCircle size={14} className="text-green-400" />,
  })[s] || <Info size={14} className="text-blue-400" />

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Alerts & Notifications</h1>
          <p className="text-sm text-gray-400 mt-0.5">{notifications.filter(n => !n.is_read).length} unread</p>
        </div>
        <button onClick={handleMarkAllRead} className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-sm text-gray-300 transition-colors">
          <CheckCheck size={14} />
          Mark all read
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <div className="relative flex-1 min-w-48">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search notifications..."
            className="w-full pl-9 pr-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-sm text-white placeholder-gray-500 focus:outline-none focus:border-cyan-500"
          />
        </div>
        <div className="flex gap-1 bg-gray-900 border border-gray-700 rounded-lg p-1">
          {['all', 'critical', 'warning', 'info', 'resolved'].map(f => (
            <button key={f} onClick={() => setSeverityFilter(f)}
              className={`px-3 py-1 rounded text-xs capitalize ${severityFilter === f ? 'bg-cyan-600 text-white' : 'text-gray-400 hover:text-white'}`}>
              {f}
            </button>
          ))}
        </div>
      </div>

      {/* Notification list */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        {filtered.length === 0 ? (
          <div className="text-center py-16 text-gray-500">
            <Bell size={32} className="mx-auto mb-3 opacity-30" />
            No notifications match your filter
          </div>
        ) : (
          <div className="divide-y divide-gray-800">
            {filtered.map(n => (
              <div key={n.id} onClick={() => handleMarkRead(n.id)}
                className={`flex items-start gap-4 p-4 cursor-pointer hover:bg-gray-800/40 transition-colors ${!n.is_read ? 'bg-gray-800/20' : ''}`}>
                <div className="mt-0.5 flex-shrink-0">{severityIcon(n.severity)}</div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-gray-200">{n.title}</span>
                    {!n.is_read && <span className="w-2 h-2 rounded-full bg-cyan-400 flex-shrink-0" />}
                  </div>
                  <p className="text-xs text-gray-400 mt-0.5">{n.description}</p>
                  {n.recommended_action && (
                    <p className="text-xs text-cyan-400/70 mt-1 italic">{n.recommended_action}</p>
                  )}
                  <p className="text-[10px] text-gray-600 mt-1">{formatTimestamp(n.utc_timestamp)}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
