import { useRef, useState, useEffect } from 'react'
import { Wifi, WifiOff, AlertCircle } from 'lucide-react'
import { motion } from 'framer-motion'
import { useCameraStream } from '../../hooks/useCameraStream'
import { BoundingBoxOverlay } from './BoundingBoxOverlay'
import { useAlarmStore } from '../../stores/alarmStore'
import type { Camera, Alarm } from '../../types/api'

interface CameraCardProps {
  camera: Camera
  latestAlarm?: Alarm | null
}

export function CameraCard({ camera, latestAlarm }: CameraCardProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [dims, setDims] = useState({ w: 320, h: 180 })
  const [isNearViewport, setIsNearViewport] = useState(false)
  const { setExpandedCamera } = useAlarmStore()

  // ACTIVE ve ERROR kameralar için WebSocket açılır — ERROR kamera toparlandığında
  // kare otomatik akar; INACTIVE kameralar için bağlantı kurulmaz.
  const { frame, alarmTriggered, connected } = useCameraStream(
    camera.id,
    camera.status !== 'inactive' && isNearViewport
  )

  // Büyük kamera listelerinde yalnızca görünür ve yakındaki kartlar yayın açar.
  useEffect(() => {
    if (!containerRef.current) return
    const observer = new IntersectionObserver(
      ([entry]) => setIsNearViewport(entry.isIntersecting),
      { rootMargin: '240px 0px' },
    )
    observer.observe(containerRef.current)
    return () => observer.disconnect()
  }, [])

  // Kamera div boyutu değişince canvas boyutunu güncelle
  useEffect(() => {
    if (!containerRef.current) return
    const observer = new ResizeObserver((entries) => {
      const { width, height } = entries[0].contentRect
      setDims({ w: Math.round(width), h: Math.round(height) })
    })
    observer.observe(containerRef.current)
    return () => observer.disconnect()
  }, [])

  const box = alarmTriggered && latestAlarm?.bounding_box ? latestAlarm.bounding_box : null

  return (
    <div className="bg-[var(--bg-card)] border border-[var(--border)] rounded-xl overflow-hidden flex flex-col">
      {/* Başlık */}
      <div className="flex items-center justify-between px-3 py-2.5 border-b border-[var(--border)]">
        <span className="text-sm font-medium text-[var(--text-primary)] truncate">{camera.name}</span>
        <div className="flex items-center gap-1.5 shrink-0">
          {alarmTriggered && (
            <motion.div
              animate={{ opacity: [1, 0.3, 1] }}
              transition={{ repeat: Infinity, duration: 1 }}
            >
              <AlertCircle size={14} className="text-[var(--danger)]" />
            </motion.div>
          )}
          {connected ? (
            <Wifi size={14} className="text-[var(--success)]" />
          ) : (
            <WifiOff size={14} className="text-[var(--text-secondary)]" />
          )}
        </div>
      </div>

      {/* Video alanı */}
      <div
        ref={containerRef}
        onClick={() => {
          if (camera.status === 'active') {
            setExpandedCamera(camera.id)
          }
        }}
        className={`relative aspect-video bg-[var(--bg-primary)] flex items-center justify-center ${
          camera.status === 'active' ? 'cursor-pointer group' : ''
        }`}
      >
        {frame ? (
          <img
            src={frame}
            alt={camera.name}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="flex flex-col items-center gap-2 text-[var(--text-secondary)]">
            <WifiOff size={24} className={camera.status === 'error' ? 'text-[var(--danger)]' : ''} />
            <span className={`text-xs ${camera.status === 'error' ? 'text-[var(--danger)]' : ''}`}>
              {camera.status === 'active'
                ? 'Bağlanıyor...'
                : camera.status === 'error'
                ? 'Bağlantı Yok — Yeniden deneniyor'
                : 'İzleme Kapalı'}
            </span>
          </div>
        )}
        <BoundingBoxOverlay box={box} containerWidth={dims.w} containerHeight={dims.h} />

        {/* Hover Canlı İzle Katmanı */}
        {camera.status === 'active' && (
          <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity duration-200 z-10">
            <span className="bg-black/60 text-white text-xs font-semibold px-3 py-1.5 rounded-full flex items-center gap-1.5 shadow-lg">
              <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
              Canlı İzle
            </span>
          </div>
        )}

        {/* Alarm banner */}
        {alarmTriggered && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            className="absolute top-2 left-2 right-2 bg-[var(--danger)]/90 text-white text-xs font-medium px-2 py-1 rounded text-center z-20"
          >
            İnsan Tespit Edildi
          </motion.div>
        )}
      </div>

      {/* Alt bilgi */}
      <div className="px-3 py-2 flex items-center justify-between">
        <span className="text-xs text-[var(--text-secondary)]">{camera.host}</span>
        <span
          className={`text-xs font-medium ${
            camera.status === 'active'
              ? 'text-[var(--success)]'
              : camera.status === 'error'
              ? 'text-[var(--danger)]'
              : 'text-[var(--text-secondary)]'
          }`}
        >
          {camera.status === 'active' ? 'Çevrimiçi' : camera.status === 'error' ? 'Çevrimdışı' : 'İzleme Kapalı'}
        </span>
      </div>
    </div>
  )
}
