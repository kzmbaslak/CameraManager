// Yeni alarmları polling ile çeker; insan/hareket tespiti popup bildirimine dönüştürür
import { useEffect, useRef } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { alarmsApi } from '../api/alarms'
import { useAuthStore } from '../stores/authStore'
import { useAlarmStore } from '../stores/alarmStore'
import { useSystemSettingsStore } from '../stores/systemSettingsStore'

interface WindowWithWebkitAudio extends Window {
  webkitAudioContext?: typeof AudioContext
}

const AudioContextClass = window.AudioContext || (window as WindowWithWebkitAudio).webkitAudioContext

function playHumanDetectionSound(durationSeconds: number, stopPrevious: () => void): () => void {
  if (!AudioContextClass) return () => undefined

  try {
    stopPrevious()
    const audioContext = new AudioContextClass()
    const oscillator = audioContext.createOscillator()
    const gain = audioContext.createGain()
    const now = audioContext.currentTime
    const duration = Math.min(Math.max(durationSeconds, 1), 15)

    oscillator.type = 'sine'
    oscillator.frequency.setValueAtTime(880, now)
    oscillator.frequency.setValueAtTime(660, now + 0.18)
    oscillator.frequency.setValueAtTime(880, now + 0.36)

    gain.gain.setValueAtTime(0.0001, now)
    gain.gain.exponentialRampToValueAtTime(0.12, now + 0.03)
    for (let t = 0.25; t < duration; t += 0.5) {
      gain.gain.setValueAtTime(0.12, now + t)
      gain.gain.exponentialRampToValueAtTime(0.0001, now + t + 0.2)
      gain.gain.exponentialRampToValueAtTime(0.12, now + t + 0.28)
    }
    gain.gain.exponentialRampToValueAtTime(0.0001, now + duration)

    oscillator.connect(gain)
    gain.connect(audioContext.destination)
    oscillator.start(now)
    oscillator.stop(now + duration)

    let stopped = false
    const stop = () => {
      if (stopped) return
      stopped = true
      try {
        oscillator.stop()
      } catch {
        // Oscillator zaten planlanan zamanda durmuş olabilir.
      }
      void audioContext.close()
    }
    oscillator.onended = stop
    return stop
  } catch {
    return () => undefined
  }
}

/**
 * Yeni alarmları 8 saniyede bir kontrol eder.
 * Yalnızca insan veya hareket tespiti alarmları canlı görüntülü popup olarak gösterilir.
 * Kamera çevrimdışı alarmları popup yerine alarm listesine düşer — kamera zaten erişilemiyor.
 */
export function useAlarmNotifications() {
  const token = useAuthStore((s) => s.token)
  const { addNotification, dismissedIds, soundMutedUntil, soundStopSignal } = useAlarmStore()
  const soundEnabled = useSystemSettingsStore((s) => s.humanDetectionSoundEnabled)
  const soundDuration = useSystemSettingsStore((s) => s.humanDetectionSoundDurationSeconds)
  const seenIds = useRef<Set<number>>(new Set(dismissedIds))
  const stopSoundRef = useRef<() => void>(() => undefined)
  const qc = useQueryClient()

  const { data: newAlarms = [] } = useQuery({
    queryKey: ['alarms', 'new', 'global'],
    queryFn: () => alarmsApi.listByStatus('new', 50),
    refetchInterval: 8_000,
    enabled: !!token,
  })

  useEffect(() => {
    newAlarms.forEach((alarm) => {
      if (seenIds.current.has(alarm.id)) return
      seenIds.current.add(alarm.id)

      // Kamera çevrimdışı alarmı için canlı görüntülü popup açma —
      // kamera erişilemez, boş önizleme kafa karıştırır; alarm listesinden takip edilebilir
      if (alarm.alarm_type === 'camera_offline') return

      addNotification(alarm)
      const soundMuted = soundMutedUntil !== null && soundMutedUntil > Date.now()
      if (alarm.alarm_type === 'human_detected' && soundEnabled && !soundMuted) {
        stopSoundRef.current = playHumanDetectionSound(soundDuration, stopSoundRef.current)
      }
    })
  }, [addNotification, newAlarms, soundDuration, soundEnabled, soundMutedUntil])

  useEffect(() => {
    stopSoundRef.current()
  }, [soundStopSignal])

  useEffect(() => () => stopSoundRef.current(), [])

  return { qc }
}
