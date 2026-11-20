/**
 * frontend/src/App.jsx
 * Root application component — sets up routing and auth guards.
 */
import React, { useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import Login from './pages/Login'
import Overview from './pages/Overview'
import Infrastructure from './pages/Infrastructure'
import NetworkMonitoring from './pages/NetworkMonitoring'
import SecurityMonitoring from './pages/SecurityMonitoring'
import AIInsights from './pages/AIInsights'
import AlertsNotifications from './pages/AlertsNotifications'
import IncidentManagement from './pages/IncidentManagement'
import CollectorFleet from './pages/CollectorFleet'
import EgressProof from './pages/EgressProof'
import Analytics from './pages/Analytics'
import ActivityTimeline from './pages/ActivityTimeline'
import Settings from './pages/Settings'
import RemediationSimulator from './pages/RemediationSimulator'
import Performance from './pages/Performance'
import useAuthStore from './store/authStore'
import { connectWebSocket } from './services/websocket'
import useNotificationStore from './store/notificationStore'

/** Guard: redirect to /login if not authenticated */
function RequireAuth({ children }) {
  const token = localStorage.getItem('sentinel_token')
  if (!token) return <Navigate to="/login" replace />
  return children
}

function AppRoutes() {
  const { token } = useAuthStore()
  const { addNotification } = useNotificationStore()

  // Connect WebSocket for real-time notifications
  useEffect(() => {
    if (token) {
      return connectWebSocket(token, (data) => {
        if (data.type === 'notification' && data.data) {
          addNotification({ ...data.data, is_read: false })
        }
      })
    }
  }, [token, addNotification])

  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/*" element={
        <RequireAuth>
          <Layout>
            <Routes>
              <Route path="/" element={<Overview />} />
              <Route path="/infrastructure" element={<Infrastructure />} />
              <Route path="/network" element={<NetworkMonitoring />} />
              <Route path="/security" element={<SecurityMonitoring />} />
              <Route path="/ai-insights" element={<AIInsights />} />
              <Route path="/alerts" element={<AlertsNotifications />} />
              <Route path="/incidents" element={<IncidentManagement />} />
              <Route path="/collectors" element={<CollectorFleet />} />
              <Route path="/egress" element={<EgressProof />} />
              <Route path="/analytics" element={<Analytics />} />
              <Route path="/timeline" element={<ActivityTimeline />} />
              <Route path="/remediation" element={<RemediationSimulator />} />
              <Route path="/performance" element={<Performance />} />
              <Route path="/settings" element={<Settings />} />
            </Routes>
          </Layout>
        </RequireAuth>
      } />
    </Routes>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AppRoutes />
    </BrowserRouter>
  )
}
