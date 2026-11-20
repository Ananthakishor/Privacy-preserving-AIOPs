/**
 * frontend/src/pages/IncidentManagement.jsx
 */
import React, { useState, useEffect } from 'react'
import { GitMerge, CheckCircle, Clock, AlertTriangle, ChevronDown, ChevronUp } from 'lucide-react'
import api from '../services/api'
import { formatTimestamp, getHealthConfig } from '../utils/health'

function IncidentRow({ incident, onResolve }) {
  const [expanded, setExpanded] = useState(false)
  const [timeline, setTimeline] = useState([])

  const loadTimeline = async () => {
    if (expanded) { setExpanded(false); return }
    try {
      const { data } = await api.get(`/incidents/${incident.id}/timeline`)
      setTimeline(data)
    } catch (e) {}
    setExpanded(true)
  }

  const handleResolve = async () => {
    await api.post(`/incidents/${incident.id}/resolve`, { resolution_note: 'Resolved via dashboard' }).catch(() => {})
    onResolve()
  }

  const cfg = getHealthConfig(incident.severity === 'critical' ? 'poor' : incident.severity === 'warning' ? 'fair' : 'good')

  return (
    <div className="border border-gray-800 rounded-xl overflow-hidden">
      <div className={`flex items-center gap-4 p-4 cursor-pointer hover:bg-gray-800/30 ${expanded ? 'bg-gray-800/20' : 'bg-gray-900'}`}
        onClick={loadTimeline}>
        <div className={`w-2 h-2 rounded-full flex-shrink-0 ${cfg.dot}`} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-white truncate">{incident.title}</span>
            <span className={`text-xs px-2 py-0.5 rounded ${cfg.badge}`}>{incident.severity}</span>
            <span className={`text-xs px-2 py-0.5 rounded ${
              incident.status === 'open' ? 'bg-red-900/30 text-red-400' :
              incident.status === 'acknowledged' ? 'bg-yellow-900/30 text-yellow-400' :
              'bg-green-900/30 text-green-400'
            }`}>{incident.status}</span>
          </div>
          <p className="text-xs text-gray-500 mt-0.5">Source: {incident.source_id} · {formatTimestamp(incident.created_at)}</p>
        </div>
        <div className="flex items-center gap-2">
          {incident.status !== 'resolved' && (
            <button onClick={(e) => { e.stopPropagation(); handleResolve() }}
              className="px-3 py-1 rounded-lg bg-green-500/15 text-green-400 hover:bg-green-500/25 text-xs transition-colors">
              Resolve
            </button>
          )}
          {expanded ? <ChevronUp size={16} className="text-gray-400" /> : <ChevronDown size={16} className="text-gray-400" />}
        </div>
      </div>

      {expanded && (
        <div className="border-t border-gray-800 p-4 bg-gray-900/50">
          <p className="text-xs text-gray-400 mb-3">{incident.description}</p>
          <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">Timeline</h4>
          <div className="space-y-2">
            {timeline.map((event, i) => (
              <div key={i} className="flex items-start gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-cyan-400 mt-1.5 flex-shrink-0" />
                <div>
                  <p className="text-xs text-gray-300">{event.description}</p>
                  <p className="text-[10px] text-gray-600">{formatTimestamp(event.timestamp)}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default function IncidentManagement() {
  const [incidents, setIncidents] = useState([])
  const [statusFilter, setStatusFilter] = useState('all')

  const load = async () => {
    try {
      const params = statusFilter !== 'all' ? `?status=${statusFilter}` : ''
      const { data } = await api.get(`/incidents/${params}`)
      setIncidents(data)
    } catch (e) {}
  }

  useEffect(() => { load(); const t = setInterval(load, 15000); return () => clearInterval(t) }, [statusFilter])

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-white">Incident Management</h1>
        <p className="text-sm text-gray-400 mt-0.5">Correlated incident groups with investigation guidance</p>
      </div>

      <div className="flex gap-1 bg-gray-900 border border-gray-700 rounded-lg p-1 w-fit">
        {['all', 'open', 'acknowledged', 'resolved'].map(s => (
          <button key={s} onClick={() => setStatusFilter(s)}
            className={`px-3 py-1 rounded text-xs capitalize ${statusFilter === s ? 'bg-cyan-600 text-white' : 'text-gray-400 hover:text-white'}`}>
            {s}
          </button>
        ))}
      </div>

      <div className="space-y-3">
        {incidents.length === 0 ? (
          <div className="text-center py-16 text-gray-500 bg-gray-900 border border-gray-800 rounded-xl">
            <CheckCircle size={32} className="mx-auto mb-3 opacity-30 text-green-400" />
            No incidents found
          </div>
        ) : incidents.map(inc => (
          <IncidentRow key={inc.id} incident={inc} onResolve={load} />
        ))}
      </div>
    </div>
  )
}
