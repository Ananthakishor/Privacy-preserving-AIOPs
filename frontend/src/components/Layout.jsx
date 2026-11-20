/**
 * frontend/src/components/Layout.jsx
 * Dark sidebar navigation layout with notification bell in header.
 */
import React, { useState } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard, Server, Network, Shield, Brain, Bell,
  AlertTriangle, GitMerge, Radio, Lock, BarChart3, Clock,
  Settings, LogOut, Menu, X, Zap, ChevronRight, PlayCircle, Activity
} from 'lucide-react'
import NotificationBell from './NotificationBell'
import useAuthStore from '../store/authStore'
import api from '../services/api'

const NAV_ITEMS = [
  { to: '/', icon: LayoutDashboard, label: 'Overview' },
  { to: '/infrastructure', icon: Server, label: 'Infrastructure' },
  { to: '/network', icon: Network, label: 'Network Monitoring' },
  { to: '/security', icon: Shield, label: 'Security Monitoring' },
  { to: '/ai-insights', icon: Brain, label: 'AI Insights' },
  { to: '/alerts', icon: Bell, label: 'Alerts & Notifications' },
  { to: '/incidents', icon: GitMerge, label: 'Incident Management' },
  { to: '/collectors', icon: Radio, label: 'Collector Fleet' },
  { to: '/egress', icon: Lock, label: 'Egress Proof / Privacy' },
  { to: '/analytics', icon: BarChart3, label: 'Analytics & Reports' },
  { to: '/timeline', icon: Clock, label: 'Activity Timeline' },
  { to: '/remediation', icon: PlayCircle, label: 'Remediation Sim' },
  { to: '/performance', icon: Activity, label: 'Performance' },
  { to: '/settings', icon: Settings, label: 'Settings' },
]

export default function Layout({ children }) {
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()

  const handleLogout = async () => {
    try { await api.post('/auth/logout') } catch (e) {}
    logout()
    navigate('/login')
  }

  return (
    <div className="flex h-screen bg-gray-950 overflow-hidden">
      {/* Sidebar */}
      <aside className={`${sidebarOpen ? 'w-64' : 'w-16'} flex-shrink-0 bg-gray-900 border-r border-gray-800 transition-all duration-200 flex flex-col`}>
        {/* Logo */}
        <div className="flex items-center gap-3 px-4 h-16 border-b border-gray-800">
          <div className="w-8 h-8 rounded-lg bg-cyan-500/20 border border-cyan-500/40 flex items-center justify-center flex-shrink-0">
            <Zap size={16} className="text-cyan-400" />
          </div>
          {sidebarOpen && (
            <div>
              <div className="text-sm font-bold text-white">SentinelOps</div>
              <div className="text-[10px] text-cyan-400/60 uppercase tracking-wider">AI Platform</div>
            </div>
          )}
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto py-3 px-2 space-y-0.5">
          {NAV_ITEMS.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all group ${
                  isActive
                    ? 'bg-cyan-500/15 text-cyan-400 border border-cyan-500/25'
                    : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800/60'
                }`
              }
              title={!sidebarOpen ? label : ''}
            >
              <Icon size={16} className="flex-shrink-0" />
              {sidebarOpen && <span className="truncate">{label}</span>}
            </NavLink>
          ))}
        </nav>

        {/* User info */}
        <div className="p-3 border-t border-gray-800">
          {sidebarOpen ? (
            <div className="flex items-center gap-2 px-2 py-1.5 rounded-lg">
              <div className="w-7 h-7 rounded-full bg-cyan-500/20 flex items-center justify-center text-xs font-bold text-cyan-400">
                {user?.email?.[0]?.toUpperCase() || 'U'}
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-xs font-medium text-gray-300 truncate">{user?.email || 'User'}</div>
                <div className="text-[10px] text-gray-500 capitalize">{user?.role || 'viewer'}</div>
              </div>
              <button onClick={handleLogout} className="text-gray-500 hover:text-red-400 transition-colors" title="Logout">
                <LogOut size={14} />
              </button>
            </div>
          ) : (
            <button onClick={handleLogout} className="w-full flex justify-center text-gray-500 hover:text-red-400 py-1" title="Logout">
              <LogOut size={16} />
            </button>
          )}
        </div>
      </aside>

      {/* Main content area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top header */}
        <header className="h-16 flex items-center justify-between px-4 bg-gray-900 border-b border-gray-800 flex-shrink-0">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-2 rounded-lg text-gray-400 hover:text-white hover:bg-gray-800 transition-colors"
          >
            {sidebarOpen ? <X size={18} /> : <Menu size={18} />}
          </button>

          <div className="flex items-center gap-3">
            {/* Live indicator */}
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-green-500/10 border border-green-500/25">
              <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
              <span className="text-xs text-green-400 font-medium">LIVE</span>
            </div>

            <NotificationBell />
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto p-6 bg-gray-950">
          {children}
        </main>
      </div>
    </div>
  )
}
