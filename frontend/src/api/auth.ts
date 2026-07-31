// Kimlik doğrulama API çağrıları.
import client from './client'
import type { LoginResponse, OpenApiSchemas } from '../types/api'

export type LoginPayload = OpenApiSchemas['LoginRequest']
export type ChangePasswordPayload = OpenApiSchemas['ChangePasswordRequest']
export type ChangePasswordResponse = { message: string }

export const authApi = {
  // JSON formatında giriş — FastAPI /auth/login
  login: async (username: string, password: string): Promise<LoginResponse> => {
    const payload: LoginPayload = { username, password }
    const { data } = await client.post<LoginResponse>('/auth/login', payload)
    return data
  },
  changePassword: async (payload: ChangePasswordPayload): Promise<ChangePasswordResponse> => {
    const { data } = await client.post<ChangePasswordResponse>('/auth/change-password', payload)
    return data
  },
  logout: async (): Promise<void> => {
    await client.post('/auth/logout')
  },
}
