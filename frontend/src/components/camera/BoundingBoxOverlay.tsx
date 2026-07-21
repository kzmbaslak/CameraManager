// Kamera goruntusu uzerinde Detection/BoundingBox kutularini cizer.
import { useEffect, useRef } from 'react'
import type { BoundingBox, Detection } from '../../types/api'

type ObjectFitMode = 'cover' | 'contain'

interface BoundingBoxOverlayProps {
  detections?: Detection[]
  box?: BoundingBox | null
  containerWidth: number
  containerHeight: number
  sourceWidth?: number | null
  sourceHeight?: number | null
  fit?: ObjectFitMode
}

function transformBox(
  box: BoundingBox,
  containerWidth: number,
  containerHeight: number,
  sourceWidth: number | null | undefined,
  sourceHeight: number | null | undefined,
  fit: ObjectFitMode,
) {
  if (!sourceWidth || !sourceHeight) {
    return box
  }

  const scale = fit === 'contain'
    ? Math.min(containerWidth / sourceWidth, containerHeight / sourceHeight)
    : Math.max(containerWidth / sourceWidth, containerHeight / sourceHeight)
  const renderedWidth = sourceWidth * scale
  const renderedHeight = sourceHeight * scale
  const offsetX = (containerWidth - renderedWidth) / 2
  const offsetY = (containerHeight - renderedHeight) / 2

  return {
    x: box.x * scale + offsetX,
    y: box.y * scale + offsetY,
    width: box.width * scale,
    height: box.height * scale,
  }
}

/** Canli goruntude insan tespitlerini guven skoru etiketiyle gosterir. */
export function BoundingBoxOverlay({
  detections = [],
  box,
  containerWidth,
  containerHeight,
  sourceWidth,
  sourceHeight,
  fit = 'cover',
}: BoundingBoxOverlayProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    ctx.clearRect(0, 0, canvas.width, canvas.height)

    const items = detections.length
      ? detections
      : box
      ? [{ label: 'person', confidence: 0, bounding_box: box }]
      : []
    if (!items.length) return

    ctx.lineWidth = Math.max(2, Math.round(containerWidth / 320))
    ctx.font = 'bold 11px Inter, sans-serif'

    for (const detection of items) {
      const scaled = transformBox(
        detection.bounding_box,
        containerWidth,
        containerHeight,
        sourceWidth,
        sourceHeight,
        fit,
      )
      const confidence = detection.confidence ? ` ${Math.round(detection.confidence * 100)}%` : ''
      const label = `Insan${confidence}`
      const labelW = ctx.measureText(label).width + 10
      const labelH = 18
      const labelY = Math.max(0, scaled.y - labelH)

      ctx.save()
      ctx.strokeStyle = '#f97316'
      ctx.shadowColor = 'rgba(249, 115, 22, 0.8)'
      ctx.shadowBlur = 8
      ctx.strokeRect(scaled.x, scaled.y, scaled.width, scaled.height)
      ctx.restore()

      ctx.fillStyle = 'rgba(249, 115, 22, 0.96)'
      ctx.fillRect(scaled.x, labelY, labelW, labelH)
      ctx.fillStyle = '#111827'
      ctx.fillText(label, scaled.x + 5, labelY + 13)
    }
  }, [box, detections, containerWidth, containerHeight, sourceWidth, sourceHeight, fit])

  return (
    <canvas
      ref={canvasRef}
      width={containerWidth}
      height={containerHeight}
      className="pointer-events-none absolute inset-0 z-[5]"
    />
  )
}
