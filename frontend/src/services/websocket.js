import { apiOrigin } from './api'

const listeners = new Set()

export function connectWebSocket(token, onMessage) {
  const url = new URL('/api/v1/notifications/ws', apiOrigin)
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
  let socket
  let retry
  let active = true

  function connect() {
    socket = new WebSocket(url)
    socket.onopen = () => {
      if (active) socket.send(token)
    }
    socket.onmessage = ({ data }) => {
      if (!active) return
      const message = JSON.parse(data)
      listeners.forEach(listener => listener(message))
      onMessage(message)
    }
    socket.onclose = ({ code }) => {
      if (active && code !== 1008) retry = setTimeout(connect, 5000)
    }
  }

  connect()
  return () => {
    active = false
    clearTimeout(retry)
    socket.close()
  }
}

export function addNotificationListener(fn) {
  listeners.add(fn)
  return () => listeners.delete(fn)
}
