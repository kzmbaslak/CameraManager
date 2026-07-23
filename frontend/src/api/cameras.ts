// Kamera CRUD API çağrıları — list, get, add, update, updateStatus, toggleAI, delete
import client from './client'
import type { Camera, CameraCreate, CameraStatus, CameraScanRequest, CameraScanResult, CameraHealthSummary, CameraRtspDiagnostics, CameraRtspPreviewRequest, CameraStreamDiagnostics, StreamTokenResponse } from '../types/api'

/** Kamera güncelleme için kısmi veri tipi */
export interface CameraUpdate {
  name?: string
  host?: string
  rtsp_port?: number
  rtsp_path?: string
  onvif_port?: number
  username?: string
  password?: string
  ai_confidence_threshold?: number
  ai_iou_threshold?: number
  ai_alarm_cooldown_seconds?: number
  ai_frame_stride?: number
  ai_inference_width?: number
  ai_active_start?: string | null
  ai_active_end?: string | null
  ai_roi_polygon?: string | null
}

export const camerasApi = {
  /** Sistemdeki tüm kameraları listeler. */
  list: async (): Promise<Camera[]> => {
    const { data } = await client.get<Camera[]>('/cameras/')
    return data
  },

  /** Belirli bir kameranın detaylarını getirir. */
  get: async (id: number): Promise<Camera> => {
    const { data } = await client.get<Camera>(`/cameras/${id}`)
    return data
  },

  /** Sisteme yeni kamera ekler. */
  add: async (payload: CameraCreate): Promise<Camera> => {
    const { data } = await client.post<Camera>('/cameras/', payload)
    return data
  },

  /** Kameranın ad, host, port gibi bağlantı bilgilerini günceller. */
  update: async (id: number, payload: CameraUpdate): Promise<Camera> => {
    const { data } = await client.patch<Camera>(`/cameras/${id}`, payload)
    return data
  },

  /** Kamerayı ACTIVE veya INACTIVE yapar; worker buna göre başlar/durur. */
  updateStatus: async (id: number, status: CameraStatus): Promise<Camera> => {
    const { data } = await client.patch<Camera>(`/cameras/${id}/status`, null, {
      params: { status },
    })
    return data
  },

  /** AI insan tespitini açar veya kapatır; kamera aktifken worker güncellenir. */
  toggleAI: async (id: number, enabled: boolean): Promise<Camera> => {
    const { data } = await client.patch<Camera>(`/cameras/${id}/ai`, null, {
      params: { enabled },
    })
    return data
  },

  /** Kamerayı sistemden siler. */
  delete: async (id: number): Promise<void> => {
    await client.delete(`/cameras/${id}`)
  },

  /** Ağdaki kameraları tarar. AbortSignal ile iptal edilebilir. */
  scan: async (payload: CameraScanRequest, signal?: AbortSignal): Promise<CameraScanResult[]> => {
    const { data } = await client.post<CameraScanResult[]>('/cameras/scan', payload, { signal })
    return data
  },

  /** Kayıtlı kameranın RTSP bağlantısını şifre göstermeden test eder. */
  diagnoseRtsp: async (id: number): Promise<CameraRtspDiagnostics> => {
    const { data } = await client.get<CameraRtspDiagnostics>(`/cameras/${id}/diagnostics/rtsp`)
    return data
  },

  /** Kaydetmeden formdaki RTSP baglantisini test eder. */
  previewRtsp: async (payload: CameraRtspPreviewRequest): Promise<CameraRtspDiagnostics> => {
    const { data } = await client.post<CameraRtspDiagnostics>('/cameras/diagnostics/rtsp-preview', payload)
    return data
  },

  /** Canlı akış üretici ve RTSP sağlık metriklerini döner. */
  diagnoseStream: async (id: number): Promise<CameraStreamDiagnostics> => {
    const { data } = await client.get<CameraStreamDiagnostics>(`/cameras/${id}/diagnostics/stream`)
    return data
  },

  /** Kameranin son erisilebilirlik gecmisi ve trend ozetini dondurur. */
  diagnoseHealthHistory: async (id: number, limit = 120): Promise<CameraHealthSummary> => {
    const { data } = await client.get<CameraHealthSummary>(`/cameras/${id}/diagnostics/health-history`, {
      params: { limit },
    })
    return data
  },

  /** WebSocket canlı izleme için kısa ömürlü stream token'ı alır. */
  getStreamToken: async (id: number): Promise<StreamTokenResponse> => {
    const { data } = await client.get<StreamTokenResponse>(`/cameras/${id}/stream-token`)
    return data
  },

  /** Birden fazla kamerayı toplu olarak ekler. */
  bulkAdd: async (payload: CameraCreate[]): Promise<Camera[]> => {
    const { data } = await client.post<Camera[]>('/cameras/bulk-add', payload)
    return data
  },
}
