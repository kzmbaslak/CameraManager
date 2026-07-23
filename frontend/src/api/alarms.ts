// Alarm API çağrıları — listeleme (tümü, kameraya göre, duruma göre) ve onaylama
import client from './client'
import type { Alarm, AlarmSeverity, AlarmStatus, AlarmTrainingFeedbackItem, AlarmType } from '../types/api'

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
  update: async (alarmId: number, payload: {
    assigned_to?: string | null
    operator_note?: string | null
    severity?: AlarmSeverity
    false_positive?: boolean
  }): Promise<Alarm> => {
    const { data } = await client.patch<Alarm>(`/alarms/${alarmId}`, payload)
    return data
  },

  /** Alarmi cozum nedeni ile kapatir. */
  resolve: async (alarmId: number, payload: { resolution_reason?: string | null; false_positive?: boolean }): Promise<Alarm> => {
    const { data } = await client.post<Alarm>(`/alarms/${alarmId}/resolve`, payload)
    return data
  },

  /** Alarmi tek aksiyonla yanlis alarm olarak kapatir. */
  markFalsePositive: async (alarmId: number): Promise<Alarm> => {
    const { data } = await client.post<Alarm>(`/alarms/${alarmId}/false-positive`)
    return data
  },

  /** AI egitim/threshold iyilestirmesi icin sinirli alarm geri bildirimi alir. */
  trainingFeedback: async (params?: {
    limit?: number
    false_positive_only?: boolean
  }): Promise<AlarmTrainingFeedbackItem[]> => {
    const { data } = await client.get<AlarmTrainingFeedbackItem[]>('/alarms/training-feedback', { params })
    return data
  },

  /** Alarm kanit snapshot dosyasini blob olarak getirir. */
  snapshot: async (alarmId: number, variant: 'raw' | 'annotated' = 'raw'): Promise<{ blob: Blob; sha256: string | null; variant: string | null }> => {
    const path = variant === 'annotated' ? `/alarms/${alarmId}/snapshot/annotated` : `/alarms/${alarmId}/snapshot`
    const { data, headers } = await client.get<Blob>(path, { responseType: 'blob' })
    return {
      blob: data,
      sha256: headers['x-snapshot-sha256'] ?? null,
      variant: headers['x-snapshot-variant'] ?? null,
    }
  },
}
