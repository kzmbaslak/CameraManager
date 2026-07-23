// Sistem saglik ve guvenlik durusu API cagrilari.
import client from './client'
import type { AuditEvent, SecurityPermissions, SecurityPosture, SetupStatus } from '../types/api'

const filenameFromDisposition = (disposition: string | undefined, fallback: string) => {
  if (!disposition) return fallback
  const match = disposition.match(/filename="?([^"]+)"?/i)
  return match?.[1] ?? fallback
}

export const systemApi = {
  /** Uygulamanin temel guvenlik durusunu getirir. */
  securityPosture: async (): Promise<SecurityPosture> => {
    const { data } = await client.get<SecurityPosture>('/security/posture')
    return data
  },

  /** Mevcut kullanicinin backend politika izinlerini getirir. */
  securityPermissions: async (): Promise<SecurityPermissions> => {
    const { data } = await client.get<SecurityPermissions>('/security/permissions')
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

  /** Admin tarafindan hassas sistem yedegini zip olarak indirir. */
  createSystemBackup: async (): Promise<{ blob: Blob; filename: string }> => {
    const response = await client.post<Blob>('/backup/system', undefined, { responseType: 'blob' })
    return {
      blob: response.data,
      filename: filenameFromDisposition(response.headers['content-disposition'], 'kamera-backup.zip'),
    }
  },
}
