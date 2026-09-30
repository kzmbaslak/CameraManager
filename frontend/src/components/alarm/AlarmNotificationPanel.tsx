// Persistent alarm action panel shown above every page.
import { AnimatePresence, motion } from 'framer-motion'
import { useEffect, useRef, useState } from 'react'
import { AlertTriangle, BellOff, CheckCircle, Clock3, Eye, VolumeX, XCircle } from 'lucide-react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import dayjs from 'dayjs'
import 'dayjs/locale/tr'
import { alarmsApi } from '../../api/alarms'
import { useAlarmStore } from '../../stores/alarmStore'
import { useCameraStream } from '../../hooks/useCameraStream'
import { useAlarmNotifications } from '../../hooks/useAlarmNotifications'
import { usePermissions } from '../../hooks/usePermissions'
import { useSystemSettingsStore } from '../../stores/systemSettingsStore'
import { BoundingBoxOverlay } from '../camera/BoundingBoxOverlay'
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

function ShortcutLegend({ canOperateAlarms }: { canOperateAlarms: boolean }) {
  return (
    <div className="flex items-center gap-1.5 whitespace-nowrap text-[11px] text-text-secondary">
      <Kbd>Space</Kbd><span>Sustur</span>
      <Kbd>S</Kbd><span>30 sn</span>
      <Kbd>M</Kbd><span>5 dk</span>
      {canOperateAlarms && (
        <>
          <Kbd>A</Kbd><span>Onayla</span>
        </>
      )}
      <Kbd>Enter</Kbd><span>Canlı</span>
    </div>
  )
}

function AlarmProcedureChecklist() {
  return (
    <div className="border-t border-border px-3 py-2">
      <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-text-secondary">
        Mudahale Sirasi
      </p>
      <ol className="grid gap-1 text-[11px] text-text-secondary">
        <li className="flex items-center gap-2">
          <span className="flex h-4 w-4 shrink-0 items-center justify-center rounded bg-info/15 text-[10px] font-bold text-info">1</span>
          <span>Canli goruntuyu ac, insan konumunu kutudan dogrula.</span>
        </li>
        <li className="flex items-center gap-2">
          <span className="flex h-4 w-4 shrink-0 items-center justify-center rounded bg-warning/15 text-[10px] font-bold text-warning">2</span>
          <span>Yakindaki kameralarla yon ve devam eden hareketi kontrol et.</span>
        </li>
        <li className="flex items-center gap-2">
          <span className="flex h-4 w-4 shrink-0 items-center justify-center rounded bg-success/15 text-[10px] font-bold text-success">3</span>
          <span>Alarmi onayla veya yanlis alarm olarak kapat; gerekirse not ekle.</span>
        </li>
      </ol>
    </div>
  )
}

const typeLabel: Record<string, string> = {
  human_detected: 'İnsan Tespiti',
  motion_detected: 'Hareket',
  person_density_anomaly: 'Yogunluk Anomalisi',
  camera_health_degraded: 'Kamera Saglik Uyarisi',
  camera_offline: 'Kamera Çevrimdışı',
}

function NotificationCard({
  alarm,
  receivedAt,
  onAcknowledge,
  onFalseAlarm,
  busy,
  canOperateAlarms,
}: {
  alarm: Alarm
  receivedAt: number
  onAcknowledge: (alarm: Alarm) => void
  onFalseAlarm: (alarm: Alarm) => void
  busy: boolean
  canOperateAlarms: boolean
}) {
  const previewRef = useRef<HTMLButtonElement>(null)
  const [previewDims, setPreviewDims] = useState({ w: 360, h: 203 })
  const { dismiss, setExpandedCamera } = useAlarmStore()
  const showHumanDetectionBoxes = useSystemSettingsStore((s) => s.humanDetectionBoxesVisible)
  const streamEnabled = alarm.alarm_type !== 'camera_offline' && alarm.alarm_type !== 'camera_health_degraded'
  const { frame, connected, detections, frameWidth, frameHeight } = useCameraStream(alarm.camera_id, streamEnabled, 'alarm')

  useEffect(() => {
    if (!previewRef.current) return
    const observer = new ResizeObserver((entries) => {
      const { width, height } = entries[0].contentRect
      setPreviewDims({ w: Math.round(width), h: Math.round(height) })
    })
    observer.observe(previewRef.current)
    return () => observer.disconnect()
  }, [])

  return (
    <motion.div
      layout
      initial={{ opacity: 0, x: 80, scale: 0.98 }}
      animate={{ opacity: 1, x: 0, scale: 1 }}
      exit={{ opacity: 0, x: 80, scale: 0.98 }}
      transition={{ duration: 0.2, ease: 'easeOut' }}
      className="w-[360px] overflow-hidden rounded-md border border-danger/50 bg-bg-card shadow-2xl"
      role="alert"
      aria-live="assertive"
    >
      <div className="flex items-start justify-between gap-3 border-b border-danger/25 bg-danger/15 px-3 py-2.5">
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
        ref={previewRef}
        type="button"
        onClick={() => setExpandedCamera(alarm.camera_id, alarm.id)}
        className="relative flex aspect-video w-full items-center justify-center overflow-hidden bg-bg-primary"
      >
        {frame ? (
          <img src={frame} alt="Alarm kamera önizlemesi" className="h-full w-full object-cover" />
        ) : (
          <div className="text-xs text-text-secondary">{connected ? 'Bağlanıyor...' : 'Bağlantı yok'}</div>
        )}
        {showHumanDetectionBoxes && (
          <BoundingBoxOverlay
            detections={detections}
            box={!detections.length ? alarm.bounding_box : null}
            containerWidth={previewDims.w}
            containerHeight={previewDims.h}
            sourceWidth={frameWidth}
            sourceHeight={frameHeight}
            fit="cover"
            stale={!detections.length && Boolean(alarm.bounding_box)}
          />
        )}
        <div className="absolute inset-x-0 bottom-0 flex items-center justify-between bg-black/65 px-3 py-2 text-xs text-white">
          <span>Canlı görüntüyü aç</span>
          <Eye size={14} />
        </div>
      </button>

      <AlarmProcedureChecklist />

      <div className="grid grid-cols-2 gap-2 p-3">
        {canOperateAlarms ? (
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
        ) : (
          <div className="col-span-2 rounded-md border border-border bg-bg-secondary px-3 py-2 text-xs text-text-secondary">
            Bu rol alarm onaylama islemi yapamaz.
          </div>
        )}
        <Button
          size="sm"
          variant="secondary"
          icon={<Eye size={14} />}
          onClick={() => setExpandedCamera(alarm.camera_id, alarm.id)}
          className={canOperateAlarms ? undefined : 'col-span-2'}
        >
          Canlı Aç
        </Button>
        {canOperateAlarms && (
        <Button
          size="sm"
          variant="ghost"
          icon={<XCircle size={14} />}
          loading={busy}
          onClick={() => onFalseAlarm(alarm)}
        >
          Yanlış Alarm
        </Button>
        )}
      </div>
    </motion.div>
  )
}

export function AlarmNotificationPanel() {
  useAlarmNotifications()

  const qc = useQueryClient()
  const { canOperateAlarms } = usePermissions()
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

  const falseAlarm = useMutation({
    mutationFn: alarmsApi.markFalsePositive,
    onSuccess: (alarm) => {
      stopSound()
      dismiss(alarm.id)
      void qc.invalidateQueries({ queryKey: ['alarms'] })
    },
  })

  const handleAcknowledge = (alarm: Alarm) => acknowledge.mutate(alarm.id)
  const handleFalseAlarm = (alarm: Alarm) => falseAlarm.mutate(alarm.id)
  const handleShortMute = () => muteSoundFor(30 * 1000)
  const handleLongMute = () => muteSoundFor(5 * 60 * 1000)

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
      if (e.key === 's' || e.key === 'S') muteSoundFor(30 * 1000)
      if (e.key === 'm' || e.key === 'M') muteSoundFor(5 * 60 * 1000)
      if ((e.key === 'a' || e.key === 'A') && canOperateAlarms) acknowledge.mutate(firstAlarm.id)
      if (e.key === 'Enter') setExpandedCamera(firstAlarm.camera_id, firstAlarm.id)
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [acknowledge, canOperateAlarms, muteSoundFor, notifications, setExpandedCamera, stopSound])

  return (
    <div className="fixed right-4 top-4 z-[100] flex max-h-[calc(100vh-2rem)] flex-col items-end gap-2">
      <AnimatePresence>
        {notifications.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="flex items-center gap-2 rounded-md border border-border bg-bg-secondary px-3 py-2 shadow-2xl"
          >
            <Button
              size="sm"
              variant="secondary"
              icon={<Clock3 size={13} />}
              onClick={handleShortMute}
              title="Yeni alarm seslerini 30 saniye boyunca susturur; alarm kartlari gorunur kalir."
            >
              30 sn Sessiz
            </Button>
            <Button
              size="sm"
              variant="secondary"
              icon={<VolumeX size={13} />}
              onClick={handleLongMute}
              title="Yeni alarm seslerini 5 dakika boyunca susturur; alarm kartlari gorunur kalir."
            >
              5 dk Sessiz
            </Button>
            {canOperateAlarms && notifications.length > 1 && (
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
              <ShortcutLegend canOperateAlarms={canOperateAlarms} />
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
              busy={
                (acknowledge.isPending && acknowledge.variables === alarm.id) ||
                (falseAlarm.isPending && falseAlarm.variables === alarm.id)
              }
              onAcknowledge={handleAcknowledge}
              onFalseAlarm={handleFalseAlarm}
              canOperateAlarms={canOperateAlarms}
            />
          ))}
        </AnimatePresence>
      </div>
    </div>
  )
}
