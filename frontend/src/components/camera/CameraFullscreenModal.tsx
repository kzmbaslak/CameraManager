// Fullscreen live camera modal with alarm actions.
import { useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { AlertCircle, CheckCircle, VolumeX, Wifi, WifiOff, X } from 'lucide-react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { camerasApi } from '../../api/cameras'
import { alarmsApi } from '../../api/alarms'
import { useCameraStream } from '../../hooks/useCameraStream'
import { useAlarmStore } from '../../stores/alarmStore'
import { Button } from '../ui/Button'

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

  const { data: cameras = [] } = useQuery({
    queryKey: ['cameras'],
    queryFn: camerasApi.list,
    enabled: expandedCameraId !== null,
  })

  const camera = cameras.find((c) => c.id === expandedCameraId) ?? null

  const { frame, alarmTriggered, alarmId, connected } = useCameraStream(
    expandedCameraId ?? 0,
    expandedCameraId !== null,
    'live',
  )
  const actionableAlarmId = expandedAlarmId ?? alarmId

  const acknowledge = useMutation({
    mutationFn: alarmsApi.acknowledge,
    onSuccess: (alarm) => {
      stopSound()
      dismiss(alarm.id)
      void qc.invalidateQueries({ queryKey: ['alarms'] })
      setExpandedCamera(null)
    },
  })

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
                {alarmTriggered && (
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
              <button
                type="button"
                aria-label="Tam ekran kamerayı kapat"
                onClick={() => setExpandedCamera(null)}
                className="rounded-lg p-1.5 text-text-secondary transition-colors hover:bg-border hover:text-text-primary"
              >
                <X size={18} />
              </button>
            </div>

            <div className="relative flex aspect-video items-center justify-center bg-bg-primary">
              {frame ? (
                <img src={frame} alt={camera?.name} className="h-full w-full object-contain" />
              ) : (
                <div className="flex flex-col items-center gap-3 text-text-secondary">
                  <WifiOff size={40} />
                  <span className="text-sm">Görüntü bekleniyor...</span>
                </div>
              )}

              {alarmTriggered && (
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
            </div>

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
                <span className="ml-auto text-text-secondary">Kısayol: Space susturur, A onaylar, Esc kapatır</span>
              </div>
            )}
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  )
}
