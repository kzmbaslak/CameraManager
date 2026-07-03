import { useEffect, useRef } from 'react'
import type { BoundingBox } from '../../types/api'

interface BoundingBoxOverlayProps {
  box: BoundingBox | null
  containerWidth: number
  containerHeight: number
}

export function BoundingBoxOverlay({ box, containerWidth, containerHeight }: BoundingBoxOverlayProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    ctx.clearRect(0, 0, canvas.width, canvas.height)

    if (!box) return

    // Alarm kutusunu kırmızıyla çiz
    ctx.strokeStyle = '#ef4444'
    ctx.lineWidth = 2
    ctx.shadowColor = '#ef4444'
    ctx.shadowBlur = 6
    ctx.strokeRect(box.x, box.y, box.width, box.height)

    // "İnsan Tespit" etiketi
    ctx.fillStyle = '#ef4444'
    ctx.font = 'bold 11px Inter, sans-serif'
    const label = 'İnsan Tespit'
    const labelW = ctx.measureText(label).width + 8
    ctx.fillRect(box.x, box.y - 18, labelW, 18)
    ctx.fillStyle = '#ffffff'
    ctx.shadowBlur = 0
    ctx.fillText(label, box.x + 4, box.y - 5)
  }, [box, containerWidth, containerHeight])

  return (
    <canvas
      ref={canvasRef}
      width={containerWidth}
      height={containerHeight}
      className="absolute inset-0 pointer-events-none"
    />
  )
}
