// Live camera tile for the operator grid.
import { useEffect, useRef, useState } from 'react'
import { motion } from 'framer-motion'
import { AlertCircle, Play, Wifi, WifiOff } from 'lucide-react'
import { useCameraStream } from '../../hooks/useCameraStream'
import { BoundingBoxOverlay } from './BoundingBoxOverlay'
import { useAlarmStore } from '../../stores/alarmStore'
import type { Alarm, Camera } from '../../types/api'

interface CameraCardProps {
  camera: Camera
  latestAlarm?: Alarm | null
}

export function CameraCard({ camera, latestAlarm }: CameraCardProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [dims, setDims] = useState({ w: 320, h: 180 })
  const [isNearViewport, setIsNearViewport] = useState(false)
  const { setExpandedCamera } = useAlarmStore()

  const { frame, alarmTriggered, connected } = useCameraStream(
    camera.id,
    camera.status !== 'inactive' && isNearViewport,
  )

  useEffect(() => {
    if (!containerRef.current) return
    const observer = new IntersectionObserver(
      ([entry]) => setIsNearViewport(entry.isIntersecting),
      { rootMargin: '240px 0px' },
    )
    observer.observe(containerRef.current)
    return () => observer.disconnect()
  }, [])

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
    <div className={`flex flex-col overflow-hidden rounded-md border bg-bg-card ${
      alarmTriggered ? 'border-danger shadow-[0_0_0_1px_rgba(220,38,38,0.35)]' : 'border-border'
    }`}>
      <div className="flex items-center justify-between border-b border-border bg-bg-secondary px-3 py-2">
        <span className="truncate text-sm font-medium text-text-primary">{camera.name}</span>
        <div className="flex shrink-0 items-center gap-1.5">
          {alarmTriggered && (
            <motion.div animate={{ opacity: [1, 0.35, 1] }} transition={{ repeat: Infinity, duration: 1 }}>
              <AlertCircle size={14} className="text-danger" />
            </motion.div>
          )}
          {connected ? (
            <Wifi size={14} className="text-success" />
          ) : (
            <WifiOff size={14} className="text-text-secondary" />
          )}
        </div>
      </div>

      <div
        ref={containerRef}
        onClick={() => {
          if (camera.status === 'active') setExpandedCamera(camera.id, latestAlarm?.id ?? null)
        }}
        className={`relative flex aspect-video items-center justify-center bg-bg-primary ${
          camera.status === 'active' ? 'group cursor-pointer' : ''
        }`}
      >
        {frame ? (
          <img src={frame} alt={camera.name} className="h-full w-full object-cover" />
        ) : (
          <div className="flex flex-col items-center gap-2 text-text-secondary">
            <WifiOff size={24} className={camera.status === 'error' ? 'text-danger' : ''} />
            <span className={`text-xs ${camera.status === 'error' ? 'text-danger' : ''}`}>
              {camera.status === 'active'
                ? 'Bağlanıyor...'
                : camera.status === 'error'
                ? 'Bağlantı Yok - Yeniden deneniyor'
                : 'İzleme Kapalı'}
            </span>
          </div>
        )}
        <BoundingBoxOverlay box={box} containerWidth={dims.w} containerHeight={dims.h} />

        {camera.status === 'active' && (
          <div className="absolute inset-0 z-10 flex items-center justify-center bg-black/45 opacity-0 transition-opacity duration-200 group-hover:opacity-100">
            <span className="flex items-center gap-1.5 rounded bg-black/70 px-3 py-1.5 text-xs font-semibold text-white shadow-lg">
              <Play size={12} fill="currentColor" />
              Canlı İzle
            </span>
          </div>
        )}

        {alarmTriggered && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            className="absolute left-2 right-2 top-2 z-20 rounded bg-danger/95 px-2 py-1 text-center text-xs font-semibold uppercase tracking-wide text-white"
          >
            İnsan Tespit Edildi
          </motion.div>
        )}
      </div>

      <div className="flex items-center justify-between border-t border-border px-3 py-2">
        <span className="font-mono text-xs text-text-secondary">{camera.host}</span>
        <span
          className={`text-xs font-medium ${
            camera.status === 'active'
              ? 'text-success'
              : camera.status === 'error'
              ? 'text-danger'
              : 'text-text-secondary'
          }`}
        >
          {camera.status === 'active' ? 'Çevrimiçi' : camera.status === 'error' ? 'Çevrimdışı' : 'İzleme Kapalı'}
        </span>
      </div>
    </div>
  )
}
