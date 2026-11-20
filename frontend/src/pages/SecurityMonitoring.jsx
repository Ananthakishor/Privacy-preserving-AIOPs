/**
 * frontend/src/pages/SecurityMonitoring.jsx
 */
import React, { useState, useEffect } from 'react'
import { Shield, AlertTriangle, Eye } from 'lucide-react'
import api from '../services/api'
import { formatTimestamp, getSeverityConfig } from '../utils/health'

export default function SecurityMonitoring() {
  const [alerts, setAlerts] = useState([])
  const [secMetrics, setSecMetrics] = useState([])

  useEffect(() => {
    const load = async () => {
      try {
        const [a, m] = await Promise.all([
          api.get('/alerts/?limit=20'),
          api.get('/telemetry/metrics?category=security&minutes=60'),
        ])
        setAlerts(a.data.filter(a => a.metric_category === 'security' || a.alert_type === 'anomaly'))
        setSecMetrics(m.data)
      } catch (e) {}
    }
    load(); const t = setInterval(load, 15000); return () => clearInterval(t)
  }, [])

  const latestFailedLogins = secMetrics.length > 0 ? secMetrics.at(-1).value : 0

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-white">Security Monitoring</h1>
        <p className="text-sm text-gray-400 mt-0.5">Authentication failures, suspicious activity summaries</p>
      </div>

      <div className="p-4 rounded-xl bg-blue-900/10 border border-blue-500/20">
        <div className="flex items-center gap-2 text-blue-400 text-sm font-medium mb-1">
          <Shield size={14} />
          Privacy Notice
        </div>
        <p className="text-xs text-gray-400">
          Raw authentication logs, usernames, and IP addresses remain on the local collector.
          Only aggregated counts and severity summaries are transmitted here.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <p className="text-xs text-gray-500 uppercase tracking-wide">Failed Login Count (last window)</p>
          <p className={`text-3xl font-bold mt-1 ${latestFailedLogins >= 10 ? 'text-red-400' : latestFailedLogins >= 5 ? 'text-yellow-400' : 'text-green-400'}`}>
            {Math.round(latestFailedLogins)}
          </p>
          <p className="text-xs text-gray-500 mt-1">Count only — no raw credentials stored here</p>
        </div>
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <p className="text-xs text-gray-500 uppercase tracking-wide">Security Alerts</p>
          <p className="text-3xl font-bold mt-1 text-orange-400">{alerts.length}</p>
          <p className="text-xs text-gray-500 mt-1">Flagged anomalies from collector summaries</p>
        </div>
      </div>

      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <h3 className="text-sm font-semibold text-gray-200 mb-4 flex items-center gap-2">
          <AlertTriangle size={14} className="text-red-400" /> Security Alerts
        </h3>
        {alerts.length === 0 ? (
          <div className="text-center py-8 text-gray-500 text-sm">No security alerts</div>
        ) : alerts.map(a => (
          <div key={a.id} className="flex items-start gap-3 p-3 rounded-lg bg-gray-800/50 border border-gray-700/50 mb-2">
            <AlertTriangle size={14} className={a.severity === 'critical' ? 'text-red-400' : 'text-yellow-400'} />
            <div>
              <p className="text-xs text-gray-200">{a.message}</p>
              <p className="text-[10px] text-gray-500 mt-1">{a.source_id} · {formatTimestamp(a.created_at)}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
