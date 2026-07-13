// Kimlik doğrulama API çağrıları.
import client from './client'
import type { LoginResponse } from '../types/api'

export const authApi = {
  // JSON formatında giriş — FastAPI /auth/login
  login: async (username: string, password: string): Promise<LoginResponse> => {
    const { data } = await client.post<LoginResponse>('/auth/login', { username, password })
    return data
  },
}
