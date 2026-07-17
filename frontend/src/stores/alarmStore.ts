// Alarm notification and operator action state.
import { create } from 'zustand'
import type { Alarm } from '../types/api'

interface AlarmNotification {
  alarm: Alarm
  receivedAt: number
}

interface AlarmState {
  notifications: AlarmNotification[]
  dismissedIds: number[]
  expandedCameraId: number | null
  expandedAlarmId: number | null
  soundMutedUntil: number | null
  soundStopSignal: number
  addNotification: (alarm: Alarm) => void
  dismiss: (alarmId: number) => void
  dismissAll: () => void
  stopSound: () => void
  muteSoundFor: (milliseconds: number) => void
  setExpandedCamera: (cameraId: number | null, alarmId?: number | null) => void
}

export const useAlarmStore = create<AlarmState>((set) => ({
  notifications: [],
  dismissedIds: [],
  expandedCameraId: null,
  expandedAlarmId: null,
  soundMutedUntil: null,
  soundStopSignal: 0,

  addNotification: (alarm) =>
    set((s) => ({
      notifications: [
        { alarm, receivedAt: Date.now() },
        ...s.notifications.filter((n) => n.alarm.id !== alarm.id),
      ].slice(0, 5),
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

  stopSound: () =>
    set((s) => ({
      soundStopSignal: s.soundStopSignal + 1,
    })),

  muteSoundFor: (milliseconds) =>
    set((s) => ({
      soundMutedUntil: Date.now() + milliseconds,
      soundStopSignal: s.soundStopSignal + 1,
    })),

  setExpandedCamera: (cameraId, alarmId = null) =>
    set({ expandedCameraId: cameraId, expandedAlarmId: cameraId === null ? null : alarmId }),
}))
