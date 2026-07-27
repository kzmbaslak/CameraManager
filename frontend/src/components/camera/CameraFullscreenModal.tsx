// Fullscreen live camera modal with alarm actions.
import { useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { AlertCircle, ArrowDown, ArrowLeft, ArrowRight, ArrowUp, CheckCircle, Minus, Plus, Square, VolumeX, Wifi, WifiOff, X } from 'lucide-react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { camerasApi } from '../../api/cameras'
import { alarmsApi } from '../../api/alarms'
import { useCameraStream } from '../../hooks/useCameraStream'
import { usePermissions } from '../../hooks/usePermissions'
import { useAlarmStore } from '../../stores/alarmStore'
import { useToastStore } from '../../stores/toastStore'
import { getApiErrorMessage } from '../../utils/apiError'
import { Button } from '../ui/Button'
import { BoundingBoxOverlay } from './BoundingBoxOverlay'
import { CameraCard } from './CameraCard'
import type { CameraPtzDirection } from '../../types/api'

type FullscreenLayout = 1 | 4 | 9
type PtzSpeedProfile = 'slow' | 'normal' | 'fast'

const fullscreenLayoutClass: Record<FullscreenLayout, string> = {
  1: 'grid-cols-1',
  4: 'grid-cols-2',
  9: 'grid-cols-3',
}

const ptzSpeedProfiles: Record<PtzSpeedProfile, { label: string; speed: number; durationMs: number }> = {
  slow: { label: 'Yavas', speed: 0.25, durationMs: 250 },
  normal: { label: 'Normal', speed: 0.45, durationMs: 350 },
  fast: { label: 'Hizli', speed: 0.75, durationMs: 500 },
}

function isRecentDetection(detectedAt: string | null, ttlMs = 5_000) {
  if (!detectedAt) return false
  const timestamp = Date.parse(detectedAt)
  return Number.isFinite(timestamp) && Date.now() - timestamp <= ttlMs
}

function Kbd({ children }: { children: string }) {
  return (
    <kbd className="rounded border border-border bg-bg-secondary px-1.5 py-0.5 font-mono text-[10px] font-semibold text-text-primary">
      {children}
    </kbd>
  )
}

export function CameraFullscreenModal() {
  const {
    expandedCameraId,
    expandedAlarmId,
    setExpandedCamera,
    dismiss,
    stopSound,
    muteSoundFor,
  } = useAlarmStore()
  const qc = useQueryClient()
  const { canControlPtz } = usePermissions()
  const showToast = useToastStore((state) => state.showToast)
  const videoRef = useRef<HTMLDivElement>(null)
  const [dims, setDims] = useState({ w: 960, h: 540 })
  const [layout, setLayout] = useState<FullscreenLayout>(1)
  const [selectedPresetToken, setSelectedPresetToken] = useState('')
  const [ptzSpeedProfile, setPtzSpeedProfile] = useState<PtzSpeedProfile>('normal')

  const { data: cameras = [] } = useQuery({
    queryKey: ['cameras'],
    queryFn: camerasApi.list,
    enabled: expandedCameraId !== null,
  })

  const camera = cameras.find((c) => c.id === expandedCameraId) ?? null
  const ptzSupported = camera?.onvif_ptz_supported === true
  const { data: ptzPresetData } = useQuery({
    queryKey: ['camera-ptz-presets', expandedCameraId],
    queryFn: () => camerasApi.ptzPresets(expandedCameraId as number),
    enabled: expandedCameraId !== null && canControlPtz && ptzSupported && layout === 1,
    staleTime: 60_000,
  })
  const ptzPresets = ptzPresetData?.presets ?? []
  const activePresetToken = ptzPresets.some((preset) => preset.token === selectedPresetToken)
    ? selectedPresetToken
    : ''
  const watchedCameras = cameras
    .filter((item) => item.id === expandedCameraId || item.status !== 'inactive')
    .sort((left, right) => {
      if (left.id === expandedCameraId) return -1
      if (right.id === expandedCameraId) return 1
      return left.id - right.id
    })
    .slice(0, layout)

  const { frame, alarmTriggered, alarmId, connected, detections, frameWidth, frameHeight, detectedAt } = useCameraStream(
    expandedCameraId ?? 0,
    expandedCameraId !== null,
    'live',
  )
  const actionableAlarmId = expandedAlarmId ?? alarmId
  const hasFreshDetection = isRecentDetection(detectedAt)
  const activeDetections = hasFreshDetection ? detections : []
  const isAlarmActive = alarmTriggered || hasFreshDetection

  const acknowledge = useMutation({
    mutationFn: alarmsApi.acknowledge,
    onSuccess: (alarm) => {
      stopSound()
      dismiss(alarm.id)
      void qc.invalidateQueries({ queryKey: ['alarms'] })
      setExpandedCamera(null)
    },
  })

  const ptzMove = useMutation({
    mutationFn: (direction: CameraPtzDirection) => {
      const profile = ptzSpeedProfiles[ptzSpeedProfile]
      return camerasApi.ptzMove(expandedCameraId as number, {
        direction,
        speed: profile.speed,
        duration_ms: profile.durationMs,
      })
    },
    onError: (err) => showToast({
      variant: 'danger',
      title: 'PTZ komutu gonderilemedi',
      description: getApiErrorMessage(err, 'ONVIF PTZ baglantisini ve kamera yetkisini kontrol edin.'),
    }),
  })

  const ptzGotoPreset = useMutation({
    mutationFn: (presetToken: string) => camerasApi.ptzGotoPreset(expandedCameraId as number, presetToken),
    onSuccess: () => showToast({
      variant: 'success',
      title: 'PTZ preset gonderildi',
      description: 'Kamera secili preset pozisyonuna yonlendirildi.',
    }),
    onError: (err) => showToast({
      variant: 'danger',
      title: 'PTZ preset gonderilemedi',
      description: getApiErrorMessage(err, 'ONVIF preset listesini ve kamera yetkisini kontrol edin.'),
    }),
  })

  const sendPtz = (direction: CameraPtzDirection) => {
    if (!expandedCameraId || ptzMove.isPending) return
    ptzMove.mutate(direction)
  }

  const gotoPreset = () => {
    if (!activePresetToken || !expandedCameraId || ptzGotoPreset.isPending) return
    ptzGotoPreset.mutate(activePresetToken)
  }

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null
      if (target?.closest('input, textarea, select, [contenteditable="true"]')) return
      if (e.key === 'Escape') setExpandedCamera(null)
      if ((e.key === 'a' || e.key === 'A') && actionableAlarmId) acknowledge.mutate(actionableAlarmId)
      if (e.code === 'Space') {
        e.preventDefault()
        stopSound()
      }
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [acknowledge, actionableAlarmId, setExpandedCamera, stopSound])

  useEffect(() => {
    if (!videoRef.current) return
    const observer = new ResizeObserver((entries) => {
      const { width, height } = entries[0].contentRect
      setDims({ w: Math.round(width), h: Math.round(height) })
    })
    observer.observe(videoRef.current)
    return () => observer.disconnect()
  }, [expandedCameraId])

  return (
    <AnimatePresence>
      {expandedCameraId !== null && (
        <div className="fixed inset-0 z-[200] flex items-center justify-center p-4">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 bg-black/85"
            onClick={() => setExpandedCamera(null)}
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.94 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.94 }}
            transition={{ duration: 0.2, ease: 'easeOut' }}
            className="relative w-full max-w-5xl overflow-hidden rounded-lg border border-border bg-bg-card shadow-2xl"
          >
            <div className="flex items-center justify-between border-b border-border px-5 py-3">
              <div className="flex min-w-0 items-center gap-3">
                {isAlarmActive && (
                  <motion.div animate={{ opacity: [1, 0.35, 1] }} transition={{ repeat: Infinity, duration: 1 }}>
                    <AlertCircle size={16} className="text-danger" />
                  </motion.div>
                )}
                <span className="truncate font-semibold text-text-primary">
                  {camera?.name ?? `Kamera #${expandedCameraId}`}
                </span>
                {connected ? (
                  <span className="flex items-center gap-1 text-xs text-success">
                    <Wifi size={12} /> Canlı
                  </span>
                ) : (
                  <span className="flex items-center gap-1 text-xs text-text-secondary">
                    <WifiOff size={12} /> Bağlantı yok
                  </span>
                )}
              </div>
              <div className="flex shrink-0 items-center gap-1 rounded-md border border-border bg-bg-secondary p-1">
                {([1, 4, 9] as FullscreenLayout[]).map((value) => (
                  <button
                    key={value}
                    type="button"
                    title={`${value} kamera tam ekran layout`}
                    aria-label={`${value} kamera tam ekran layout`}
                    onClick={() => setLayout(value)}
                    className={`h-7 min-w-8 rounded px-2 text-xs font-semibold transition-colors ${
                      layout === value ? 'bg-accent text-white' : 'text-text-secondary hover:bg-bg-card hover:text-text-primary'
                    }`}
                  >
                    {value === 1 ? '1' : value === 4 ? '2x2' : '3x3'}
                  </button>
                ))}
              </div>
              <button
                type="button"
                aria-label="Tam ekran kamerayı kapat"
                onClick={() => setExpandedCamera(null)}
                className="rounded-lg p-1.5 text-text-secondary transition-colors hover:bg-border hover:text-text-primary"
              >
                <X size={18} />
              </button>
            </div>

            {layout === 1 ? (
            <div ref={videoRef} className="relative flex aspect-video items-center justify-center bg-bg-primary">
              {frame ? (
                <img src={frame} alt={camera?.name} className="h-full w-full object-contain" />
              ) : (
                <div className="flex flex-col items-center gap-3 text-text-secondary">
                  <WifiOff size={40} />
                  <span className="text-sm">Görüntü bekleniyor...</span>
                </div>
              )}
              <BoundingBoxOverlay
                detections={activeDetections}
                containerWidth={dims.w}
                containerHeight={dims.h}
                sourceWidth={frameWidth}
                sourceHeight={frameHeight}
                fit="contain"
              />

              {isAlarmActive && (
                <motion.div
                  initial={{ opacity: 0, y: -8 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="absolute left-4 right-4 top-4 flex items-center justify-between gap-3 rounded-lg bg-danger/95 px-4 py-3 text-white shadow-lg"
                >
                  <span className="text-sm font-semibold">İnsan Tespit Edildi</span>
                  <div className="flex flex-wrap items-center justify-end gap-2">
                    <Button
                      size="sm"
                      variant="secondary"
                      icon={<VolumeX size={13} />}
                      onClick={() => muteSoundFor(5 * 60 * 1000)}
                      className="border-white/30 bg-white/15 text-white hover:bg-white/25"
                    >
                      5 dk Sessiz
                    </Button>
                    {actionableAlarmId && (
                      <Button
                        size="sm"
                        variant="secondary"
                        icon={<CheckCircle size={13} />}
                        loading={acknowledge.isPending}
                        onClick={() => acknowledge.mutate(actionableAlarmId)}
                        className="border-white/30 bg-white text-danger hover:bg-white/90"
                      >
                        Sustur ve Onayla
                      </Button>
                    )}
                  </div>
                </motion.div>
              )}
              {camera && canControlPtz && ptzSupported && (
                <div className="absolute bottom-4 right-4 flex w-44 flex-col gap-2 rounded-md border border-white/15 bg-black/60 p-2 shadow-lg backdrop-blur">
                  <div className="grid grid-cols-3 gap-1" aria-label="PTZ hiz profili">
                    {(Object.entries(ptzSpeedProfiles) as [PtzSpeedProfile, (typeof ptzSpeedProfiles)[PtzSpeedProfile]][]).map(([key, profile]) => (
                      <button
                        key={key}
                        type="button"
                        aria-label={`PTZ hiz profili ${profile.label}`}
                        title={`PTZ hiz profili ${profile.label}`}
                        onClick={() => setPtzSpeedProfile(key)}
                        className={`rounded-md px-1.5 py-1 text-[11px] font-semibold transition-colors ${
                          ptzSpeedProfile === key ? 'bg-white text-black' : 'text-white hover:bg-white/20'
                        }`}
                      >
                        {profile.label}
                      </button>
                    ))}
                  </div>
                  <div className="grid grid-cols-3 gap-1">
                    <span />
                    <button type="button" aria-label="PTZ yukari" title="PTZ yukari" disabled={ptzMove.isPending} onClick={() => sendPtz('up')} className="flex h-9 w-9 items-center justify-center rounded-md text-white transition-colors hover:bg-white/20 disabled:opacity-50">
                      <ArrowUp size={17} />
                    </button>
                    <button type="button" aria-label="PTZ yakinlastir" title="PTZ yakinlastir" disabled={ptzMove.isPending} onClick={() => sendPtz('zoom_in')} className="flex h-9 w-9 items-center justify-center rounded-md text-white transition-colors hover:bg-white/20 disabled:opacity-50">
                      <Plus size={17} />
                    </button>
                    <button type="button" aria-label="PTZ sola" title="PTZ sola" disabled={ptzMove.isPending} onClick={() => sendPtz('left')} className="flex h-9 w-9 items-center justify-center rounded-md text-white transition-colors hover:bg-white/20 disabled:opacity-50">
                      <ArrowLeft size={17} />
                    </button>
                    <button type="button" aria-label="PTZ durdur" title="PTZ durdur" disabled={ptzMove.isPending} onClick={() => sendPtz('stop')} className="flex h-9 w-9 items-center justify-center rounded-md text-white transition-colors hover:bg-white/20 disabled:opacity-50">
                      <Square size={15} />
                    </button>
                    <button type="button" aria-label="PTZ saga" title="PTZ saga" disabled={ptzMove.isPending} onClick={() => sendPtz('right')} className="flex h-9 w-9 items-center justify-center rounded-md text-white transition-colors hover:bg-white/20 disabled:opacity-50">
                      <ArrowRight size={17} />
                    </button>
                    <span />
                    <button type="button" aria-label="PTZ asagi" title="PTZ asagi" disabled={ptzMove.isPending} onClick={() => sendPtz('down')} className="flex h-9 w-9 items-center justify-center rounded-md text-white transition-colors hover:bg-white/20 disabled:opacity-50">
                      <ArrowDown size={17} />
                    </button>
                    <button type="button" aria-label="PTZ uzaklastir" title="PTZ uzaklastir" disabled={ptzMove.isPending} onClick={() => sendPtz('zoom_out')} className="flex h-9 w-9 items-center justify-center rounded-md text-white transition-colors hover:bg-white/20 disabled:opacity-50">
                      <Minus size={17} />
                    </button>
                  </div>
                  {ptzPresets.length > 0 && (
                    <div className="flex gap-1">
                      <select
                        aria-label="PTZ preset sec"
                        value={activePresetToken}
                        onChange={(event) => setSelectedPresetToken(event.target.value)}
                        className="min-w-0 flex-1 rounded-md border border-white/15 bg-black/50 px-2 py-1 text-xs text-white outline-none focus:border-white/60"
                      >
                        <option value="">Preset</option>
                        {ptzPresets.map((preset) => (
                          <option key={preset.token} value={preset.token}>
                            {preset.name || preset.token}
                          </option>
                        ))}
                      </select>
                      <button
                        type="button"
                        aria-label="PTZ preset pozisyonuna git"
                        title="PTZ preset pozisyonuna git"
                        disabled={!activePresetToken || ptzGotoPreset.isPending}
                        onClick={gotoPreset}
                        className="rounded-md px-2 text-xs font-semibold text-white transition-colors hover:bg-white/20 disabled:opacity-50"
                      >
                        Git
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
            ) : (
              <div className={`grid ${fullscreenLayoutClass[layout]} gap-2 bg-bg-primary p-2`}>
                {watchedCameras.map((item) => (
                  <CameraCard
                    key={item.id}
                    camera={item}
                    streamProfile={item.id === expandedCameraId ? 'live' : 'grid'}
                  />
                ))}
              </div>
            )}

            {camera && (
              <div className="flex flex-wrap gap-x-6 gap-y-1 border-t border-border px-5 py-3 text-xs text-text-secondary">
                <span>Host: <strong className="text-text-primary">{camera.host}</strong></span>
                <span>Port: <strong className="text-text-primary">{camera.rtsp_port}</strong></span>
                <span>
                  Durum:{' '}
                  <strong className={
                    camera.status === 'active' ? 'text-success' :
                    camera.status === 'error' ? 'text-danger' : 'text-text-secondary'
                  }>
                    {camera.status === 'active' ? 'Aktif' : camera.status === 'error' ? 'Hata' : 'Pasif'}
                  </strong>
                </span>
                <span>AI: <strong className="text-text-primary">{camera.ai_detection_enabled ? 'Açık' : 'Kapalı'}</strong></span>
                <span>
                  PTZ:{' '}
                  <strong className={camera.onvif_ptz_supported ? 'text-success' : 'text-text-secondary'}>
                    {camera.onvif_ptz_supported === true ? 'Destekli' : camera.onvif_ptz_supported === false ? 'Destek yok' : 'ONVIF test bekliyor'}
                  </strong>
                </span>
                <span className="ml-auto flex items-center gap-1.5 text-text-secondary">
                  <Kbd>Space</Kbd><span>Sustur</span>
                  <Kbd>A</Kbd><span>Onayla</span>
                  <Kbd>Esc</Kbd><span>Kapat</span>
                </span>
              </div>
            )}
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  )
}
