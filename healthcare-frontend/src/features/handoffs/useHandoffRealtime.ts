import { useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { handoffKeys, handoffWebSocketUrl } from './api'

export type RealtimeState = 'disabled' | 'connecting' | 'connected' | 'reconnecting' | 'error'

export function useHandoffRealtime(enabled: boolean) {
  const client = useQueryClient()
  const [state, setState] = useState<RealtimeState>(enabled ? 'connecting' : 'disabled')

  useEffect(() => {
    if (!enabled) {
      return undefined
    }
    let active = true
    let socket: WebSocket | null = null
    let timer: number | undefined
    let attempt = 0

    const connect = () => {
      if (!active) return
      setState(attempt === 0 ? 'connecting' : 'reconnecting')
      try {
        socket = new WebSocket(handoffWebSocketUrl())
      } catch {
        setState('error')
        timer = window.setTimeout(connect, 2000)
        return
      }
      socket.onopen = () => {
        attempt = 0
        setState('connected')
        void client.invalidateQueries({ queryKey: handoffKeys.all })
      }
      socket.onmessage = (event) => {
        try {
          const payload = JSON.parse(String(event.data)) as { type?: string }
          if (payload.type === 'handoff.created' || payload.type === 'handoff.updated') {
            void client.invalidateQueries({ queryKey: handoffKeys.all })
          }
        } catch {
          // Ignore malformed best-effort notifications and keep REST state authoritative.
        }
      }
      socket.onerror = () => setState('error')
      socket.onclose = () => {
        if (!active) return
        attempt += 1
        setState('reconnecting')
        const delay = Math.min(1000 * 2 ** (attempt - 1), 10_000)
        timer = window.setTimeout(connect, delay)
      }
    }

    connect()
    return () => {
      active = false
      if (timer !== undefined) window.clearTimeout(timer)
      socket?.close()
    }
  }, [client, enabled])

  return enabled ? state : 'disabled'
}
