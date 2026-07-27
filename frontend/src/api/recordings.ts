// Recording segment API cagrilari.
import client from './client'
import type { RecordingSegmentListResponse } from '../types/api'

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
}
