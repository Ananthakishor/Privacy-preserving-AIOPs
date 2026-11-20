/**
 * frontend/src/pages/ActivityTimeline.jsx
 */
import React, { useState, useEffect } from 'react'
import { Clock, AlertTriangle, GitMerge, Radio, Info } from 'lucide-react'
import api from '../services/api'
import { formatTimestamp, getSeverityConfig } from '../utils/health'

export default function ActivityTimeline() {
  const [alerts, setAlerts] = useState([])
  const [incidents, setIncidents] = useState([])

  useEffect(() => {
    const load = async () => {
      try {
        const [a, i] = await Promise.all([
          api.get('/alerts/?limit=30'),
          api.get('/incidents/?limit=20'),
        ])
        setAlerts(a.data)
        setIncidents(i.data)
      } catch (e) {}
    }
    load()
  }, [])

  // Merge and sort by timestamp
  const events = [
    ...alerts.map(a => ({ type: 'alert', data: a, ts: a.created_at })),
    ...incidents.map(i => ({ type: 'incident', data: i, ts: i.created_at })),
  ].sort((a, b) => b.ts.localeCompare(a.ts))

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-white">Activity Timeline</h1>
        <p className="text-sm text-gray-400 mt-0.5">Chronological log of all system events</p>
      </div>

      <div className="relative">
        {/* Timeline line */}
        <div className="absolute left-5 top-0 bottom-0 w-px bg-gray-800" />

        <div className="space-y-3">
          {events.length === 0 ? (
            <div className="text-center py-16 text-gray-500">No events yet</div>
          ) : events.map((event, i) => (
            <div key={i} className="relative flex items-start gap-4 pl-12">
              {/* Dot */}
              <div className={`absolute left-3.5 w-3 h-3 rounded-full border-2 border-gray-900 ${
                event.type === 'incident' ? 'bg-orange-400' :
                event.data.severity === 'critical' ? 'bg-red-400' :
                event.data.severity === 'warning' ? 'bg-yellow-400' : 'bg-blue-400'
              }`} />

              <div className="flex-1 bg-gray-900 border border-gray-800 rounded-xl p-4 hover:border-gray-700 transition-colors">
                <div className="flex items-center gap-2 mb-1">
                  {event.type === 'incident' ? <GitMerge size={12} className="text-orange-400" /> : <AlertTriangle size={12} className="text-yellow-400" />}
                  <span className="text-xs font-semibold text-gray-200">
                    {event.type === 'incident' ? event.data.title : `${event.data.severity?.toUpperCase()} — ${event.data.source_id}`}
                  </span>
                  <span className="text-[10px] text-gray-500 ml-auto">{formatTimestamp(event.ts)}</span>
                </div>
                <p className="text-xs text-gray-400">
                  {event.type === 'incident' ? event.data.description : event.data.message?.substring(0, 120)}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
