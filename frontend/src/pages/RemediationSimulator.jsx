/**
 * frontend/src/pages/RemediationSimulator.jsx
 * Safe Remediation Simulator — propose, approve, execute (simulated), and rollback.
 *
 * IMPORTANT: ALL ACTIONS ARE SIMULATIONS ONLY.
 * No real infrastructure changes occur. This page demonstrates the approval
 * workflow, audit trail, and rollback capability required by the PDF.
 */
import React, { useState, useEffect } from 'react'
import {
  Shield, Play, CheckCircle, XCircle, RotateCcw, Plus,
  ChevronDown, ChevronUp, AlertTriangle, Info, Loader2, Clock
} from 'lucide-react'
import api from '../services/api'
import { formatTimestamp } from '../utils/health'

const STATUS_COLORS = {
  pending:  { cls: 'bg-yellow-900/50 text-yellow-400', label: 'Pending Approval' },
  approved: { cls: 'bg-green-900/50 text-green-400', label: 'Approved' },
  rejected: { cls: 'bg-red-900/50 text-red-400', label: 'Rejected' },
  executed: { cls: 'bg-blue-900/50 text-blue-400', label: 'Executed (Sim)' },
  rolled_back: { cls: 'bg-purple-900/50 text-purple-400', label: 'Rolled Back' },
}

export default function RemediationSimulator() {
  const [remediations, setRemediations] = useState([])
  const [incidents, setIncidents] = useState([])
  const [safeActions, setSafeActions] = useState([])
  const [loading, setLoading] = useState(true)
  const [showPropose, setShowPropose] = useState(false)
  const [proposing, setProposing] = useState(false)
  const [form, setForm] = useState({ incident_id: '', proposed_action: '' })
  const [actionMsg, setActionMsg] = useState(null)
  const [expanded, setExpanded] = useState({})

  const load = async () => {
    try {
      const [r, i, a] = await Promise.all([
        api.get('/remediation/'),
        api.get('/incidents/?status=open'),
        api.get('/remediation/actions'),
      ])
      setRemediations(r.data)
      setIncidents(i.data?.incidents || i.data || [])
      setSafeActions(a.data?.actions || [])
    } catch (e) {
      console.error('Load error:', e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load(); const t = setInterval(load, 10000); return () => clearInterval(t) }, [])

  const handlePropose = async () => {
    if (!form.incident_id || !form.proposed_action) return
    setProposing(true)
    try {
      await api.post('/remediation/propose', form)
      setActionMsg({ type: 'success', text: 'Remediation proposed successfully. Waiting for approval.' })
      setForm({ incident_id: '', proposed_action: '' })
      setShowPropose(false)
      load()
    } catch (e) {
      setActionMsg({ type: 'error', text: e.response?.data?.detail || 'Failed to propose.' })
    } finally { setProposing(false) }
  }

  const handleApprove = async (id) => {
    try {
      await api.post(`/remediation/${id}/approve`)
      setActionMsg({ type: 'success', text: 'Action approved. Ready to execute.' })
      load()
    } catch (e) {
      setActionMsg({ type: 'error', text: e.response?.data?.detail || 'Approval failed.' })
    }
  }

  const handleExecute = async (id) => {
    try {
      const r = await api.post(`/remediation/${id}/execute`)
      setActionMsg({ type: 'success', text: `Simulation complete: ${r.data.simulation_note}` })
      load()
    } catch (e) {
      setActionMsg({ type: 'error', text: e.response?.data?.detail || 'Execution failed.' })
    }
  }

  const handleRollback = async (id) => {
    try {
      await api.post(`/remediation/${id}/rollback`)
      setActionMsg({ type: 'success', text: 'Rollback simulation complete. Audit record updated.' })
      load()
    } catch (e) {
      setActionMsg({ type: 'error', text: e.response?.data?.detail || 'Rollback failed.' })
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Safe Remediation Simulator</h1>
          <p className="text-sm text-gray-400 mt-0.5">
            Propose, approve, and simulate remediation actions with full audit trail
          </p>
        </div>
        <button
          onClick={() => setShowPropose(!showPropose)}
          className="flex items-center gap-2 bg-cyan-600 hover:bg-cyan-500 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors"
        >
          <Plus size={14} /> Propose Action
        </button>
      </div>

      {/* Safety disclaimer */}
      <div className="p-4 rounded-xl bg-orange-900/10 border border-orange-500/20 flex items-start gap-3">
        <AlertTriangle size={16} className="text-orange-400 mt-0.5 flex-shrink-0" />
        <div>
          <p className="text-sm font-semibold text-orange-300">Simulation Mode — No Real Changes</p>
          <p className="text-xs text-gray-400 mt-1">
            All actions on this page are executed in an isolated simulation environment.
            No real infrastructure is modified. The approval workflow, audit trail, and rollback
            capability are real and demonstrable — only the execution is simulated.
          </p>
        </div>
      </div>

      {/* Action feedback message */}
      {actionMsg && (
        <div className={`p-3 rounded-lg text-sm ${
          actionMsg.type === 'success'
            ? 'bg-green-900/20 border border-green-700/50 text-green-300'
            : 'bg-red-900/20 border border-red-700/50 text-red-300'
        }`}>
          {actionMsg.text}
          <button onClick={() => setActionMsg(null)} className="ml-3 text-xs opacity-60 hover:opacity-100">✕</button>
        </div>
      )}

      {/* Propose form */}
      {showPropose && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-4">
          <h3 className="text-sm font-semibold text-white">Propose New Remediation Action</h3>

          <div>
            <label className="text-xs text-gray-400 block mb-1">Select Incident</label>
            <select
              value={form.incident_id}
              onChange={e => setForm({ ...form, incident_id: e.target.value })}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-cyan-500"
            >
              <option value="">-- Select an open incident --</option>
              {incidents.map(i => (
                <option key={i.id} value={i.id}>{i.title} [{i.severity}]</option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-xs text-gray-400 block mb-1">Safe Action (from catalog)</label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {safeActions.map(action => (
                <button
                  key={action.key}
                  onClick={() => setForm({ ...form, proposed_action: action.label })}
                  className={`text-left text-xs p-2.5 rounded-lg border transition-colors ${
                    form.proposed_action === action.label
                      ? 'border-cyan-500 bg-cyan-900/20 text-cyan-200'
                      : 'border-gray-700 bg-gray-800/50 text-gray-300 hover:border-gray-500'
                  }`}
                >
                  <div className="font-medium">{action.label}</div>
                  {action.reversible !== undefined && (
                    <span className={`text-[10px] mt-0.5 ${action.reversible ? 'text-green-500' : 'text-red-500'}`}>
                      {action.reversible ? '↩ Reversible' : '⚠ Not reversible'}
                    </span>
                  )}
                </button>
              ))}
            </div>
          </div>

          <div className="flex gap-3">
            <button
              onClick={handlePropose}
              disabled={proposing || !form.incident_id || !form.proposed_action}
              className="bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white text-sm px-4 py-2 rounded-lg transition-colors flex items-center gap-2"
            >
              {proposing && <Loader2 size={12} className="animate-spin" />}
              Submit Proposal
            </button>
            <button
              onClick={() => setShowPropose(false)}
              className="text-sm text-gray-400 hover:text-white px-4 py-2 rounded-lg border border-gray-700 hover:border-gray-500 transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Remediations list */}
      {loading ? (
        <div className="flex items-center gap-2 text-gray-400 py-8">
          <Loader2 size={16} className="animate-spin" />
          <span className="text-sm">Loading remediations...</span>
        </div>
      ) : remediations.length === 0 ? (
        <div className="text-center py-16 text-gray-500 bg-gray-900 border border-gray-800 rounded-xl">
          <Shield size={32} className="mx-auto mb-3 opacity-30" />
          <p className="text-sm">No remediation actions yet.</p>
          <p className="text-xs mt-1 text-gray-600">Click "Propose Action" to create one.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {remediations.map(item => {
            const statusCfg = STATUS_COLORS[item.status] || STATUS_COLORS.pending
            const isExpanded = expanded[item.id]
            return (
              <div key={item.id} className="bg-gray-900 border border-gray-800 rounded-xl p-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${statusCfg.cls}`}>
                        {statusCfg.label}
                      </span>
                      <p className="text-sm font-medium text-white truncate">{item.proposed_action}</p>
                    </div>
                    <p className="text-xs text-gray-500 mt-1">
                      Incident: <span className="text-gray-300">{item.incident_id.slice(0, 8)}…</span>
                      {' '}· Proposed: <span className="text-gray-300">{formatTimestamp(item.created_at)}</span>
                    </p>
                  </div>

                  {/* Action buttons */}
                  <div className="flex items-center gap-2 flex-shrink-0">
                    {item.status === 'pending' && (
                      <button
                        onClick={() => handleApprove(item.id)}
                        className="flex items-center gap-1 text-xs bg-green-900/40 hover:bg-green-800/60 text-green-400 px-2 py-1 rounded-lg border border-green-700/50 transition-colors"
                      >
                        <CheckCircle size={12} /> Approve
                      </button>
                    )}
                    {item.status === 'approved' && (
                      <button
                        onClick={() => handleExecute(item.id)}
                        className="flex items-center gap-1 text-xs bg-blue-900/40 hover:bg-blue-800/60 text-blue-400 px-2 py-1 rounded-lg border border-blue-700/50 transition-colors"
                      >
                        <Play size={12} /> Simulate
                      </button>
                    )}
                    {item.status === 'executed' && (
                      <button
                        onClick={() => handleRollback(item.id)}
                        className="flex items-center gap-1 text-xs bg-purple-900/40 hover:bg-purple-800/60 text-purple-400 px-2 py-1 rounded-lg border border-purple-700/50 transition-colors"
                      >
                        <RotateCcw size={12} /> Rollback
                      </button>
                    )}
                    <button
                      onClick={() => setExpanded(p => ({ ...p, [item.id]: !isExpanded }))}
                      className="text-gray-500 hover:text-white"
                    >
                      {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                    </button>
                  </div>
                </div>

                {/* Expanded audit details */}
                {isExpanded && (
                  <div className="mt-4 pt-4 border-t border-gray-800 text-xs text-gray-400 space-y-1">
                    <p><span className="text-gray-500">Approval ID:</span> <span className="font-mono text-gray-300">{item.id}</span></p>
                    <p><span className="text-gray-500">Proposed by:</span> <span className="text-gray-300">{item.proposed_by.slice(0, 12)}…</span></p>
                    {item.approved_by && (
                      <p><span className="text-gray-500">Approved by:</span> <span className="text-gray-300">{item.approved_by.slice(0, 12)}…</span></p>
                    )}
                    {item.approved_at && (
                      <p><span className="text-gray-500">Approved at:</span> <span className="text-gray-300">{formatTimestamp(item.approved_at)}</span></p>
                    )}
                    <div className="mt-2 p-2 rounded bg-gray-800/50 border border-gray-700/40">
                      <p className="text-[10px] text-gray-500 italic">
                        All actions are simulated. Audit records are immutable once written.
                        Rollback simulation marks the audit record as rolled_back.
                      </p>
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
