/**
 * frontend/src/pages/AIInsights.jsx
 * Explainable AIOps recommendations and anomaly analysis.
 */
import React, { useState, useEffect } from 'react'
import { Brain, AlertTriangle, ChevronDown, ChevronUp, TrendingUp, Info } from 'lucide-react'
import api from '../services/api'
import { formatTimestamp, getSeverityConfig } from '../utils/health'

function RecommendationCard({ rec }) {
  const [expanded, setExpanded] = useState(false)
  const signals = Array.isArray(rec.contributing_signals) ? rec.contributing_signals : []
  const steps = Array.isArray(rec.suggested_steps) ? rec.suggested_steps : []

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-2">
          <Brain size={16} className="text-cyan-400 flex-shrink-0" />
          <span className="text-sm font-semibold text-white">AI Recommendation</span>
        </div>
        <button onClick={() => setExpanded(!expanded)} className="text-gray-500 hover:text-white">
          {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </button>
      </div>

      <p className="text-sm text-gray-300 mt-3 leading-relaxed">{rec.explanation}</p>

      <div className="mt-3 p-2 rounded bg-gray-800/50 border border-gray-700/50">
        <p className="text-[10px] text-gray-500 font-medium">Confidence basis: {rec.confidence_basis}</p>
      </div>

      {expanded && (
        <>
          {signals.length > 0 && (
            <div className="mt-4">
              <p className="text-xs font-semibold text-gray-400 mb-2 uppercase tracking-wide">Contributing Signals</p>
              <div className="space-y-2">
                {signals.map((s, i) => (
                  <div key={i} className="flex items-center gap-3 p-2 rounded bg-gray-800/30">
                    <TrendingUp size={12} className="text-yellow-400 flex-shrink-0" />
                    <div className="flex-1 text-xs">
                      <span className="text-gray-200">{s.signal}</span>
                      <span className="text-gray-500 ml-2">
                        observed: <span className="text-red-400">{s.observed_value?.toFixed(1)}</span>
                        {' '}baseline: <span className="text-green-400">{s.baseline?.toFixed(1)}</span>
                        {' '}deviation: <span className="text-yellow-400">{s.deviation?.toFixed(1)}σ</span>
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {steps.length > 0 && (
            <div className="mt-4">
              <p className="text-xs font-semibold text-gray-400 mb-2 uppercase tracking-wide">Recommended Investigation</p>
              <ol className="space-y-2">
                {steps.map((step, i) => (
                  <li key={i} className="flex items-start gap-2 text-xs text-gray-300">
                    <span className="w-5 h-5 rounded-full bg-cyan-500/20 text-cyan-400 flex items-center justify-center flex-shrink-0 font-bold text-[10px]">
                      {i + 1}
                    </span>
                    {step}
                  </li>
                ))}
              </ol>
            </div>
          )}
        </>
      )}

      <p className="text-[10px] text-gray-600 mt-3">{formatTimestamp(rec.created_at)}</p>
    </div>
  )
}

export default function AIInsights() {
  const [anomalies, setAnomalies] = useState([])
  const [recommendations, setRecommendations] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const load = async () => {
      try {
        const [a, r] = await Promise.all([
          api.get('/aiops/anomalies?limit=20'),
          api.get('/aiops/recommendations?limit=10'),
        ])
        setAnomalies(a.data)
        setRecommendations(r.data)
      } catch (e) {}
      finally { setLoading(false) }
    }
    load(); const t = setInterval(load, 15000); return () => clearInterval(t)
  }, [])

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-white">AI Insights</h1>
        <p className="text-sm text-gray-400 mt-0.5">Explainable anomaly detection and recommendations</p>
      </div>

      <div className="p-4 rounded-xl bg-cyan-900/10 border border-cyan-500/20">
        <div className="flex items-center gap-2 text-cyan-400 text-sm font-medium mb-1">
          <Info size={14} />
          How anomaly detection works
        </div>
        <p className="text-xs text-gray-400">
          Z-score analysis: anomalies are flagged when a metric deviates more than 2.5 standard deviations
          from its rolling baseline (last 50 samples). A warm-up state is shown when fewer than 10 samples exist.
          No external LLM is used for core detections — all explanations are grounded in actual metric values.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Anomalies */}
        <div>
          <h3 className="text-sm font-semibold text-gray-200 mb-3 flex items-center gap-2">
            <AlertTriangle size={14} className="text-yellow-400" />
            Detected Anomalies ({anomalies.length})
          </h3>
          {anomalies.length === 0 ? (
            <div className="text-center py-12 text-gray-500 bg-gray-900 border border-gray-800 rounded-xl">
              No anomalies detected — system operating normally
            </div>
          ) : (
            <div className="space-y-3">
              {anomalies.map(a => (
                <div key={a.alert_id} className="bg-gray-900 border border-gray-800 rounded-xl p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <span className={`text-xs font-bold uppercase px-1.5 py-0.5 rounded ${
                      a.severity === 'critical' ? 'bg-red-900/50 text-red-400' :
                      a.severity === 'warning' ? 'bg-yellow-900/50 text-yellow-400' :
                      'bg-blue-900/50 text-blue-400'
                    }`}>{a.severity}</span>
                    <span className="text-xs text-gray-300 font-medium">{a.metric_category?.toUpperCase()} on {a.source_id}</span>
                  </div>
                  <p className="text-xs text-gray-400 leading-relaxed">{a.explanation}</p>
                  <div className="flex gap-4 mt-2 text-xs">
                    <span className="text-gray-500">Observed: <span className="text-red-400">{a.observed_value?.toFixed(1)}</span></span>
                    <span className="text-gray-500">Baseline: <span className="text-green-400">{a.expected_baseline?.toFixed(1)}</span></span>
                    <span className="text-gray-500">Deviation: <span className="text-yellow-400">{a.deviation_sigma?.toFixed(1)}σ</span></span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Recommendations */}
        <div>
          <h3 className="text-sm font-semibold text-gray-200 mb-3 flex items-center gap-2">
            <Brain size={14} className="text-cyan-400" />
            Recommendations ({recommendations.length})
          </h3>
          {recommendations.length === 0 ? (
            <div className="text-center py-12 text-gray-500 bg-gray-900 border border-gray-800 rounded-xl">
              No recommendations yet — trigger a scenario to generate insights
            </div>
          ) : (
            <div className="space-y-3">
              {recommendations.map(r => <RecommendationCard key={r.id} rec={r} />)}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
