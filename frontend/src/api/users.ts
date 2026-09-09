// Kullanıcı CRUD API çağrıları — list, add, update, delete
import client from './client'
import type { User, UserCreate, UserPageResponse } from '../types/api'
import type { OpenApiSchemas } from '../types/openapi.generated'

/** Kullanıcı güncelleme için kısmi veri tipi */
export type UserUpdate = OpenApiSchemas['UserUpdate']

export const usersApi = {
  /** Sistemdeki tüm kullanıcıları listeler. */
  list: async (): Promise<User[]> => {
    const { data } = await client.get<User[]>('/users/')
    return data
  },

  listPaginated: async (params: {
    page: number
    page_size: number
    search?: string
    role?: string
    active?: 'all' | 'active' | 'inactive'
    sort?: string
  }): Promise<UserPageResponse> => {
    const { data } = await client.get<UserPageResponse>('/users/', {
      params: { paginated: true, ...params },
    })
    return data
  },

  /** Sisteme yeni kullanıcı ekler; şifre sunucuda bcrypt ile hashlenir. */
  add: async (payload: UserCreate): Promise<User> => {
    const { data } = await client.post<User>('/users/', payload)
    return data
  },

  /** Kullanıcının rolünü, aktiflik durumunu veya şifresini günceller. */
  update: async (id: number, payload: UserUpdate): Promise<User> => {
    const { data } = await client.patch<User>(`/users/${id}`, payload)
    return data
  },

  /** Kullanıcıyı sistemden siler. */
  delete: async (id: number): Promise<void> => {
    await client.delete(`/users/${id}`)
  },
}
