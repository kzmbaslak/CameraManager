// Sistem saglik ve guvenlik durusu API cagrilari.
import client from './client'
import type { SecurityPosture } from '../types/api'

export const systemApi = {
  /** Uygulamanin temel guvenlik durusunu getirir. */
  securityPosture: async (): Promise<SecurityPosture> => {
    const { data } = await client.get<SecurityPosture>('/security/posture')
    return data
  },
}
