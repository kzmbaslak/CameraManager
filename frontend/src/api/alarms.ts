// Alarm API çağrıları — listeleme (tümü, kameraya göre, duruma göre) ve onaylama
import client from './client'
import type { Alarm, AlarmStatus, AlarmType } from '../types/api'

export const alarmsApi = {
  /** Alarmları opsiyonel filtrelerle listeler (kamera, tip, durum). */
  listAll: async (params?: {
    camera_id?: number
    alarm_type?: AlarmType
    status?: AlarmStatus
    limit?: number
  }): Promise<Alarm[]> => {
    const { data } = await client.get<Alarm[]>('/alarms/', { params })
    return data
  },

  /** Belirli bir kameraya ait alarmları listeler. */
  listByCamera: async (cameraId: number, limit = 100): Promise<Alarm[]> => {
    const { data } = await client.get<Alarm[]>(`/alarms/camera/${cameraId}`, { params: { limit } })
    return data
  },

  /** Duruma göre alarm listesi — legacy; yeni kod listAll kullanmalı. */
  listByStatus: async (status: AlarmStatus, limit = 100): Promise<Alarm[]> => {
    const { data } = await client.get<Alarm[]>(`/alarms/status/${status}`, { params: { limit } })
    return data
  },

  /** Alarmı onaylandı olarak işaretler. */
  acknowledge: async (alarmId: number): Promise<Alarm> => {
    const { data } = await client.post<Alarm>(`/alarms/${alarmId}/acknowledge`)
    return data
  },

  /** Alarm atama ve operator notu alanlarini gunceller. */
  update: async (alarmId: number, payload: { assigned_to?: string | null; operator_note?: string | null }): Promise<Alarm> => {
    const { data } = await client.patch<Alarm>(`/alarms/${alarmId}`, payload)
    return data
  },

  /** Alarmi cozum nedeni ile kapatir. */
  resolve: async (alarmId: number, payload: { resolution_reason?: string | null }): Promise<Alarm> => {
    const { data } = await client.post<Alarm>(`/alarms/${alarmId}/resolve`, payload)
    return data
  },

  /** Alarm kanit snapshot dosyasini blob olarak getirir. */
  snapshot: async (alarmId: number): Promise<Blob> => {
    const { data } = await client.get<Blob>(`/alarms/${alarmId}/snapshot`, { responseType: 'blob' })
    return data
  },
}
