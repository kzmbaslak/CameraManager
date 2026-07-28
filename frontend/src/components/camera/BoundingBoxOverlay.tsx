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
  emphasis?: 'grid' | 'live'
  stale?: boolean
}

function transformBox(
  box: BoundingBox,
  containerWidth: number,
  containerHeight: number,
  sourceWidth: number | null | undefined,
  sourceHeight: number | null | undefined,
  fit: ObjectFitMode,
) {
  const isNormalized = box.x <= 1 && box.y <= 1 && box.width <= 1 && box.height <= 1
  const sourceBox = isNormalized && sourceWidth && sourceHeight
    ? {
        x: box.x * sourceWidth,
        y: box.y * sourceHeight,
        width: box.width * sourceWidth,
        height: box.height * sourceHeight,
      }
    : box

  if (!sourceWidth || !sourceHeight) {
    return {
      x: isNormalized ? sourceBox.x * containerWidth : sourceBox.x,
      y: isNormalized ? sourceBox.y * containerHeight : sourceBox.y,
      width: isNormalized ? sourceBox.width * containerWidth : sourceBox.width,
      height: isNormalized ? sourceBox.height * containerHeight : sourceBox.height,
    }
  }

  const scale = fit === 'contain'
    ? Math.min(containerWidth / sourceWidth, containerHeight / sourceHeight)
    : Math.max(containerWidth / sourceWidth, containerHeight / sourceHeight)
  const renderedWidth = sourceWidth * scale
  const renderedHeight = sourceHeight * scale
  const offsetX = (containerWidth - renderedWidth) / 2
  const offsetY = (containerHeight - renderedHeight) / 2

  return {
    x: sourceBox.x * scale + offsetX,
    y: sourceBox.y * scale + offsetY,
    width: sourceBox.width * scale,
    height: sourceBox.height * scale,
  }
}

function clampBox(box: BoundingBox, containerWidth: number, containerHeight: number) {
  const x = Math.min(Math.max(box.x, 0), containerWidth)
  const y = Math.min(Math.max(box.y, 0), containerHeight)
  const right = Math.min(Math.max(box.x + box.width, 0), containerWidth)
  const bottom = Math.min(Math.max(box.y + box.height, 0), containerHeight)

  return {
    x,
    y,
    width: Math.max(0, right - x),
    height: Math.max(0, bottom - y),
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
  emphasis = 'grid',
  stale = false,
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

    ctx.lineWidth = emphasis === 'live'
      ? Math.max(3, Math.round(containerWidth / 260))
      : Math.max(2, Math.round(containerWidth / 340))
    ctx.font = `bold ${emphasis === 'live' ? 13 : 11}px Inter, sans-serif`

    for (const detection of items) {
      const scaled = clampBox(transformBox(
        detection.bounding_box,
        containerWidth,
        containerHeight,
        sourceWidth,
        sourceHeight,
        fit,
      ), containerWidth, containerHeight)
      if (scaled.width < 2 || scaled.height < 2) continue

      const confidence = detection.confidence ? ` ${Math.round(detection.confidence * 100)}%` : ''
      const label = `Insan${confidence}`
      const labelW = ctx.measureText(label).width + 12
      const labelH = emphasis === 'live' ? 22 : 18
      const labelY = Math.max(0, scaled.y - labelH)
      const labelX = Math.min(scaled.x, Math.max(0, containerWidth - labelW))

      ctx.save()
      ctx.strokeStyle = stale ? '#fbbf24' : '#f97316'
      ctx.shadowColor = stale ? 'rgba(251, 191, 36, 0.7)' : 'rgba(249, 115, 22, 0.85)'
      ctx.shadowBlur = emphasis === 'live' ? 12 : 8
      if (stale) ctx.setLineDash([8, 5])
      ctx.strokeRect(scaled.x, scaled.y, scaled.width, scaled.height)
      ctx.setLineDash([])
      ctx.restore()

      ctx.fillStyle = stale ? 'rgba(251, 191, 36, 0.96)' : 'rgba(249, 115, 22, 0.96)'
      ctx.fillRect(labelX, labelY, labelW, labelH)
      ctx.fillStyle = '#111827'
      ctx.fillText(label, labelX + 6, labelY + (emphasis === 'live' ? 16 : 13))
    }
  }, [box, detections, containerWidth, containerHeight, sourceWidth, sourceHeight, fit, emphasis, stale])

  return (
    <canvas
      ref={canvasRef}
      width={containerWidth}
      height={containerHeight}
      className="pointer-events-none absolute inset-0 z-[5]"
    />
  )
}
