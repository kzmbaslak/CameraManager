// Kamera akışına abone olur ve geçici bağlantı kesintilerinde yeniden bağlanır.
import { useEffect, useState } from 'react'

import { camerasApi } from '../api/cameras'
import { useAuthStore } from '../stores/authStore'
import { subscribeToCameraStream, type StreamState } from './cameraStreamRegistry'

export type StreamProfile = 'grid' | 'live' | 'alarm'

/** Kamera akışına abone olur ve paylaşılan WebSocket üzerinden güncel kareyi döner. */
export function useCameraStream(cameraId: number, enabled = true, profile: StreamProfile = 'grid'): StreamState {
  const [state, setState] = useState<StreamState>({
    frame: null,
    alarmTriggered: false,
    alarmId: null,
    connected: false,
  })
  const token = useAuthStore((s) => s.token)

  useEffect(() => {
    if (!enabled) {
      return
    }

    return subscribeToCameraStream(cameraId, {
      profile,
      accessToken: token,
      tokenFactory: async () => {
        if (!token) return null
        const data = await camerasApi.getStreamToken(cameraId)
        return data.stream_token
      },
      onUpdate: setState,
    })
  }, [cameraId, enabled, profile, token])

  return state
}
