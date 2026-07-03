// Yeni alarmları polling ile çeker; insan/hareket tespiti popup bildirimine dönüştürür
import { useEffect, useRef } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { alarmsApi } from '../api/alarms'
import { useAuthStore } from '../stores/authStore'
import { useAlarmStore } from '../stores/alarmStore'

/**
 * Yeni alarmları 8 saniyede bir kontrol eder.
 * Yalnızca insan veya hareket tespiti alarmları canlı görüntülü popup olarak gösterilir.
 * Kamera çevrimdışı alarmları popup yerine alarm listesine düşer — kamera zaten erişilemiyor.
 */
export function useAlarmNotifications() {
  const token = useAuthStore((s) => s.token)
  const { addNotification, dismissedIds } = useAlarmStore()
  const seenIds = useRef<Set<number>>(new Set(dismissedIds))
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
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [newAlarms])

  return { qc }
}
