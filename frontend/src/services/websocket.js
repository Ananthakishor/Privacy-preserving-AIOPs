/**
 * frontend/src/services/websocket.js
 * WebSocket client for real-time notifications.
 * Automatically reconnects on disconnect.
 */

let ws = null
let reconnectTimer = null
const listeners = new Set()

export function connectWebSocket(tenantId, onMessage) {
  if (ws && ws.readyState === WebSocket.OPEN) return

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const url = `${protocol}//${window.location.hostname}:8000/api/v1/notifications/ws?tenant_id=${tenantId}`

  ws = new WebSocket(url)

  ws.onopen = () => {
    console.log('[WS] Connected to notification stream')
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
  }

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      listeners.forEach(listener => listener(data))
      if (onMessage) onMessage(data)
    } catch (e) {
      // ignore malformed messages
    }
  }

  ws.onclose = () => {
    console.log('[WS] Disconnected — reconnecting in 5s...')
    reconnectTimer = setTimeout(() => connectWebSocket(tenantId, onMessage), 5000)
  }

  ws.onerror = (err) => {
    console.warn('[WS] Error:', err)
  }
}

export function addNotificationListener(fn) {
  listeners.add(fn)
  return () => listeners.delete(fn)
}

export function disconnectWebSocket() {
  if (ws) ws.close()
}
