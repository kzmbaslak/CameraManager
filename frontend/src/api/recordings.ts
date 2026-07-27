// Recording segment API cagrilari.
import client from './client'
import type { RecordingPruneResult, RecordingSegmentListResponse } from '../types/api'

export const recordingsApi = {
  /** Kayit segmentlerini kamera ve zaman araligina gore listeler. */
  list: async (params: {
    camera_id?: number
    since?: string
    until?: string
    limit?: number
  } = {}): Promise<RecordingSegmentListResponse> => {
    const { data } = await client.get<RecordingSegmentListResponse>('/recordings/', { params })
    return data
  },

  /** Admin-only kayit retention/disk kotasi temizligini calistirir. */
  prune: async (params: { retention_days?: number; quota_mb?: number } = {}): Promise<RecordingPruneResult> => {
    const { data } = await client.post<RecordingPruneResult>('/recordings/maintenance/prune', undefined, { params })
    return data
  },
}
