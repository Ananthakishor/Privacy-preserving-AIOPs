/**
 * frontend/src/pages/Infrastructure.jsx
 * Server and infrastructure health monitoring page.
 */
import React, { useState, useEffect } from 'react'
import { Server, Cpu, HardDrive, Activity, RefreshCw } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import api from '../services/api'
import { getHealthConfig, formatTimestamp } from '../utils/health'

function classifyHealth(latest) {
  const cpu = latest.cpu || 0, mem = latest.memory || 0
  if (cpu >= 90 || mem >= 90) return 'poor'
  if (cpu >= 75 || mem >= 80) return 'fair'
  if (cpu >= 60 || mem >= 70) return 'good'
  return 'excellent'
}

export default function Infrastructure() {
  const [metrics, setMetrics] = useState([])
  const [loading, setLoading] = useState(true)

  const load = async () => {
    try {
      const { data } = await api.get('/telemetry/metrics?minutes=15')
      setMetrics(data)
    } catch (e) {}
    finally { setLoading(false) }
  }

  useEffect(() => { load(); const t = setInterval(load, 10000); return () => clearInterval(t) }, [])

  // Build per-source summary
  const sourceMap = {}
  metrics.forEach(m => {
    if (!sourceMap[m.source_id]) sourceMap[m.source_id] = {}
    sourceMap[m.source_id][m.category] = m.value
  })

  const sources = Object.entries(sourceMap).map(([id, vals]) => ({
    id, ...vals, health: classifyHealth(vals)
  }))

  const barData = sources.map(s => ({
    name: s.id.replace('src-', ''),
    CPU: Math.round(s.cpu || 0),
    Memory: Math.round(s.memory || 0),
    Disk: Math.round(s.disk || 0),
  }))

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Infrastructure</h1>
          <p className="text-sm text-gray-400 mt-0.5">Server and application health monitoring</p>
        </div>
        <button onClick={load} className="p-2 rounded-lg text-gray-400 hover:text-white hover:bg-gray-800">
          <RefreshCw size={16} />
        </button>
      </div>

      {/* Server cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {sources.length === 0 ? (
          <div className="col-span-3 text-center py-16 text-gray-500">
            <Server size={32} className="mx-auto mb-3 opacity-30" />
            <p>No server data yet — start the collector or simulator</p>
          </div>
        ) : sources.map(s => {
          const cfg = getHealthConfig(s.health)
          return (
            <div key={s.id} className={`bg-gray-900 border rounded-xl p-5 ${cfg.border}`}>
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <Server size={16} className={cfg.color} />
                  <span className="font-medium text-sm text-white">{s.id}</span>
                </div>
                <span className={`text-xs font-medium px-2 py-0.5 rounded ${cfg.badge}`}>{cfg.label}</span>
              </div>
              <div className="grid grid-cols-3 gap-3">
                {[
                  { label: 'CPU', value: s.cpu, color: 'text-cyan-400', icon: Cpu },
                  { label: 'Memory', value: s.memory, color: 'text-purple-400', icon: Activity },
                  { label: 'Disk', value: s.disk, color: 'text-orange-400', icon: HardDrive },
                ].map(({ label, value, color, icon: Icon }) => (
                  <div key={label} className="text-center">
                    <div className={`text-lg font-bold ${color}`}>{value ? `${Math.round(value)}%` : '—'}</div>
                    <div className="text-[10px] text-gray-500 mt-0.5">{label}</div>
                    <div className="mt-1 h-1 bg-gray-800 rounded-full overflow-hidden">
                      <div className={`h-full rounded-full transition-all ${
                        (value || 0) >= 90 ? 'bg-red-500' :
                        (value || 0) >= 75 ? 'bg-yellow-500' : 'bg-cyan-500'
                      }`} style={{ width: `${Math.min(value || 0, 100)}%` }} />
                    </div>
                  </div>
                ))}
              </div>
              <div className="mt-3 text-xs text-gray-500">
                Network latency: <span className="text-gray-300">{s.network ? `${Math.round(s.network)}ms` : '—'}</span>
              </div>
            </div>
          )
        })}
      </div>

      {/* Bar comparison chart */}
      {barData.length > 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-gray-200 mb-4">Resource Utilization Comparison</h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={barData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
              <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#6b7280' }} />
              <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: '#6b7280' }} />
              <Tooltip contentStyle={{ backgroundColor: '#111827', border: '1px solid #374151', borderRadius: '8px' }} />
              <Bar dataKey="CPU" fill="#06b6d4" radius={[4,4,0,0]} />
              <Bar dataKey="Memory" fill="#8b5cf6" radius={[4,4,0,0]} />
              <Bar dataKey="Disk" fill="#f97316" radius={[4,4,0,0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}
