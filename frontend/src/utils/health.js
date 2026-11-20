/**
 * frontend/src/utils/health.js
 * Health state utilities — colors, icons, labels.
 */

export const HEALTH_CONFIG = {
  excellent: {
    label: 'Excellent',
    color: 'text-green-400',
    bg: 'bg-green-400/10',
    border: 'border-green-400/30',
    dot: 'bg-green-400',
    badge: 'bg-green-900/50 text-green-300 border border-green-500/40',
  },
  good: {
    label: 'Good',
    color: 'text-blue-400',
    bg: 'bg-blue-400/10',
    border: 'border-blue-400/30',
    dot: 'bg-blue-400',
    badge: 'bg-blue-900/50 text-blue-300 border border-blue-500/40',
  },
  fair: {
    label: 'Fair',
    color: 'text-yellow-400',
    bg: 'bg-yellow-400/10',
    border: 'border-yellow-400/30',
    dot: 'bg-yellow-400',
    badge: 'bg-yellow-900/50 text-yellow-300 border border-yellow-500/40',
  },
  poor: {
    label: 'Poor',
    color: 'text-red-400',
    bg: 'bg-red-400/10',
    border: 'border-red-400/30',
    dot: 'bg-red-400',
    badge: 'bg-red-900/50 text-red-300 border border-red-500/40',
  },
}

export const SEVERITY_CONFIG = {
  critical: { label: 'Critical', color: 'text-red-400', bg: 'bg-red-900/30' },
  warning:  { label: 'Warning',  color: 'text-yellow-400', bg: 'bg-yellow-900/30' },
  info:     { label: 'Info',     color: 'text-blue-400', bg: 'bg-blue-900/30' },
  resolved: { label: 'Resolved', color: 'text-green-400', bg: 'bg-green-900/30' },
}

export function getHealthConfig(state) {
  return HEALTH_CONFIG[state?.toLowerCase()] || HEALTH_CONFIG.excellent
}

export function getSeverityConfig(severity) {
  return SEVERITY_CONFIG[severity?.toLowerCase()] || SEVERITY_CONFIG.info
}

export function formatTimestamp(ts) {
  if (!ts) return 'N/A'
  return new Date(ts).toLocaleString('en-US', {
    month: 'short', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
    timeZone: 'UTC', timeZoneName: 'short',
  })
}

export function timeAgo(ts) {
  if (!ts) return 'N/A'
  const diff = (Date.now() - new Date(ts).getTime()) / 1000
  if (diff < 60) return `${Math.round(diff)}s ago`
  if (diff < 3600) return `${Math.round(diff / 60)}m ago`
  return `${Math.round(diff / 3600)}h ago`
}
