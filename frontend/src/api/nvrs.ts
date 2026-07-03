import client from './client'
import type { NVR, NVRCreate, NVRChannelInfo, Camera, NVRScanRequest, NVRScanResponse } from '../types/api'

/** NVR güncelleme için kısmi veri tipi */
export interface NVRUpdate {
  name?: string
  host?: string
  onvif_port?: number
  username?: string
  password?: string
}

export const nvrsApi = {
  /** Sistemdeki tüm NVR cihazlarını listeler. */
  list: async (): Promise<NVR[]> => {
    const { data } = await client.get<NVR[]>('/nvrs/')
    return data
  },

  /** Belirli bir NVR'ın detaylarını getirir. */
  get: async (id: number): Promise<NVR> => {
    const { data } = await client.get<NVR>(`/nvrs/${id}`)
    return data
  },

  /** Sisteme yeni NVR cihazı ekler. */
  add: async (payload: NVRCreate): Promise<NVR> => {
    const { data } = await client.post<NVR>('/nvrs/', payload)
    return data
  },

  /** Birden fazla NVR'ı toplu olarak sisteme ekler. */
  bulkAdd: async (payload: NVRCreate[]): Promise<NVR[]> => {
    const { data } = await client.post<NVR[]>('/nvrs/bulk-add', payload)
    return data
  },

  /** NVR'ın ad, host, port gibi bilgilerini günceller. */
  update: async (id: number, payload: NVRUpdate): Promise<NVR> => {
    const { data } = await client.patch<NVR>(`/nvrs/${id}`, payload)
    return data
  },

  /** NVR'ı aktif veya pasif yapar. */
  toggleStatus: async (id: number, isActive: boolean): Promise<NVR> => {
    const { data } = await client.patch<NVR>(`/nvrs/${id}/status`, null, {
      params: { is_active: isActive },
    })
    return data
  },

  /** NVR'ı sistemden siler (bağlı kameralar NVR bağlantısını kaybeder). */
  delete: async (id: number): Promise<void> => {
    await client.delete(`/nvrs/${id}`)
  },

  /** ONVIF ile NVR kanallarını listeler — kaydetmez, yalnızca önizleme. */
  probe: async (id: number): Promise<NVRChannelInfo[]> => {
    const { data } = await client.post<NVRChannelInfo[]>(`/nvrs/${id}/probe`)
    return data
  },

  /** Tüm keşfedilen kanalları sisteme kamera olarak aktarır. */
  importChannels: async (id: number, channels: NVRChannelInfo[]): Promise<Camera[]> => {
    const { data } = await client.post<Camera[]>(`/nvrs/${id}/import`, { channels })
    return data
  },

  /** Seçili kanalları sisteme aktarır. */
  importSelected: async (id: number, channels: NVRChannelInfo[]): Promise<Camera[]> => {
    const { data } = await client.post<Camera[]>(`/nvrs/${id}/import`, { channels })
    return data
  },

  /** WS-Discovery ile yerel ağdaki ONVIF/NVR cihazlarını arar. */
  discover: async (): Promise<{ xaddr: string; host: string; port: number }[]> => {
    const { data } = await client.post<{ xaddr: string; host: string; port: number }[]>('/nvrs/discover')
    return data
  },

  /** IP aralığına göre NVR cihazlarını (VideoEdge, Hikvision, Dahua) tarar. AbortSignal ile iptal edilebilir. */
  scan: async (payload: NVRScanRequest, signal?: AbortSignal): Promise<NVRScanResponse[]> => {
    const { data } = await client.post<NVRScanResponse[]>('/nvrs/scan', payload, { signal })
    return data
  },
}

