/**
 * frontend/src/pages/NetworkMonitoring.jsx
 */
import React, { useState, useEffect } from 'react'
import { Network, Wifi, AlertTriangle } from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, ReferenceLine } from 'recharts'
import api from '../services/api'

export default function NetworkMonitoring() {
  const [metrics, setMetrics] = useState([])

  useEffect(() => {
    const load = async () => {
      try {
        const { data } = await api.get('/telemetry/metrics?category=network&minutes=60')
        setMetrics(data)
      } catch (e) {}
    }
    load(); const t = setInterval(load, 10000); return () => clearInterval(t)
  }, [])

  const chartData = metrics
    .sort((a, b) => a.event_time.localeCompare(b.event_time))
    .slice(-40)
    .map(m => ({ time: m.event_time.substring(11, 19), latency: m.value, source: m.source_id }))

  const latestLatency = chartData.at(-1)?.latency || 0
  const status = latestLatency > 500 ? 'Critical' : latestLatency > 200 ? 'Elevated' : 'Normal'
  const statusColor = latestLatency > 500 ? 'text-red-400' : latestLatency > 200 ? 'text-yellow-400' : 'text-green-400'

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-white">Network Monitoring</h1>
        <p className="text-sm text-gray-400 mt-0.5">Latency, bandwidth, and connectivity metrics</p>
      </div>

      <div className="grid grid-cols-3 gap-4">
        {[
          { label: 'Network Latency', value: `${latestLatency.toFixed(1)}ms`, color: statusColor },
          { label: 'Status', value: status, color: statusColor },
          { label: 'Data Points', value: metrics.length, color: 'text-cyan-400' },
        ].map(({ label, value, color }) => (
          <div key={label} className="bg-gray-900 border border-gray-800 rounded-xl p-5">
            <p className="text-xs text-gray-500 uppercase tracking-wide">{label}</p>
            <p className={`text-2xl font-bold mt-1 ${color}`}>{value}</p>
          </div>
        ))}
      </div>

      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <h3 className="text-sm font-semibold text-gray-200 mb-4 flex items-center gap-2">
          <Network size={14} className="text-green-400" />
          Network Latency Over Time (ms)
        </h3>
        {chartData.length === 0 ? (
          <div className="h-48 flex items-center justify-center text-gray-500 text-sm">No network data yet</div>
        ) : (
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
              <XAxis dataKey="time" tick={{ fontSize: 10, fill: '#6b7280' }} />
              <YAxis tick={{ fontSize: 10, fill: '#6b7280' }} />
              <Tooltip contentStyle={{ backgroundColor: '#111827', border: '1px solid #374151', borderRadius: '8px' }} />
              <ReferenceLine y={200} stroke="#eab308" strokeDasharray="4 4" label={{ value: 'Warn', fontSize: 10, fill: '#eab308' }} />
              <ReferenceLine y={500} stroke="#ef4444" strokeDasharray="4 4" label={{ value: 'Crit', fontSize: 10, fill: '#ef4444' }} />
              <Line type="monotone" dataKey="latency" stroke="#22c55e" dot={false} strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  )
}
