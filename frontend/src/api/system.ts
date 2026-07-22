// Sistem saglik ve guvenlik durusu API cagrilari.
import client from './client'
import type { AuditEvent, SecurityPosture, SetupStatus } from '../types/api'

export const systemApi = {
  /** Uygulamanin temel guvenlik durusunu getirir. */
  securityPosture: async (): Promise<SecurityPosture> => {
    const { data } = await client.get<SecurityPosture>('/security/posture')
    return data
  },

  /** Kurulum dosyasi, model, DB semasi ve admin hazirligini getirir. */
  setupStatus: async (): Promise<SetupStatus> => {
    const { data } = await client.get<SetupStatus>('/setup/status')
    return data
  },

  /** Son audit olaylarini getirir. */
  auditEvents: async (limit = 50): Promise<AuditEvent[]> => {
    const { data } = await client.get<AuditEvent[]>('/audit/events', { params: { limit } })
    return data
  },
}
