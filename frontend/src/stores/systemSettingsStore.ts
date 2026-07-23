// Genel sistem arayüz ayarlarını tarayıcıda kalıcı olarak tutan Zustand store'u.
import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type ThemeMode = 'dark' | 'light'

interface SystemSettingsState {
  themeMode: ThemeMode
  humanDetectionSoundEnabled: boolean
  humanDetectionSoundDurationSeconds: number
  setThemeMode: (mode: ThemeMode) => void
  setHumanDetectionSoundEnabled: (enabled: boolean) => void
  setHumanDetectionSoundDurationSeconds: (seconds: number) => void
}

const clampDuration = (seconds: number) => Math.min(Math.max(Math.round(seconds), 1), 15)

export const useSystemSettingsStore = create<SystemSettingsState>()(
  persist(
    (set) => ({
      themeMode: 'dark',
      humanDetectionSoundEnabled: true,
      humanDetectionSoundDurationSeconds: 3,
      setThemeMode: (mode) => set({ themeMode: mode }),
      setHumanDetectionSoundEnabled: (enabled) => set({ humanDetectionSoundEnabled: enabled }),
      setHumanDetectionSoundDurationSeconds: (seconds) =>
        set({ humanDetectionSoundDurationSeconds: clampDuration(seconds) }),
    }),
    {
      name: 'kamera-system-settings',
    }
  )
)
