// Camera grid with selectable density.
import { useState } from 'react'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { CameraCard } from './CameraCard'
import type { Alarm, Camera } from '../../types/api'

export type GridCols = 1 | 2 | 3 | 4

interface CameraGridProps {
  cameras: Camera[]
  alarmMap?: Record<number, Alarm>
  cols?: GridCols
  lowBandwidth?: boolean
}

const colsClass: Record<GridCols, string> = {
  1: 'grid-cols-1',
  2: 'grid-cols-2',
  3: 'grid-cols-3',
  4: 'grid-cols-4',
}

function EmptyState() {
  return (
    <div className="flex h-64 flex-col items-center justify-center rounded-md border border-dashed border-border bg-bg-secondary text-text-secondary">
      <p className="text-sm">İzlenen kamera bulunamadı.</p>
    </div>
  )
}

function SingleView({
  cameras,
  alarmMap,
  lowBandwidth,
}: {
  cameras: Camera[]
  alarmMap: Record<number, Alarm>
  lowBandwidth: boolean
}) {
  const [index, setIndex] = useState(0)
  const camera = cameras[Math.min(index, cameras.length - 1)]

  if (!camera) return <EmptyState />

  return (
    <div className="flex flex-col gap-3">
      {cameras.length > 1 && (
        <div className="flex items-center justify-between">
          <button
            onClick={() => setIndex((value) => Math.max(0, value - 1))}
            disabled={index === 0}
            className="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm text-text-secondary transition-colors hover:bg-bg-card hover:text-text-primary disabled:cursor-not-allowed disabled:opacity-30"
          >
            <ChevronLeft size={16} />
            Önceki
          </button>

          <div className="flex items-center gap-1.5">
            {cameras.map((item, itemIndex) => (
              <button
                key={item.id}
                onClick={() => setIndex(itemIndex)}
                title={item.name}
                aria-label={`${item.name} kamerasına geç`}
                className={`h-2 w-2 rounded-full transition-colors ${
                  itemIndex === index ? 'bg-accent' : 'bg-border hover:bg-text-secondary'
                }`}
              />
            ))}
          </div>

          <button
            onClick={() => setIndex((value) => Math.min(cameras.length - 1, value + 1))}
            disabled={index === cameras.length - 1}
            className="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm text-text-secondary transition-colors hover:bg-bg-card hover:text-text-primary disabled:cursor-not-allowed disabled:opacity-30"
          >
            Sonraki
            <ChevronRight size={16} />
          </button>
        </div>
      )}

      <div className="mx-auto w-full max-w-4xl">
        <CameraCard camera={camera} latestAlarm={alarmMap[camera.id] ?? null} streamProfile={lowBandwidth ? 'alarm' : 'grid'} />
      </div>

      <p className="text-center text-xs text-text-secondary">
        {index + 1} / {cameras.length} - {camera.name}
      </p>
    </div>
  )
}

export function CameraGrid({ cameras, alarmMap = {}, cols = 2, lowBandwidth = false }: CameraGridProps) {
  if (cameras.length === 0) return <EmptyState />
  if (cols === 1) return <SingleView cameras={cameras} alarmMap={alarmMap} lowBandwidth={lowBandwidth} />

  return (
    <div className={`grid ${colsClass[cols]} gap-2`}>
      {cameras.map((camera) => (
        <CameraCard
          key={camera.id}
          camera={camera}
          latestAlarm={alarmMap[camera.id] ?? null}
          streamProfile={lowBandwidth ? 'alarm' : 'grid'}
        />
      ))}
    </div>
  )
}
