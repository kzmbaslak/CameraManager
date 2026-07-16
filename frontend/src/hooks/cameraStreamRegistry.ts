// Kamera WebSocket bağlantılarını kamera başına tek paylaşımlı bağlantıda toplar.
import type { StreamProfile } from './useCameraStream'
import type { StreamMessage } from '../types/api'

type StreamListener = (state: StreamState) => void

export interface StreamState {
  frame: string | null
  alarmTriggered: boolean
  alarmId: number | null
  connected: boolean
}

interface StreamSubscriptionOptions {
  profile: StreamProfile
  accessToken: string | null
  tokenFactory: () => Promise<string | null>
  onUpdate: StreamListener
}

const PROFILE_WEIGHT: Record<StreamProfile, number> = {
  alarm: 1,
  grid: 2,
  live: 3,
}

interface SharedStream {
  cameraId: number
  listeners: Set<StreamListener>
  listenerProfiles: Map<StreamListener, StreamProfile>
  state: StreamState
  websocket: WebSocket | null
  retryTimer: ReturnType<typeof setTimeout> | null
  reconnectTimer: ReturnType<typeof setTimeout> | null
  retryDelay: number
  accessToken: string | null
  tokenFactory: () => Promise<string | null>
  profile: StreamProfile
  objectUrl: string | null
  disposed: boolean
  disposeTimer: ReturnType<typeof setTimeout> | null
  pendingReconnect: boolean
}

const streams = new Map<number, SharedStream>()
let visibilityListenerAttached = false

function initialState(): StreamState {
  return {
    frame: null,
    alarmTriggered: false,
    alarmId: null,
    connected: false,
  }
}

function clearObjectUrl(stream: SharedStream) {
  if (stream.objectUrl) {
    URL.revokeObjectURL(stream.objectUrl)
    stream.objectUrl = null
  }
}

function isTabVisible() {
  return typeof document === 'undefined' || document.visibilityState !== 'hidden'
}

function emit(stream: SharedStream) {
  for (const listener of stream.listeners) {
    listener(stream.state)
  }
}

function ensureVisibilityListener() {
  if (visibilityListenerAttached || typeof document === 'undefined') {
    return
  }
  visibilityListenerAttached = true
  document.addEventListener('visibilitychange', () => {
    if (!isTabVisible()) {
      return
    }
    for (const stream of streams.values()) {
      if (stream.pendingReconnect && stream.listeners.size > 0 && stream.accessToken) {
        stream.pendingReconnect = false
        requestReconnect(stream, 0)
      }
    }
  })
}

function effectiveProfile(stream: SharedStream): StreamProfile {
  let best: StreamProfile = 'alarm'
  for (const profile of stream.listenerProfiles.values()) {
    if (PROFILE_WEIGHT[profile] > PROFILE_WEIGHT[best]) {
      best = profile
    }
  }
  return best
}

function buildUrl(cameraId: number, profile: StreamProfile) {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.host
  const qs = new URLSearchParams({ profile })
  return `${protocol}//${host}/api/streams/${cameraId}?${qs.toString()}`
}

async function connect(stream: SharedStream) {
  if (stream.disposed) return
  if (stream.reconnectTimer) {
    clearTimeout(stream.reconnectTimer)
    stream.reconnectTimer = null
  }
  if (stream.websocket) {
    try {
      stream.websocket.close()
    } catch {
      // Bağlantı zaten kapanıyor olabilir.
    }
    stream.websocket = null
  }

  const streamToken = await stream.tokenFactory()
  if (!streamToken || stream.disposed || stream.listeners.size === 0) {
    return
  }

  const ws = new WebSocket(buildUrl(stream.cameraId, stream.profile))
  ws.binaryType = 'blob'
  stream.websocket = ws

  ws.onopen = () => {
    ws.send(JSON.stringify({ token: streamToken }))
    stream.retryDelay = 1_000
    stream.state = { ...stream.state, connected: true }
    emit(stream)
  }

  ws.onmessage = (e) => {
    if (typeof e.data !== 'string') {
      clearObjectUrl(stream)
      const blob = e.data instanceof Blob ? e.data : new Blob([e.data], { type: 'image/jpeg' })
      const frameUrl = URL.createObjectURL(blob)
      stream.objectUrl = frameUrl
      stream.state = {
        ...stream.state,
        frame: frameUrl,
        connected: true,
      }
      emit(stream)
      return
    }

    const msg = JSON.parse(e.data) as StreamMessage & { error?: string }
    if (msg.error) {
      ws.close()
      return
    }

    stream.state = {
      ...stream.state,
      frame: msg.frame ? `data:image/jpeg;base64,${msg.frame}` : stream.state.frame,
      alarmTriggered: Boolean(msg.alarm_triggered),
      alarmId: msg.alarm_id ?? null,
      connected: true,
    }
    emit(stream)
  }

  ws.onclose = () => {
    if (stream.websocket === ws) stream.websocket = null
    stream.state = { ...stream.state, connected: false }
    emit(stream)
    if (!stream.disposed && stream.listeners.size > 0) {
      if (isTabVisible()) {
        stream.retryTimer = setTimeout(() => {
          void connect(stream)
        }, stream.retryDelay)
        stream.retryDelay = Math.min(stream.retryDelay * 2, 15_000)
      } else {
        stream.pendingReconnect = true
      }
    }
  }

  ws.onerror = () => ws.close()
}

function ensureStream(cameraId: number): SharedStream {
  const existing = streams.get(cameraId)
  if (existing) return existing

  const created: SharedStream = {
    cameraId,
    listeners: new Set(),
    listenerProfiles: new Map(),
    state: initialState(),
    websocket: null,
    retryTimer: null,
    reconnectTimer: null,
    retryDelay: 1_000,
    accessToken: null,
    tokenFactory: async () => null,
    profile: 'alarm',
    objectUrl: null,
    disposed: false,
    disposeTimer: null,
    pendingReconnect: false,
  }
  streams.set(cameraId, created)
  ensureVisibilityListener()
  return created
}

function scheduleDispose(cameraId: number, stream: SharedStream) {
  if (stream.disposeTimer) {
    clearTimeout(stream.disposeTimer)
  }
  if (stream.reconnectTimer) {
    clearTimeout(stream.reconnectTimer)
    stream.reconnectTimer = null
  }
  stream.disposeTimer = setTimeout(() => {
    if (stream.listeners.size > 0) {
      return
    }
    stream.disposed = true
    clearObjectUrl(stream)
    if (stream.websocket) {
      try {
        stream.websocket.close()
      } catch {
        // Kapama zaten devam ediyor olabilir.
      }
    }
    stream.websocket = null
    streams.delete(cameraId)
  }, 8_000)
}

function requestReconnect(stream: SharedStream, delay = 120) {
  if (stream.disposed || stream.listeners.size === 0) return
  if (stream.reconnectTimer) {
    return
  }
  stream.reconnectTimer = setTimeout(() => {
    stream.reconnectTimer = null
    void connect(stream)
  }, delay)
}

export function subscribeToCameraStream(cameraId: number, options: StreamSubscriptionOptions) {
  const stream = ensureStream(cameraId)
  if (stream.disposeTimer) {
    clearTimeout(stream.disposeTimer)
    stream.disposeTimer = null
  }
  stream.disposed = false
  stream.listeners.add(options.onUpdate)
  stream.listenerProfiles.set(options.onUpdate, options.profile)

  const nextProfile = effectiveProfile(stream)
  const tokenChanged = stream.accessToken !== options.accessToken
  const profileChanged = nextProfile !== stream.profile
  stream.accessToken = options.accessToken
  stream.tokenFactory = options.tokenFactory
  stream.profile = nextProfile

  if (stream.retryTimer) {
    clearTimeout(stream.retryTimer)
    stream.retryTimer = null
  }
  if (stream.pendingReconnect && isTabVisible()) {
    stream.pendingReconnect = false
  }

  options.onUpdate(stream.state)

  if (options.accessToken && (!stream.websocket || tokenChanged || profileChanged)) {
    requestReconnect(stream, isTabVisible() ? 120 : 0)
  }

  return () => {
    stream.listeners.delete(options.onUpdate)
    stream.listenerProfiles.delete(options.onUpdate)

    const updatedProfile = effectiveProfile(stream)
    const shouldReconnect = updatedProfile !== stream.profile
    stream.profile = updatedProfile

    if (stream.listeners.size === 0) {
      if (stream.retryTimer) clearTimeout(stream.retryTimer)
      if (stream.reconnectTimer) clearTimeout(stream.reconnectTimer)
      stream.pendingReconnect = false
      scheduleDispose(cameraId, stream)
      return
    }

    if (shouldReconnect && stream.accessToken) {
      requestReconnect(stream, isTabVisible() ? 120 : 0)
    }
  }
}
