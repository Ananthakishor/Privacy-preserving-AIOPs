/**
 * frontend/src/pages/AIInsights.jsx
 * Explainable AIOps recommendations, anomaly analysis, predictive warnings,
 * and the "Ask Sentinel AI" assistant (powered by IBM watsonx + rule-based fallback).
 */
import React, { useState, useEffect } from 'react'
import {
  Brain, AlertTriangle, ChevronDown, ChevronUp, TrendingUp, Info,
  MessageSquare, Send, Loader2, TrendingDown, Zap, Clock
} from 'lucide-react'
import api from '../services/api'
import { formatTimestamp, getSeverityConfig } from '../utils/health'

/** Colored badge for data_source provenance */
function DataSourceBadge({ source }) {
  const cfg = {
    live: { label: 'LIVE', cls: 'bg-green-900/60 text-green-400 border border-green-700/50' },
    seed: { label: 'SEED', cls: 'bg-blue-900/60 text-blue-400 border border-blue-700/50' },
    simulated: { label: 'SIM', cls: 'bg-yellow-900/60 text-yellow-400 border border-yellow-700/50' },
  }[source] || { label: 'LIVE', cls: 'bg-green-900/60 text-green-400 border border-green-700/50' }
  return (
    <span className={`text-[9px] font-bold px-1 py-0.5 rounded ${cfg.cls}`}>{cfg.label}</span>
  )
}

/** Recommendation card with expandable details */
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

/** Predictive warning card */
function PredictionCard({ pred }) {
  const urgency = pred.minutes_to_breach < 3 ? 'critical' : pred.minutes_to_breach < 7 ? 'warning' : 'info'
  const colors = {
    critical: 'border-red-700/50 bg-red-900/10',
    warning: 'border-yellow-700/50 bg-yellow-900/10',
    info: 'border-blue-700/50 bg-blue-900/10',
  }[urgency]

  return (
    <div className={`rounded-xl p-4 border ${colors}`}>
      <div className="flex items-center gap-2 mb-2">
        <Zap size={14} className={urgency === 'critical' ? 'text-red-400' : urgency === 'warning' ? 'text-yellow-400' : 'text-blue-400'} />
        <span className="text-xs font-bold text-white uppercase">
          {pred.category} — {pred.source_id}
        </span>
        <span className="ml-auto text-[10px] font-bold bg-orange-900/50 text-orange-400 px-1.5 py-0.5 rounded border border-orange-700/50">
          ESTIMATE
        </span>
      </div>
      <div className="grid grid-cols-2 gap-2 text-xs mt-2">
        <div>
          <span className="text-gray-500">Current: </span>
          <span className="text-white font-semibold">{pred.current_value?.toFixed(1)}</span>
        </div>
        <div>
          <span className="text-gray-500">Projected: </span>
          <span className="text-orange-400 font-semibold">{pred.projected_value?.toFixed(1)}</span>
        </div>
        <div>
          <span className="text-gray-500">Threshold: </span>
          <span className="text-red-400 font-semibold">{pred.threshold?.toFixed(1)}</span>
        </div>
        <div>
          <span className="text-gray-500">Time to breach: </span>
          <span className="text-yellow-400 font-semibold">~{pred.minutes_to_breach?.toFixed(1)}m</span>
        </div>
      </div>
      <p className="text-[10px] text-gray-500 mt-2 leading-relaxed">{pred.confidence_basis}</p>
    </div>
  )
}

/** Ask Sentinel AI chat widget */
function AskSentinelAI() {
  const [question, setQuestion] = useState('')
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: 'Hello! I\'m Sentinel AI. Ask me about your infrastructure health, incidents, or collector status. I answer only from approved metadata — no raw logs or secrets are shared with any external service.',
      source: 'system',
    }
  ])
  const [loading, setLoading] = useState(false)

  const exampleQuestions = [
    'Which server has the highest CPU?',
    'What incidents occurred recently?',
    'What is the collector status?',
    'Why might a server be unhealthy?',
  ]

  const ask = async (q) => {
    if (!q.trim()) return
    const userMsg = { role: 'user', content: q }
    setMessages(prev => [...prev, userMsg])
    setQuestion('')
    setLoading(true)

    try {
      const r = await api.post('/aiops/ask', { question: q.trim() })
      const { answer, source, warning } = r.data
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: answer,
        source,
        warning,
      }])
    } catch (e) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please check that the backend is running.',
        source: 'error',
      }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl flex flex-col" style={{ minHeight: '500px' }}>
      {/* Header */}
      <div className="p-4 border-b border-gray-800 flex items-center gap-3">
        <div className="w-8 h-8 rounded-full bg-cyan-500/20 flex items-center justify-center">
          <Brain size={16} className="text-cyan-400" />
        </div>
        <div>
          <p className="text-sm font-semibold text-white">Ask Sentinel AI</p>
          <p className="text-[10px] text-gray-500">Powered by IBM watsonx Granite · Metadata-only context · No raw logs transmitted</p>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 p-4 space-y-3 overflow-y-auto max-h-72">
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[85%] rounded-xl px-4 py-2.5 text-sm ${
              msg.role === 'user'
                ? 'bg-cyan-600/30 text-cyan-100 border border-cyan-700/40'
                : 'bg-gray-800 text-gray-200 border border-gray-700/50'
            }`}>
              <p className="leading-relaxed whitespace-pre-wrap">{msg.content}</p>
              {msg.source && msg.role === 'assistant' && msg.source !== 'system' && (
                <p className="text-[10px] text-gray-500 mt-1.5">
                  Source: {msg.source === 'watsonx' ? '🤖 IBM watsonx Granite' : '🔧 Local rule-based engine'}
                </p>
              )}
              {msg.warning && (
                <p className="text-[9px] text-yellow-600/80 mt-1 italic">{msg.warning}</p>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-gray-800 border border-gray-700/50 rounded-xl px-4 py-2.5 flex items-center gap-2">
              <Loader2 size={12} className="text-cyan-400 animate-spin" />
              <span className="text-xs text-gray-400">Sentinel AI is thinking...</span>
            </div>
          </div>
        )}
      </div>

      {/* Example questions */}
      <div className="px-4 pb-2 flex flex-wrap gap-1.5">
        {exampleQuestions.map((q, i) => (
          <button
            key={i}
            onClick={() => ask(q)}
            disabled={loading}
            className="text-[10px] px-2 py-1 rounded-full bg-gray-800 hover:bg-gray-700 text-gray-400 hover:text-gray-200 border border-gray-700 transition-colors disabled:opacity-50"
          >
            {q}
          </button>
        ))}
      </div>

      {/* Input */}
      <div className="p-4 border-t border-gray-800 flex gap-2">
        <input
          value={question}
          onChange={e => setQuestion(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && !loading && ask(question)}
          placeholder="Ask about your infrastructure..."
          disabled={loading}
          className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-cyan-500 disabled:opacity-50"
        />
        <button
          onClick={() => ask(question)}
          disabled={loading || !question.trim()}
          className="bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg p-2 transition-colors"
        >
          {loading ? <Loader2 size={16} className="text-white animate-spin" /> : <Send size={16} className="text-white" />}
        </button>
      </div>

      <div className="px-4 pb-3">
        <p className="text-[9px] text-gray-600 italic">
          Privacy guarantee: Only approved metadata (metric values, incident titles, severity, collector status)
          is included in the AI context. Raw logs, secrets, passwords, and sensitive records are NEVER sent to IBM watsonx.
        </p>
      </div>
    </div>
  )
}

/** Main page */
export default function AIInsights() {
  const [anomalies, setAnomalies] = useState([])
  const [recommendations, setRecommendations] = useState([])
  const [predictions, setPredictions] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const load = async () => {
      try {
        const [a, r, p] = await Promise.all([
          api.get('/aiops/anomalies?limit=20'),
          api.get('/aiops/recommendations?limit=10'),
          api.get('/aiops/predictions'),
        ])
        setAnomalies(a.data)
        setRecommendations(r.data)
        setPredictions(p.data?.predictions || [])
      } catch (e) {}
      finally { setLoading(false) }
    }
    load()
    const t = setInterval(load, 15000)
    return () => clearInterval(t)
  }, [])

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-white">AI Insights</h1>
        <p className="text-sm text-gray-400 mt-0.5">
          Explainable anomaly detection, predictive warnings, and AI-powered recommendations
        </p>
      </div>

      {/* How it works */}
      <div className="p-4 rounded-xl bg-cyan-900/10 border border-cyan-500/20">
        <div className="flex items-center gap-2 text-cyan-400 text-sm font-medium mb-1">
          <Info size={14} />
          How anomaly detection works
        </div>
        <p className="text-xs text-gray-400">
          Z-score analysis: anomalies are flagged when a metric deviates more than 2.5 standard deviations
          from its rolling baseline (last 50 samples, persisted in SQLite — survives restarts).
          A warm-up state is shown when fewer than 10 samples exist.
          Predictive warnings use linear regression over recent data points — labeled as ESTIMATES only.
          No external LLM is used for core detections — all explanations are grounded in actual metric values.
        </p>
      </div>

      {/* Predictive warnings */}
      {predictions.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-gray-200 mb-3 flex items-center gap-2">
            <Zap size={14} className="text-orange-400" />
            Predictive Warnings ({predictions.length})
            <span className="text-xs text-orange-400/70 font-normal">— linear trend estimates only</span>
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {predictions.map((p, i) => <PredictionCard key={i} pred={p} />)}
          </div>
        </div>
      )}

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
                  <p className="text-[10px] text-gray-600 mt-2">{formatTimestamp(a.detected_at)}</p>
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

      {/* Ask Sentinel AI */}
      <div>
        <h3 className="text-sm font-semibold text-gray-200 mb-3 flex items-center gap-2">
          <MessageSquare size={14} className="text-purple-400" />
          Ask Sentinel AI
          <span className="text-xs text-purple-400/70 font-normal">— IBM watsonx powered</span>
        </h3>
        <AskSentinelAI />
      </div>
    </div>
  )
}
