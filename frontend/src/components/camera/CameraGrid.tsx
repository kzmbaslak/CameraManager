// Kamera grid bileşeni — seçilen sütun sayısına göre kameraları dizer; 1×1 modda navigasyon sunar
import { useState } from 'react'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { CameraCard } from './CameraCard'
import type { Camera, Alarm } from '../../types/api'

/** Desteklenen sütun sayıları */
export type GridCols = 1 | 2 | 3 | 4

interface CameraGridProps {
  cameras: Camera[]
  /** kamera id → son alarm eşlemesi */
  alarmMap?: Record<number, Alarm>
  /** Sütun sayısı — GridSizeSelector'dan gelir */
  cols?: GridCols
}

const colsClass: Record<GridCols, string> = {
  1: 'grid-cols-1',
  2: 'grid-cols-2',
  3: 'grid-cols-3',
  4: 'grid-cols-4',
}

/** Kamera yoksa boş durum */
function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center h-64 text-[var(--text-secondary)]">
      <p className="text-sm">İzlenen kamera bulunamadı.</p>
    </div>
  )
}

/** 1×1 modda tek kamera büyük + önceki/sonraki navigasyon */
function SingleView({ cameras, alarmMap }: { cameras: Camera[]; alarmMap: Record<number, Alarm> }) {
  const [index, setIndex] = useState(0)
  const camera = cameras[Math.min(index, cameras.length - 1)]

  if (!camera) return <EmptyState />

  return (
    <div className="flex flex-col gap-3">
      {/* Navigasyon çubuğu */}
      {cameras.length > 1 && (
        <div className="flex items-center justify-between">
          <button
            onClick={() => setIndex((i) => Math.max(0, i - 1))}
            disabled={index === 0}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-card)] disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            <ChevronLeft size={16} />
            Önceki
          </button>

          {/* Kamera noktaları */}
          <div className="flex items-center gap-1.5">
            {cameras.map((c, i) => (
              <button
                key={c.id}
                onClick={() => setIndex(i)}
                title={c.name}
                className={`w-2 h-2 rounded-full transition-colors ${
                  i === index ? 'bg-[var(--accent)]' : 'bg-[var(--border)] hover:bg-[var(--text-secondary)]'
                }`}
              />
            ))}
          </div>

          <button
            onClick={() => setIndex((i) => Math.min(cameras.length - 1, i + 1))}
            disabled={index === cameras.length - 1}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-card)] disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            Sonraki
            <ChevronRight size={16} />
          </button>
        </div>
      )}

      {/* Büyük kamera kartı */}
      <div className="max-w-4xl mx-auto w-full">
        <CameraCard camera={camera} latestAlarm={alarmMap[camera.id] ?? null} />
      </div>

      {/* Alt kamera adı ve sayaç */}
      <p className="text-center text-xs text-[var(--text-secondary)]">
        {index + 1} / {cameras.length} — {camera.name}
      </p>
    </div>
  )
}

/** Ana grid bileşeni */
export function CameraGrid({ cameras, alarmMap = {}, cols = 2 }: CameraGridProps) {
  if (cameras.length === 0) return <EmptyState />

  if (cols === 1) {
    return <SingleView cameras={cameras} alarmMap={alarmMap} />
  }

  return (
    <div className={`grid ${colsClass[cols]} gap-3`}>
      {cameras.map((camera) => (
        <CameraCard
          key={camera.id}
          camera={camera}
          latestAlarm={alarmMap[camera.id] ?? null}
        />
      ))}
    </div>
  )
}
