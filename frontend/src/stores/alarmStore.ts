import { create } from 'zustand'
import type { Alarm } from '../types/api'

interface AlarmNotification {
  alarm: Alarm
  receivedAt: number  // Date.now()
}

interface AlarmState {
  notifications: AlarmNotification[]
  dismissedIds: number[]
  expandedCameraId: number | null          // büyük ekran için
  addNotification: (alarm: Alarm) => void
  dismiss: (alarmId: number) => void
  dismissAll: () => void
  setExpandedCamera: (cameraId: number | null) => void
}

export const useAlarmStore = create<AlarmState>((set) => ({
  notifications: [],
  dismissedIds: [],
  expandedCameraId: null,

  addNotification: (alarm) =>
    set((s) => ({
      notifications: [
        { alarm, receivedAt: Date.now() },
        ...s.notifications.filter((n) => n.alarm.id !== alarm.id),
      ].slice(0, 5), // en fazla 5 bildirim göster
    })),

  dismiss: (alarmId) =>
    set((s) => ({
      notifications: s.notifications.filter((n) => n.alarm.id !== alarmId),
      dismissedIds: [...s.dismissedIds, alarmId],
    })),

  dismissAll: () =>
    set((s) => ({
      dismissedIds: [...s.dismissedIds, ...s.notifications.map((n) => n.alarm.id)],
      notifications: [],
    })),

  setExpandedCamera: (cameraId) => set({ expandedCameraId: cameraId }),
}))
