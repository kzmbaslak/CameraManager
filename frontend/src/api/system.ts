// Sistem saglik ve guvenlik durusu API cagrilari.
import client from './client'
import type { AuditEvent, SecurityPosture } from '../types/api'

export const systemApi = {
  /** Uygulamanin temel guvenlik durusunu getirir. */
  securityPosture: async (): Promise<SecurityPosture> => {
    const { data } = await client.get<SecurityPosture>('/security/posture')
    return data
  },

  /** Son audit olaylarini getirir. */
  auditEvents: async (limit = 50): Promise<AuditEvent[]> => {
    const { data } = await client.get<AuditEvent[]>('/audit/events', { params: { limit } })
    return data
  },
}
