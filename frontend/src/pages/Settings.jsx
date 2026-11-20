/**
 * frontend/src/pages/Settings.jsx
 */
import React, { useState } from 'react'
import { Settings as SettingsIcon, Save, Info, Shield } from 'lucide-react'
import useAuthStore from '../store/authStore'

export default function Settings() {
  const { user } = useAuthStore()
  const [saved, setSaved] = useState(false)

  const handleSave = () => {
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h1 className="text-xl font-bold text-white">Settings</h1>
        <p className="text-sm text-gray-400 mt-0.5">Platform configuration and preferences</p>
      </div>

      {/* User info */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <h3 className="text-sm font-semibold text-gray-200 mb-4 flex items-center gap-2">
          <Shield size={14} className="text-cyan-400" />
          Account
        </h3>
        <div className="space-y-3">
          {[
            { label: 'Email', value: user?.email },
            { label: 'Role', value: user?.role },
            { label: 'Tenant', value: user?.tenant_id },
          ].map(({ label, value }) => (
            <div key={label} className="flex items-center gap-4">
              <span className="text-xs text-gray-500 w-20">{label}</span>
              <span className="text-sm text-gray-200">{value || '—'}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Health thresholds */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <h3 className="text-sm font-semibold text-gray-200 mb-4 flex items-center gap-2">
          <SettingsIcon size={14} className="text-cyan-400" />
          Health Thresholds
          <span className="text-[10px] text-gray-500 ml-auto">(configure backend .env for production)</span>
        </h3>
        <div className="space-y-3">
          {[
            { label: 'CPU — Fair threshold', value: '75%', desc: 'Above this → Fair health state' },
            { label: 'CPU — Poor threshold', value: '90%', desc: 'Above this → Poor health state' },
            { label: 'Memory — Fair', value: '80%', desc: 'Above this → Fair health state' },
            { label: 'Network latency — Fair', value: '200ms', desc: 'Above this → Fair health state' },
            { label: 'Offline detection', value: '60 seconds', desc: 'No heartbeat within this period → offline' },
            { label: 'Anomaly detection threshold', value: '2.5σ', desc: 'Z-score above this → anomaly flagged' },
          ].map(({ label, value, desc }) => (
            <div key={label} className="flex items-center justify-between p-3 rounded-lg bg-gray-800/40">
              <div>
                <p className="text-xs font-medium text-gray-300">{label}</p>
                <p className="text-[10px] text-gray-500 mt-0.5">{desc}</p>
              </div>
              <span className="text-sm font-bold text-cyan-400">{value}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Privacy settings */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <h3 className="text-sm font-semibold text-gray-200 mb-4 flex items-center gap-2">
          <Shield size={14} className="text-green-400" />
          Privacy & Data
        </h3>
        <div className="p-3 rounded-lg bg-green-900/10 border border-green-500/20">
          <p className="text-xs text-gray-400 leading-relaxed">
            <strong className="text-green-400">Local-first by design.</strong> Raw logs, passwords, tokens, and
            personally identifiable information never leave the collector environment. Only the 12 allow-listed
            metadata fields are transmitted. The egress proof log is stored locally and proves this.
          </p>
        </div>
      </div>
    </div>
  )
}
