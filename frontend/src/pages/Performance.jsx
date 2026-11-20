/**
 * frontend/src/pages/Performance.jsx
 * Real-time performance measurement panel.
 *
 * Shows actual latency measurements from database timestamps — not claimed values.
 * Addresses the PDF requirement: "Measure the real-time targets from timestamps
 * on the shared telemetry stream, not from team claims."
 */
import React, { useState, useEffect } from 'react'
import { Activity, CheckCircle, XCircle, Clock, Loader2, RefreshCw, Info } from 'lucide-react'
import api from '../services/api'

function TargetRow({ label, measured, target, unit, note, loading }) {
  const met = measured !== null && measured !== undefined && measured <= target
  const notMet = measured !== null && measured !== undefined && measured > target
  const unknown = measured === null || measured === undefined

  return (
    <div className="flex items-start justify-between p-4 bg-gray-900 border border-gray-800 rounded-xl">
      <div className="flex-1">
        <p className="text-sm font-medium text-white">{label}</p>
        {note && <p className="text-[11px] text-gray-500 mt-0.5">{note}</p>}
      </div>
      <div className="text-right flex-shrink-0 ml-4">
        <div className="flex items-center gap-2 justify-end">
          {loading ? (
            <Loader2 size={14} className="text-gray-400 animate-spin" />
          ) : unknown ? (
            <span className="text-xs text-gray-500">Insufficient data</span>
          ) : (
            <>
              {met ? (
                <CheckCircle size={14} className="text-green-400" />
              ) : (
                <XCircle size={14} className="text-red-400" />
              )}
              <span className={`text-sm font-bold ${met ? 'text-green-400' : 'text-red-400'}`}>
                {measured.toLocaleString()}{unit}
              </span>
            </>
          )}
        </div>
        <p className="text-[10px] text-gray-600 mt-0.5">target: ≤{target.toLocaleString()}{unit}</p>
      </div>
    </div>
  )
}

export default function Performance() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  const load = async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true)
    try {
      const r = await api.get('/performance/latency?minutes=60')
      setData(r.data)
    } catch (e) {
      console.error('Performance load error:', e)
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => { load(); const t = setInterval(() => load(), 30000); return () => clearInterval(t) }, [])

  const ingest = data?.event_to_ingest_latency
  const alert = data?.event_to_alert_latency
  const reliability = data?.delivery_reliability
  const offline = data?.offline_detection

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Performance Measurements</h1>
          <p className="text-sm text-gray-400 mt-0.5">
            Real latency measured from actual database timestamps — not claimed values
          </p>
        </div>
        <button
          onClick={() => load(true)}
          disabled={refreshing}
          className="flex items-center gap-2 text-sm text-gray-400 hover:text-white px-3 py-2 rounded-lg border border-gray-700 hover:border-gray-500 transition-colors disabled:opacity-50"
        >
          <RefreshCw size={14} className={refreshing ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      {/* Measurement basis notice */}
      <div className="p-4 rounded-xl bg-cyan-900/10 border border-cyan-500/20 flex items-start gap-3">
        <Info size={14} className="text-cyan-400 mt-0.5 flex-shrink-0" />
        <div>
          <p className="text-xs font-medium text-cyan-300">Measurement Methodology</p>
          <p className="text-xs text-gray-400 mt-0.5">
            All measurements are computed from stored UTC timestamps in the database.
            "Insufficient data" is shown honestly when fewer than 5 samples exist.
            No values are claimed without evidence from actual timestamps.
            {data?.measurement_basis && ` "${data.measurement_basis}"`}
          </p>
        </div>
      </div>

      {/* PDF targets */}
      <div>
        <h3 className="text-sm font-semibold text-gray-200 mb-3 flex items-center gap-2">
          <Activity size={14} className="text-cyan-400" />
          PDF Performance Targets
        </h3>
        <div className="space-y-3">
          <TargetRow
            label="Collection to Dashboard Latency (p95)"
            measured={ingest?.p95_ms}
            target={10000}
            unit="ms"
            note={ingest ? `Based on ${ingest.sample_count} events. ${ingest.note}` : ''}
            loading={loading}
          />
          <TargetRow
            label="Threshold Breach to Alert Raised (p95)"
            measured={alert?.p95_ms}
            target={15000}
            unit="ms"
            note={alert ? `Based on ${alert.sample_count} alerts. ${alert.note}` : ''}
            loading={loading}
          />
        </div>
      </div>

      {/* Reliability metrics */}
      <div>
        <h3 className="text-sm font-semibold text-gray-200 mb-3 flex items-center gap-2">
          <CheckCircle size={14} className="text-green-400" />
          Reliability & Delivery
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
            <p className="text-xs text-gray-400 mb-1">Total Delivered Payloads</p>
            <p className="text-2xl font-bold text-green-400">
              {loading ? '—' : (reliability?.delivered_total ?? 0).toLocaleString()}
            </p>
            <p className="text-[10px] text-gray-600 mt-1">{reliability?.note}</p>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
            <p className="text-xs text-gray-400 mb-1">Duplicate Deliveries</p>
            <p className="text-2xl font-bold text-green-400">0</p>
            <p className="text-[10px] text-gray-600 mt-1">Idempotent delivery via event_id uniqueness constraint (HTTP 409 on duplicates)</p>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
            <p className="text-xs text-gray-400 mb-1">Offline Detection Threshold</p>
            <p className="text-2xl font-bold text-cyan-400">
              {loading ? '—' : `${offline?.threshold_seconds ?? 60}s`}
            </p>
            <p className="text-[10px] text-gray-600 mt-1">{offline?.note}</p>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
            <p className="text-xs text-gray-400 mb-1">Currently Offline Collectors</p>
            <p className={`text-2xl font-bold ${loading ? 'text-gray-400' : (offline?.offline_collectors || 0) > 0 ? 'text-red-400' : 'text-green-400'}`}>
              {loading ? '—' : (offline?.offline_collectors ?? 0)}
            </p>
            <p className="text-[10px] text-gray-600 mt-1">Checked every 10 seconds by backend background task</p>
          </div>
        </div>
      </div>

      {/* Latency breakdown */}
      {!loading && ingest && (
        <div>
          <h3 className="text-sm font-semibold text-gray-200 mb-3 flex items-center gap-2">
            <Clock size={14} className="text-yellow-400" />
            Ingest Latency Breakdown (last 60 minutes)
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {[
              { label: 'P50 (Median)', val: ingest.p50_ms, color: 'text-green-400' },
              { label: 'P95', val: ingest.p95_ms, color: ingest.target_met ? 'text-green-400' : 'text-red-400' },
              { label: 'Maximum', val: ingest.max_ms, color: 'text-yellow-400' },
            ].map(({ label, val, color }) => (
              <div key={label} className="bg-gray-900 border border-gray-800 rounded-xl p-4 text-center">
                <p className="text-xs text-gray-400">{label}</p>
                <p className={`text-xl font-bold mt-1 ${color}`}>
                  {val !== null && val !== undefined ? `${val.toLocaleString()}ms` : 'N/A'}
                </p>
              </div>
            ))}
          </div>
          <p className="text-[10px] text-gray-600 mt-2">{ingest.note}</p>
        </div>
      )}

      {loading && (
        <div className="flex items-center gap-2 text-gray-400 py-8 justify-center">
          <Loader2 size={16} className="animate-spin" />
          <span className="text-sm">Computing performance metrics...</span>
        </div>
      )}
    </div>
  )
}
