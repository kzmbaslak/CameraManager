// Kamera canlı akışını tam ekran modal içinde gösterir.
import { useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, Wifi, WifiOff, AlertCircle } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { camerasApi } from '../../api/cameras'
import { useCameraStream } from '../../hooks/useCameraStream'
import { useAlarmStore } from '../../stores/alarmStore'

export function CameraFullscreenModal() {
  const { expandedCameraId, setExpandedCamera } = useAlarmStore()

  const { data: cameras = [] } = useQuery({
    queryKey: ['cameras'],
    queryFn: camerasApi.list,
    enabled: expandedCameraId !== null,
  })

  const camera = cameras.find((c) => c.id === expandedCameraId) ?? null

  const { frame, alarmTriggered, connected } = useCameraStream(
    expandedCameraId ?? 0,
    expandedCameraId !== null,
    'live'
  )

  // ESC ile kapat
  useEffect(() => {
    const handler = (e: KeyboardEvent) => e.key === 'Escape' && setExpandedCamera(null)
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [setExpandedCamera])

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
            initial={{ opacity: 0, scale: 0.92 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.92 }}
            transition={{ duration: 0.2, ease: 'easeOut' }}
            className="relative w-full max-w-5xl bg-[var(--bg-card)] border border-[var(--border)] rounded-2xl overflow-hidden shadow-2xl"
          >
            {/* Başlık */}
            <div className="flex items-center justify-between px-5 py-3 border-b border-[var(--border)]">
              <div className="flex items-center gap-3">
                {alarmTriggered && (
                  <motion.div
                    animate={{ opacity: [1, 0.3, 1] }}
                    transition={{ repeat: Infinity, duration: 1 }}
                  >
                    <AlertCircle size={16} className="text-[var(--danger)]" />
                  </motion.div>
                )}
                <span className="font-semibold text-[var(--text-primary)]">
                  {camera?.name ?? `Kamera #${expandedCameraId}`}
                </span>
                {connected ? (
                  <span className="flex items-center gap-1 text-xs text-[var(--success)]">
                    <Wifi size={12} /> Canlı
                  </span>
                ) : (
                  <span className="flex items-center gap-1 text-xs text-[var(--text-secondary)]">
                    <WifiOff size={12} /> Bağlantı yok
                  </span>
                )}
              </div>
              <button
                onClick={() => setExpandedCamera(null)}
                className="p-1.5 rounded-lg hover:bg-[var(--border)] text-[var(--text-secondary)] transition-colors"
              >
                <X size={18} />
              </button>
            </div>

            {/* Video */}
            <div className="relative aspect-video bg-[var(--bg-primary)] flex items-center justify-center">
              {frame ? (
                <img src={frame} alt={camera?.name} className="w-full h-full object-contain" />
              ) : (
                <div className="flex flex-col items-center gap-3 text-[var(--text-secondary)]">
                  <WifiOff size={40} />
                  <span className="text-sm">Görüntü bekleniyor...</span>
                </div>
              )}

              {alarmTriggered && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="absolute top-3 left-1/2 -translate-x-1/2 bg-[var(--danger)] text-white text-sm font-semibold px-4 py-1.5 rounded-full shadow-lg"
                >
                  ⚠ İnsan Tespit Edildi
                </motion.div>
              )}
            </div>

            {/* Alt bilgi */}
            {camera && (
              <div className="px-5 py-3 flex gap-6 text-xs text-[var(--text-secondary)] border-t border-[var(--border)]">
                <span>Host: <strong className="text-[var(--text-primary)]">{camera.host}</strong></span>
                <span>Port: <strong className="text-[var(--text-primary)]">{camera.rtsp_port}</strong></span>
                <span>Durum: <strong className={
                  camera.status === 'active' ? 'text-[var(--success)]' :
                  camera.status === 'error' ? 'text-[var(--danger)]' : 'text-[var(--text-secondary)]'
                }>{camera.status === 'active' ? 'Aktif' : camera.status === 'error' ? 'Hata' : 'Pasif'}</strong></span>
                <span>AI: <strong className="text-[var(--text-primary)]">{camera.ai_detection_enabled ? 'Açık' : 'Kapalı'}</strong></span>
              </div>
            )}
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  )
}
