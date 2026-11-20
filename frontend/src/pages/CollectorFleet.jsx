/**
 * frontend/src/pages/CollectorFleet.jsx
 */
import React, { useState, useEffect } from 'react'
import { Radio, Wifi, WifiOff, Clock, RefreshCw, Server } from 'lucide-react'
import api from '../services/api'
import { formatTimestamp, timeAgo } from '../utils/health'

export default function CollectorFleet() {
  const [collectors, setCollectors] = useState([])

  const load = async () => {
    try { const { data } = await api.get('/collectors/'); setCollectors(data) } catch (e) {}
  }

  useEffect(() => { load(); const t = setInterval(load, 10000); return () => clearInterval(t) }, [])

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Collector Fleet</h1>
          <p className="text-sm text-gray-400 mt-0.5">Status and health of all local collectors</p>
        </div>
        <button onClick={load} className="p-2 rounded-lg text-gray-400 hover:text-white hover:bg-gray-800">
          <RefreshCw size={16} />
        </button>
      </div>

      <div className="p-4 rounded-xl bg-blue-900/10 border border-blue-500/20 text-xs text-gray-400">
        <strong className="text-blue-400">Offline detection:</strong> A collector is marked offline if no heartbeat
        is received within 60 seconds. Health state is downgraded to Poor automatically.
      </div>

      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-800">
              {['Collector', 'Tenant', 'Status', 'Last Heartbeat', 'Version', 'CPU', 'Memory', 'Buffered'].map(h => (
                <th key={h} className="text-left text-xs text-gray-500 font-medium uppercase tracking-wide px-4 py-3">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-800">
            {collectors.length === 0 ? (
              <tr><td colSpan={8} className="text-center py-12 text-gray-500 text-sm">No collectors registered</td></tr>
            ) : collectors.map(c => (
              <tr key={c.id} className="hover:bg-gray-800/30 transition-colors">
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <Radio size={14} className={c.status === 'online' ? 'text-green-400' : 'text-red-400'} />
                    <span className="text-sm font-medium text-white">{c.name}</span>
                  </div>
                  <span className="text-[10px] text-gray-500">{c.id.substring(0, 8)}...</span>
                </td>
                <td className="px-4 py-3 text-xs text-gray-400">{c.tenant_id}</td>
                <td className="px-4 py-3">
                  <span className={`flex items-center gap-1.5 w-fit px-2 py-0.5 rounded-full text-xs ${
                    c.status === 'online' ? 'bg-green-900/30 text-green-400' : 'bg-red-900/30 text-red-400'
                  }`}>
                    {c.status === 'online' ? <Wifi size={10} /> : <WifiOff size={10} />}
                    {c.status}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <div className="text-xs text-gray-300">{timeAgo(c.last_heartbeat_at)}</div>
                  <div className="text-[10px] text-gray-600">{c.last_heartbeat_at ? new Date(c.last_heartbeat_at).toISOString().substring(0, 19) + 'Z' : 'Never'}</div>
                </td>
                <td className="px-4 py-3 text-xs text-gray-400">{c.version}</td>
                <td className="px-4 py-3 text-xs text-gray-300">{c.cpu_pct?.toFixed(1) ?? '—'}%</td>
                <td className="px-4 py-3 text-xs text-gray-300">{c.mem_pct?.toFixed(1) ?? '—'}%</td>
                <td className="px-4 py-3">
                  <span className={`text-xs font-medium ${c.buffered_count > 0 ? 'text-yellow-400' : 'text-gray-500'}`}>
                    {c.buffered_count ?? 0}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
