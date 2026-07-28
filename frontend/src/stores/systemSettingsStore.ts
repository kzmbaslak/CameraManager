// Genel sistem arayüz ayarlarını tarayıcıda kalıcı olarak tutan Zustand store'u.
import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type ThemeMode = 'dark' | 'light'

interface SystemSettingsState {
  themeMode: ThemeMode
  devicePasswordRotationDays: number
  humanDetectionSoundEnabled: boolean
  humanDetectionSoundDurationSeconds: number
  humanDetectionBoxesVisible: boolean
  setThemeMode: (mode: ThemeMode) => void
  setDevicePasswordRotationDays: (days: number) => void
  setHumanDetectionSoundEnabled: (enabled: boolean) => void
  setHumanDetectionSoundDurationSeconds: (seconds: number) => void
  setHumanDetectionBoxesVisible: (visible: boolean) => void
}

const clampDuration = (seconds: number) => Math.min(Math.max(Math.round(seconds), 1), 15)
const clampRotationDays = (days: number) => Math.min(Math.max(Math.round(days), 30), 365)

export const useSystemSettingsStore = create<SystemSettingsState>()(
  persist(
    (set) => ({
      themeMode: 'dark',
      devicePasswordRotationDays: 90,
      humanDetectionSoundEnabled: true,
      humanDetectionSoundDurationSeconds: 3,
      humanDetectionBoxesVisible: true,
      setThemeMode: (mode) => set({ themeMode: mode }),
      setDevicePasswordRotationDays: (days) => set({ devicePasswordRotationDays: clampRotationDays(days) }),
      setHumanDetectionSoundEnabled: (enabled) => set({ humanDetectionSoundEnabled: enabled }),
      setHumanDetectionSoundDurationSeconds: (seconds) =>
        set({ humanDetectionSoundDurationSeconds: clampDuration(seconds) }),
      setHumanDetectionBoxesVisible: (visible) => set({ humanDetectionBoxesVisible: visible }),
    }),
    {
      name: 'kamera-system-settings',
    }
  )
)
