// Persistent alarm action panel shown above every page.
import { AnimatePresence, motion } from 'framer-motion'
import { useEffect } from 'react'
import { AlertTriangle, BellOff, CheckCircle, Eye, VolumeX, XCircle } from 'lucide-react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import dayjs from 'dayjs'
import 'dayjs/locale/tr'
import { alarmsApi } from '../../api/alarms'
import { useAlarmStore } from '../../stores/alarmStore'
import { useCameraStream } from '../../hooks/useCameraStream'
import { useAlarmNotifications } from '../../hooks/useAlarmNotifications'
import { Button } from '../ui/Button'
import type { Alarm } from '../../types/api'

dayjs.locale('tr')

function Kbd({ children }: { children: string }) {
  return (
    <kbd className="rounded border border-border bg-bg-secondary px-1.5 py-0.5 font-mono text-[10px] font-semibold text-text-primary">
      {children}
    </kbd>
  )
}

function ShortcutLegend() {
  return (
    <div className="flex items-center gap-1.5 whitespace-nowrap text-[11px] text-text-secondary">
      <Kbd>Space</Kbd><span>Sustur</span>
      <Kbd>A</Kbd><span>Onayla</span>
      <Kbd>Enter</Kbd><span>Canlı</span>
    </div>
  )
}

const typeLabel: Record<string, string> = {
  human_detected: 'İnsan Tespiti',
  motion_detected: 'Hareket',
  camera_offline: 'Kamera Çevrimdışı',
}

function NotificationCard({
  alarm,
  receivedAt,
  onAcknowledge,
  onFalseAlarm,
  busy,
}: {
  alarm: Alarm
  receivedAt: number
  onAcknowledge: (alarm: Alarm) => void
  onFalseAlarm: (alarm: Alarm) => void
  busy: boolean
}) {
  const { dismiss, setExpandedCamera } = useAlarmStore()
  const streamEnabled = alarm.alarm_type !== 'camera_offline'
  const { frame, connected } = useCameraStream(alarm.camera_id, streamEnabled, 'alarm')

  return (
    <motion.div
      layout
      initial={{ opacity: 0, x: 80, scale: 0.98 }}
      animate={{ opacity: 1, x: 0, scale: 1 }}
      exit={{ opacity: 0, x: 80, scale: 0.98 }}
      transition={{ duration: 0.2, ease: 'easeOut' }}
      className="w-[360px] overflow-hidden rounded-lg border border-danger/50 bg-bg-card shadow-2xl"
      role="alert"
      aria-live="assertive"
    >
      <div className="flex items-start justify-between gap-3 border-b border-danger/20 bg-danger/10 px-3 py-2.5">
        <div className="flex min-w-0 items-start gap-2">
          <motion.div animate={{ opacity: [1, 0.35, 1] }} transition={{ repeat: Infinity, duration: 1 }}>
            <AlertTriangle size={16} className="mt-0.5 text-danger" />
          </motion.div>
          <div className="min-w-0">
            <p className="text-sm font-semibold text-danger">{typeLabel[alarm.alarm_type] ?? alarm.alarm_type}</p>
            <p className="text-xs text-text-secondary">
              Kamera #{alarm.camera_id} · {dayjs(receivedAt).format('HH:mm:ss')}
            </p>
          </div>
        </div>
        <button
          type="button"
          aria-label="Bildirimi gizle"
          title="Sadece bildirimi gizle"
          onClick={() => dismiss(alarm.id)}
          className="rounded p-1 text-text-secondary transition-colors hover:bg-border hover:text-text-primary"
        >
          <XCircle size={16} />
        </button>
      </div>

      <button
        type="button"
        onClick={() => setExpandedCamera(alarm.camera_id, alarm.id)}
        className="relative flex aspect-video w-full items-center justify-center overflow-hidden bg-bg-primary"
      >
        {frame ? (
          <img src={frame} alt="Alarm kamera önizlemesi" className="h-full w-full object-cover" />
        ) : (
          <div className="text-xs text-text-secondary">{connected ? 'Bağlanıyor...' : 'Bağlantı yok'}</div>
        )}
        <div className="absolute inset-x-0 bottom-0 flex items-center justify-between bg-black/65 px-3 py-2 text-xs text-white">
          <span>Canlı görüntüyü aç</span>
          <Eye size={14} />
        </div>
      </button>

      <div className="grid grid-cols-2 gap-2 p-3">
        <Button
          size="sm"
          variant="danger"
          icon={<CheckCircle size={14} />}
          loading={busy}
          onClick={() => onAcknowledge(alarm)}
          className="col-span-2"
        >
          Sustur ve Onayla
        </Button>
        <Button
          size="sm"
          variant="secondary"
          icon={<Eye size={14} />}
          onClick={() => setExpandedCamera(alarm.camera_id, alarm.id)}
        >
          Canlı Aç
        </Button>
        <Button
          size="sm"
          variant="ghost"
          icon={<XCircle size={14} />}
          loading={busy}
          onClick={() => onFalseAlarm(alarm)}
        >
          Yanlış Alarm
        </Button>
      </div>
    </motion.div>
  )
}

export function AlarmNotificationPanel() {
  useAlarmNotifications()

  const qc = useQueryClient()
  const { notifications, dismiss, dismissAll, stopSound, muteSoundFor, setExpandedCamera } = useAlarmStore()

  const acknowledge = useMutation({
    mutationFn: alarmsApi.acknowledge,
    onSuccess: (alarm) => {
      stopSound()
      dismiss(alarm.id)
      void qc.invalidateQueries({ queryKey: ['alarms'] })
    },
  })

  const acknowledgeAll = useMutation({
    mutationFn: async (alarms: Alarm[]) => Promise.all(alarms.map((alarm) => alarmsApi.acknowledge(alarm.id))),
    onSuccess: () => {
      stopSound()
      dismissAll()
      void qc.invalidateQueries({ queryKey: ['alarms'] })
    },
  })

  const handleAcknowledge = (alarm: Alarm) => acknowledge.mutate(alarm.id)
  const handleFalseAlarm = (alarm: Alarm) => acknowledge.mutate(alarm.id)
  const handleMute = () => muteSoundFor(5 * 60 * 1000)

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (notifications.length === 0) return
      const target = e.target as HTMLElement | null
      if (target?.closest('input, textarea, select, [contenteditable="true"]')) return
      const firstAlarm = notifications[0].alarm
      if (e.code === 'Space') {
        e.preventDefault()
        stopSound()
      }
      if (e.key === 'a' || e.key === 'A') acknowledge.mutate(firstAlarm.id)
      if (e.key === 'Enter') setExpandedCamera(firstAlarm.camera_id, firstAlarm.id)
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [acknowledge, notifications, setExpandedCamera, stopSound])

  return (
    <div className="fixed right-4 top-4 z-[100] flex max-h-[calc(100vh-2rem)] flex-col items-end gap-2">
      <AnimatePresence>
        {notifications.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="flex items-center gap-2 rounded-lg border border-border bg-bg-card px-3 py-2 shadow-xl"
          >
            <Button
              size="sm"
              variant="secondary"
              icon={<VolumeX size={13} />}
              onClick={handleMute}
            >
              5 dk Sessiz
            </Button>
            {notifications.length > 1 && (
              <Button
                size="sm"
                variant="danger"
                icon={<CheckCircle size={13} />}
                loading={acknowledgeAll.isPending}
                onClick={() => acknowledgeAll.mutate(notifications.map((n) => n.alarm))}
              >
                Tümünü Onayla ({notifications.length})
              </Button>
            )}
            <Button
              size="sm"
              variant="ghost"
              icon={<BellOff size={13} />}
              onClick={() => {
                stopSound()
                dismissAll()
              }}
            >
              Gizle
            </Button>
            <div className="ml-1 hidden border-l border-border pl-3 md:block">
              <ShortcutLegend />
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="flex flex-col items-end gap-2 overflow-y-auto pr-1">
        <AnimatePresence mode="popLayout">
          {notifications.map(({ alarm, receivedAt }) => (
            <NotificationCard
              key={alarm.id}
              alarm={alarm}
              receivedAt={receivedAt}
              busy={acknowledge.isPending && acknowledge.variables === alarm.id}
              onAcknowledge={handleAcknowledge}
              onFalseAlarm={handleFalseAlarm}
            />
          ))}
        </AnimatePresence>
      </div>
    </div>
  )
}
