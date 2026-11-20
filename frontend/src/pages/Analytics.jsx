/**
 * frontend/src/pages/Analytics.jsx
 */
import React, { useState, useEffect } from 'react'
import { BarChart3, TrendingUp } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, PieChart, Pie, Cell, Legend } from 'recharts'
import api from '../services/api'

const PIE_COLORS = ['#ef4444', '#eab308', '#3b82f6', '#22c55e']

export default function Analytics() {
  const [healthSummary, setHealthSummary] = useState({})
  const [trends, setTrends] = useState([])
  const [sourceSummary, setSourceSummary] = useState([])

  useEffect(() => {
    const load = async () => {
      try {
        const [h, t, s] = await Promise.allSettled([
          api.get('/reports/health-summary?hours=24'),
          api.get('/reports/incident-trends?days=7'),
          api.get('/reports/source-summary'),
        ])
        if (h.status === 'fulfilled') setHealthSummary(h.value.data.distribution || {})
        if (t.status === 'fulfilled') setTrends(t.value.data.trends || [])
        if (s.status === 'fulfilled') setSourceSummary(s.value.data.sources || [])
      } catch (e) {}
    }
    load()
  }, [])

  const pieData = Object.entries(healthSummary).map(([name, value]) => ({ name, value }))

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-white">Analytics & Reports</h1>
        <p className="text-sm text-gray-400 mt-0.5">Operational trends and historical summaries</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Health distribution */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-gray-200 mb-4">Health State Distribution (24h)</h3>
          {pieData.length === 0 ? (
            <div className="h-40 flex items-center justify-center text-gray-500 text-sm">No data</div>
          ) : (
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80}>
                  {pieData.map((entry, i) => <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}
                </Pie>
                <Tooltip contentStyle={{ backgroundColor: '#111827', border: '1px solid #374151' }} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Incident trends */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-gray-200 mb-4">Incident Frequency (7 days)</h3>
          {trends.length === 0 ? (
            <div className="h-40 flex items-center justify-center text-gray-500 text-sm">No incidents in the last 7 days</div>
          ) : (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={trends}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#6b7280' }} />
                <YAxis tick={{ fontSize: 10, fill: '#6b7280' }} />
                <Tooltip contentStyle={{ backgroundColor: '#111827', border: '1px solid #374151' }} />
                <Bar dataKey="critical" fill="#ef4444" radius={[4,4,0,0]} name="Critical" />
                <Bar dataKey="warning" fill="#eab308" radius={[4,4,0,0]} name="Warning" />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* Source alert summary */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <h3 className="text-sm font-semibold text-gray-200 mb-4">Alerts by Server</h3>
        {sourceSummary.length === 0 ? (
          <div className="text-center py-8 text-gray-500 text-sm">No alert data</div>
        ) : (
          <div className="space-y-2">
            {sourceSummary.map(s => (
              <div key={s.source_id} className="flex items-center gap-4 p-3 rounded-lg bg-gray-800/50">
                <span className="text-sm text-gray-200 w-32 truncate">{s.source_id}</span>
                <div className="flex-1 h-2 bg-gray-700 rounded-full overflow-hidden">
                  <div className="h-full bg-cyan-500 rounded-full" style={{ width: `${Math.min((s.total / 20) * 100, 100)}%` }} />
                </div>
                <span className="text-xs text-gray-400 w-20 text-right">
                  {s.critical > 0 && <span className="text-red-400">{s.critical}C </span>}
                  {s.warning > 0 && <span className="text-yellow-400">{s.warning}W </span>}
                  <span>{s.total} total</span>
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
