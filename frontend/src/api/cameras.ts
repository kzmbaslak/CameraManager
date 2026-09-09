// Kamera CRUD API çağrıları — list, get, add, update, updateStatus, toggleAI, delete
import client from './client'
import type { Camera, CameraCreate, CameraPageResponse, CameraPtzGotoPresetRequest, CameraPtzGotoPresetResponse, CameraPtzHomeResponse, CameraPtzMoveRequest, CameraPtzMoveResponse, CameraPtzPatrolRequest, CameraPtzPatrolResponse, CameraPtzPresetListResponse, CameraStatus, CameraScanRequest, CameraScanResult, CameraHealthListItem, CameraHealthSummary, CameraOnvifPreviewRequest, CameraOnvifPreviewResponse, CameraRtspDiagnostics, CameraRtspPreviewRequest, CameraStreamDiagnostics, CameraStreamMetricSummary, StreamTokenResponse, OpenApiSchemas } from '../types/api'

/** Kamera güncelleme için kısmi veri tipi */
export type CameraUpdate = OpenApiSchemas['CameraUpdate']

export type CameraBulkAiSettingsPayload = OpenApiSchemas['CameraBulkAiSettingsRequest']

export const camerasApi = {
  /** Sistemdeki tüm kameraları listeler. */
  list: async (): Promise<Camera[]> => {
    const { data } = await client.get<Camera[]>('/cameras/')
    return data
  },

  listPaginated: async (params: {
    page: number
    page_size: number
    search?: string
    status?: CameraStatus | 'all'
    ai_filter?: 'all' | 'enabled' | 'disabled'
    sort?: string
  }): Promise<CameraPageResponse> => {
    const { data } = await client.get<CameraPageResponse>('/cameras/', {
      params: { paginated: true, ...params },
    })
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

  /** Kaydetmeden formdaki ONVIF baglantisini ve stream profillerini test eder. */
  previewOnvif: async (payload: CameraOnvifPreviewRequest): Promise<CameraOnvifPreviewResponse> => {
    const { data } = await client.post<CameraOnvifPreviewResponse>('/cameras/diagnostics/onvif-preview', payload)
    return data
  },

  /** Kayitli kameraya kisa sureli ONVIF PTZ hareket komutu gonderir. */
  ptzMove: async (id: number, payload: CameraPtzMoveRequest): Promise<CameraPtzMoveResponse> => {
    const { data } = await client.post<CameraPtzMoveResponse>(`/cameras/${id}/ptz/move`, payload)
    return data
  },

  /** Kayitli kameranin ONVIF PTZ preset listesini alir. */
  ptzPresets: async (id: number): Promise<CameraPtzPresetListResponse> => {
    const { data } = await client.get<CameraPtzPresetListResponse>(`/cameras/${id}/ptz/presets`)
    return data
  },

  /** Kamerayi ONVIF PTZ preset pozisyonuna gonderir. */
  ptzGotoPreset: async (id: number, presetToken: string): Promise<CameraPtzGotoPresetResponse> => {
    const payload: CameraPtzGotoPresetRequest = { preset_token: presetToken }
    const { data } = await client.post<CameraPtzGotoPresetResponse>(`/cameras/${id}/ptz/presets/goto`, payload)
    return data
  },

  /** Kamerayi ONVIF PTZ home pozisyonuna gonderir. */
  ptzHome: async (id: number): Promise<CameraPtzHomeResponse> => {
    const { data } = await client.post<CameraPtzHomeResponse>(`/cameras/${id}/ptz/home`)
    return data
  },

  /** Secili presetleri sirayla gezerek kisa ONVIF PTZ patrol calistirir. */
  ptzPatrol: async (id: number, payload: CameraPtzPatrolRequest): Promise<CameraPtzPatrolResponse> => {
    const { data } = await client.post<CameraPtzPatrolResponse>(`/cameras/${id}/ptz/patrol`, payload)
    return data
  },

  /** Canlı akış üretici ve RTSP sağlık metriklerini döner. */
  diagnoseStream: async (id: number): Promise<CameraStreamDiagnostics> => {
    const { data } = await client.get<CameraStreamDiagnostics>(`/cameras/${id}/diagnostics/stream`)
    return data
  },

  /** Kameranin kalici stream performans gecmisi ve trend ozetini dondurur. */
  diagnoseStreamHistory: async (id: number, limit = 120): Promise<CameraStreamMetricSummary> => {
    const { data } = await client.get<CameraStreamMetricSummary>(`/cameras/${id}/diagnostics/stream-history`, {
      params: { limit },
    })
    return data
  },

  /** Kameranin son erisilebilirlik gecmisi ve trend ozetini dondurur. */
  diagnoseHealthHistory: async (id: number, limit = 120): Promise<CameraHealthSummary> => {
    const { data } = await client.get<CameraHealthSummary>(`/cameras/${id}/diagnostics/health-history`, {
      params: { limit },
    })
    return data
  },

  /** Kamera listesi icin kompakt saglik ozetlerini dondurur. */
  healthSummary: async (cameraIds: number[], limit = 120): Promise<CameraHealthListItem[]> => {
    const params = new URLSearchParams()
    cameraIds.forEach((id) => params.append('camera_ids', String(id)))
    params.set('limit', String(limit))
    const { data } = await client.get<CameraHealthListItem[]>('/cameras/diagnostics/health-summary', {
      params,
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

  /** Secili kameralara ayni AI profil ayarlarini uygular. */
  bulkUpdateAiSettings: async (payload: CameraBulkAiSettingsPayload): Promise<Camera[]> => {
    const { data } = await client.post<Camera[]>('/cameras/bulk-ai-settings', payload)
    return data
  },
}
