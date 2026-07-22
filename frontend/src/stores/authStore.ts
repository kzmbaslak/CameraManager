// JWT oturum bilgisini kalıcı olarak tutan Zustand store'u.
import { create } from 'zustand'
import { createJSONStorage, persist } from 'zustand/middleware'

interface AuthState {
  token: string | null
  username: string | null
  role: string | null
  expiresAt: number | null
  isExpired: () => boolean
  login: (token: string, username: string, role: string) => void
  logout: () => void
}

function getJwtExpiresAt(token: string): number | null {
  try {
    const payload = token.split('.')[1]
    if (!payload || typeof atob === 'undefined') return null

    const normalized = payload.replace(/-/g, '+').replace(/_/g, '/')
    const padded = normalized.padEnd(normalized.length + ((4 - (normalized.length % 4)) % 4), '=')
    const decoded = JSON.parse(atob(padded)) as { exp?: unknown }

    return typeof decoded.exp === 'number' ? decoded.exp * 1000 : null
  } catch {
    return null
  }
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      token: null,
      username: null,
      role: null,
      expiresAt: null,
      isExpired: () => {
        const expiresAt = get().expiresAt
        return Boolean(expiresAt && Date.now() >= expiresAt)
      },
      login: (token, username, role) => set({ token, username, role, expiresAt: getJwtExpiresAt(token) }),
      logout: () => set({ token: null, username: null, role: null, expiresAt: null }),
    }),
    { name: 'auth-session', storage: createJSONStorage(() => sessionStorage) }
  )
)
