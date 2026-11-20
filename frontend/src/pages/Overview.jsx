/**
 * frontend/src/pages/Overview.jsx
 * Main dashboard — summary cards + live metric charts.
 * Data is fetched from real backend APIs, not hard-coded.
 */
import React, { useState, useEffect } from 'react'
import {
  Server, Activity, AlertTriangle, Wifi, Cpu, MemoryStick,
  TrendingUp, Users, CheckCircle, XCircle, Radio, GitMerge
} from 'lucide-react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, AreaChart, Area, Legend
} from 'recharts'
import api from '../services/api'
import { getHealthConfig, formatTimestamp } from '../utils/health'

const CHART_COLORS = {
  cpu: '#06b6d4',
  memory: '#8b5cf6',
  disk: '#f97316',
  network: '#22c55e',
}

function StatCard({ icon: Icon, label, value, sub, color = 'text-cyan-400', bg = 'bg-cyan-400/10' }) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 hover:border-gray-700 transition-colors">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs text-gray-500 uppercase tracking-wide font-medium">{label}</p>
          <p className={`text-2xl font-bold mt-1 ${color}`}>{value ?? '—'}</p>
          {sub && <p className="text-xs text-gray-500 mt-1">{sub}</p>}
        </div>
        <div className={`w-10 h-10 rounded-lg ${bg} flex items-center justify-center`}>
          <Icon size={18} className={color} />
        </div>
      </div>
    </div>
  )
}

function HealthBadge({ state }) {
  const cfg = getHealthConfig(state)
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium ${cfg.badge}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${cfg.dot}`} />
      {cfg.label}
    </span>
  )
}

export default function Overview() {
  const [metrics, setMetrics] = useState([])
  const [alerts, setAlerts] = useState([])
  const [incidents, setIncidents] = useState([])
  const [collectors, setCollectors] = useState([])
  const [loading, setLoading] = useState(true)
  const [timeRange, setTimeRange] = useState(60) // minutes

  const loadData = async () => {
    try {
      const [metricsRes, alertsRes, incidentsRes, collectorsRes] = await Promise.allSettled([
        api.get(`/telemetry/metrics?minutes=${timeRange}`),
        api.get('/alerts/?limit=20'),
        api.get('/incidents/?status=open&limit=10'),
        api.get('/collectors/'),
      ])
      if (metricsRes.status === 'fulfilled') setMetrics(metricsRes.value.data)
      if (alertsRes.status === 'fulfilled') setAlerts(alertsRes.value.data)
      if (incidentsRes.status === 'fulfilled') setIncidents(incidentsRes.value.data)
      if (collectorsRes.status === 'fulfilled') setCollectors(collectorsRes.value.data)
    } catch (e) {
      console.error('Failed to load overview data', e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
    const interval = setInterval(loadData, 10000) // refresh every 10s
    return () => clearInterval(interval)
  }, [timeRange])

  // Build chart data: group metrics by source + category, latest 30 points
  const buildChartData = (category) => {
    const catMetrics = metrics
      .filter(m => m.category === category)
      .sort((a, b) => a.event_time.localeCompare(b.event_time))

    // Get unique sources
    const sources = [...new Set(catMetrics.map(m => m.source_id))]

    // Build time series grouped by time (take last 30 unique timestamps)
    const timeMap = {}
    catMetrics.forEach(m => {
      const t = m.event_time.substring(11, 19) // HH:MM:SS
      if (!timeMap[t]) timeMap[t] = { time: t }
      timeMap[t][m.source_id] = m.value
    })

    return { data: Object.values(timeMap).slice(-30), sources }
  }

  // Summary stats
  const criticalAlerts = alerts.filter(a => a.severity === 'critical').length
  const warningAlerts = alerts.filter(a => a.severity === 'warning').length
  const onlineCollectors = collectors.filter(c => c.status === 'online').length
  const sources = [...new Set(metrics.map(m => m.source_id))]

  // Average values from latest metrics per source
  const latestByCatSource = {}
  metrics.forEach(m => {
    const key = `${m.source_id}-${m.category}`
    if (!latestByCatSource[key] || m.event_time > latestByCatSource[key].event_time) {
      latestByCatSource[key] = m
    }
  })
  const cpuValues = Object.values(latestByCatSource).filter(m => m.category === 'cpu').map(m => m.value)
  const memValues = Object.values(latestByCatSource).filter(m => m.category === 'memory').map(m => m.value)
  const avgCpu = cpuValues.length ? Math.round(cpuValues.reduce((a, b) => a + b, 0) / cpuValues.length) : 0
  const avgMem = memValues.length ? Math.round(memValues.reduce((a, b) => a + b, 0) / memValues.length) : 0

  // Determine overall health
  const overallHealth = criticalAlerts > 0 ? 'poor' : warningAlerts > 2 ? 'fair' : avgCpu > 80 ? 'fair' : 'excellent'

  const cpuChart = buildChartData('cpu')
  const memChart = buildChartData('memory')

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-gray-400 text-sm">Loading dashboard...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Operations Overview</h1>
          <p className="text-sm text-gray-400 mt-0.5">Real-time infrastructure health and metrics</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1 bg-gray-800 rounded-lg p-1">
            {[15, 60, 240].map(m => (
              <button
                key={m}
                onClick={() => setTimeRange(m)}
                className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                  timeRange === m ? 'bg-cyan-600 text-white' : 'text-gray-400 hover:text-white'
                }`}
              >
                {m < 60 ? `${m}m` : `${m/60}h`}
              </button>
            ))}
          </div>
          <HealthBadge state={overallHealth} />
        </div>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <StatCard icon={Server} label="Monitored Servers" value={sources.length} sub="active sources" />
        <StatCard icon={Radio} label="Online Collectors" value={onlineCollectors} sub={`of ${collectors.length} total`} color="text-green-400" bg="bg-green-400/10" />
        <StatCard icon={AlertTriangle} label="Critical Alerts" value={criticalAlerts} sub="unacknowledged" color="text-red-400" bg="bg-red-400/10" />
        <StatCard icon={AlertTriangle} label="Warning Alerts" value={warningAlerts} sub="unacknowledged" color="text-yellow-400" bg="bg-yellow-400/10" />
        <StatCard icon={GitMerge} label="Active Incidents" value={incidents.length} sub="open" color="text-orange-400" bg="bg-orange-400/10" />
        <StatCard icon={Cpu} label="Avg CPU" value={`${avgCpu}%`} sub={`Avg Mem: ${avgMem}%`} color="text-cyan-400" />
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* CPU Chart */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-gray-200 mb-4 flex items-center gap-2">
            <Cpu size={14} className="text-cyan-400" />
            CPU Usage Over Time
          </h3>
          {cpuChart.data.length === 0 ? (
            <div className="h-40 flex items-center justify-center text-gray-500 text-sm">No data yet — start the collector</div>
          ) : (
            <ResponsiveContainer width="100%" height={160}>
              <AreaChart data={cpuChart.data}>
                <defs>
                  {cpuChart.sources.map((s, i) => (
                    <linearGradient key={s} id={`cpuGrad${i}`} x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={CHART_COLORS.cpu} stopOpacity={0.3} />
                      <stop offset="95%" stopColor={CHART_COLORS.cpu} stopOpacity={0.0} />
                    </linearGradient>
                  ))}
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                <XAxis dataKey="time" tick={{ fontSize: 10, fill: '#6b7280' }} />
                <YAxis domain={[0, 100]} tick={{ fontSize: 10, fill: '#6b7280' }} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#111827', border: '1px solid #374151', borderRadius: '8px', fontSize: '12px' }}
                  labelStyle={{ color: '#9ca3af' }}
                />
                {cpuChart.sources.map((s, i) => (
                  <Area key={s} type="monotone" dataKey={s} stroke={CHART_COLORS.cpu} fill={`url(#cpuGrad${i})`} dot={false} strokeWidth={2} />
                ))}
              </AreaChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Memory Chart */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-gray-200 mb-4 flex items-center gap-2">
            <Activity size={14} className="text-purple-400" />
            Memory Usage Over Time
          </h3>
          {memChart.data.length === 0 ? (
            <div className="h-40 flex items-center justify-center text-gray-500 text-sm">No data yet</div>
          ) : (
            <ResponsiveContainer width="100%" height={160}>
              <AreaChart data={memChart.data}>
                <defs>
                  <linearGradient id="memGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                <XAxis dataKey="time" tick={{ fontSize: 10, fill: '#6b7280' }} />
                <YAxis domain={[0, 100]} tick={{ fontSize: 10, fill: '#6b7280' }} />
                <Tooltip contentStyle={{ backgroundColor: '#111827', border: '1px solid #374151', borderRadius: '8px', fontSize: '12px' }} />
                {memChart.sources.map(s => (
                  <Area key={s} type="monotone" dataKey={s} stroke="#8b5cf6" fill="url(#memGrad)" dot={false} strokeWidth={2} />
                ))}
              </AreaChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* Recent alerts + incidents */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Alerts */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-gray-200 mb-4 flex items-center gap-2">
            <AlertTriangle size={14} className="text-yellow-400" />
            Recent Alerts
          </h3>
          {alerts.length === 0 ? (
            <div className="text-center py-8 text-gray-500 text-sm">
              <CheckCircle size={24} className="text-green-400 mx-auto mb-2" />
              No active alerts
            </div>
          ) : (
            <div className="space-y-2">
              {alerts.slice(0, 5).map(alert => (
                <div key={alert.id} className="flex items-start gap-3 p-3 rounded-lg bg-gray-800/50 border border-gray-700/50">
                  <span className={`mt-0.5 text-xs font-bold uppercase px-1.5 py-0.5 rounded ${
                    alert.severity === 'critical' ? 'bg-red-900/50 text-red-400' :
                    alert.severity === 'warning' ? 'bg-yellow-900/50 text-yellow-400' :
                    'bg-blue-900/50 text-blue-400'
                  }`}>
                    {alert.severity?.[0].toUpperCase()}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs text-gray-300 leading-relaxed line-clamp-2">{alert.message}</p>
                    <p className="text-[10px] text-gray-500 mt-1">{alert.source_id}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Open Incidents */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-gray-200 mb-4 flex items-center gap-2">
            <GitMerge size={14} className="text-orange-400" />
            Open Incidents
          </h3>
          {incidents.length === 0 ? (
            <div className="text-center py-8 text-gray-500 text-sm">
              <CheckCircle size={24} className="text-green-400 mx-auto mb-2" />
              No open incidents
            </div>
          ) : (
            <div className="space-y-2">
              {incidents.slice(0, 5).map(inc => (
                <div key={inc.id} className="p-3 rounded-lg bg-gray-800/50 border border-gray-700/50">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-medium text-gray-200 truncate">{inc.title}</span>
                    <HealthBadge state={inc.severity === 'critical' ? 'poor' : inc.severity === 'warning' ? 'fair' : 'good'} />
                  </div>
                  <p className="text-[10px] text-gray-500">Source: {inc.source_id} · {formatTimestamp(inc.created_at)}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
