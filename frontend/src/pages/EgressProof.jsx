/**
 * frontend/src/pages/EgressProof.jsx
 * Privacy Center — shows exact approved payloads sent to SaaS.
 * Proves that secrets never leave the collector environment.
 */
import React, { useState, useEffect } from 'react'
import { Lock, Eye, EyeOff, Shield, ExternalLink, ChevronDown, ChevronUp } from 'lucide-react'
import api from '../services/api'
import { formatTimestamp } from '../utils/health'

function PayloadRow({ record }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="border border-gray-800 rounded-xl overflow-hidden mb-3">
      <div className="flex items-center gap-4 p-4 cursor-pointer hover:bg-gray-800/30 bg-gray-900"
        onClick={() => setExpanded(!expanded)}>
        <Shield size={14} className="text-green-400 flex-shrink-0" />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono text-cyan-400">{record.payload_id?.substring(0, 16)}...</span>
            <span className={`text-xs px-1.5 py-0.5 rounded ${
              record.status === 'delivered' ? 'bg-green-900/30 text-green-400' : 'bg-red-900/30 text-red-400'
            }`}>{record.status}</span>
          </div>
          <p className="text-[10px] text-gray-500 mt-0.5">
            Collector: {record.collector_id?.substring(0, 8)}... · Fields: {record.fields_included?.length || 0} · {formatTimestamp(record.utc_timestamp)}
          </p>
        </div>
        {expanded ? <ChevronUp size={14} className="text-gray-500" /> : <ChevronDown size={14} className="text-gray-500" />}
      </div>

      {expanded && (
        <div className="border-t border-gray-800 p-4 bg-gray-950">
          <div className="mb-3">
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">Fields Transmitted</p>
            <div className="flex flex-wrap gap-1.5">
              {(record.fields_included || []).map(f => (
                <span key={f} className="px-2 py-0.5 rounded bg-cyan-900/20 text-cyan-400 text-[10px] font-mono border border-cyan-500/20">
                  {f}
                </span>
              ))}
            </div>
          </div>
          <div>
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">Approved Payload (what SaaS received)</p>
            <pre className="text-[10px] text-green-300 bg-gray-900 border border-gray-700 rounded-lg p-3 overflow-x-auto whitespace-pre-wrap">
              {JSON.stringify(record.payload_preview || {}, null, 2)}
            </pre>
          </div>
        </div>
      )}
    </div>
  )
}

export default function EgressProof() {
  const [records, setRecords] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const load = async () => {
      try {
        const { data } = await api.get('/privacy/transfer-audit?limit=50')
        setRecords(data)
      } catch (e) {}
      finally { setLoading(false) }
    }
    load(); const t = setInterval(load, 15000); return () => clearInterval(t)
  }, [])

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-white">Egress Proof / Privacy Center</h1>
        <p className="text-sm text-gray-400 mt-0.5">Proof of what exactly left the collector environment</p>
      </div>

      {/* Privacy architecture explanation */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[
          {
            title: 'Raw Data (Collector-Local)',
            desc: 'Raw logs, passwords, tokens, hostnames with PII — stored ONLY on the collector host. Never transmitted.',
            color: 'border-red-500/30 bg-red-900/5',
            icon: '🔒',
            items: ['CPU usage raw data', 'password=SuperSecret123', 'Raw auth.log entries', '_raw_usernames', '_raw_source_ips']
          },
          {
            title: 'Privacy Pipeline',
            desc: 'Normalize → Redact → Allow-list. Every event passes through this before transmission.',
            color: 'border-yellow-500/30 bg-yellow-900/5',
            icon: '⚙️',
            items: ['Normalize timestamps to UTC', 'Redact secret patterns', 'Replace hostname with src-id', 'Apply explicit allow-list', 'Log to egress proof file']
          },
          {
            title: 'Approved Payload (SaaS)',
            desc: 'Only these 12 fields arrive at the SaaS backend — verified in the table below.',
            color: 'border-green-500/30 bg-green-900/5',
            icon: '✅',
            items: ['tenant_id', 'source_id (pseudonymous)', 'event_id (UUID)', 'utc_timestamp', 'metric_category + value', 'severity + health_status']
          }
        ].map(({ title, desc, color, icon, items }) => (
          <div key={title} className={`border rounded-xl p-4 ${color}`}>
            <div className="flex items-center gap-2 mb-2">
              <span>{icon}</span>
              <span className="text-sm font-semibold text-white">{title}</span>
            </div>
            <p className="text-xs text-gray-400 mb-3">{desc}</p>
            <ul className="space-y-1">
              {items.map(item => (
                <li key={item} className="text-[10px] text-gray-500 flex items-center gap-1">
                  <span className="w-1 h-1 rounded-full bg-gray-600" />{item}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      <div className="p-4 rounded-xl bg-cyan-900/10 border border-cyan-500/20">
        <p className="text-xs text-gray-400">
          <strong className="text-cyan-400">Note:</strong> The raw record (including dummy secrets) is viewable
          at <span className="font-mono text-cyan-300">http://localhost:8001/raw</span> on the collector host only.
          The table below shows what the SaaS backend actually received.
        </p>
      </div>

      <div>
        <h3 className="text-sm font-semibold text-gray-200 mb-3">Transfer Audit Log ({records.length} records)</h3>
        {loading ? (
          <div className="text-center py-8 text-gray-500">Loading...</div>
        ) : records.length === 0 ? (
          <div className="text-center py-16 text-gray-500 bg-gray-900 border border-gray-800 rounded-xl">
            No transfer audit records yet — start the collector or simulator
          </div>
        ) : (
          records.map(r => <PayloadRow key={r.id || r.payload_id} record={r} />)
        )}
      </div>
    </div>
  )
}
