// Select camera grid density.
import type { GridCols } from './CameraGrid'

interface GridSizeSelectorProps {
  value: GridCols
  onChange: (cols: GridCols) => void
}

const GridIcon = ({ cols }: { cols: GridCols }) => {
  const cells = Array.from({ length: cols * cols })
  const gap = 1
  const cellSize = cols === 1 ? 10 : cols === 2 ? 5 : cols === 3 ? 3 : 2.5

  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
      {cells.map((_, index) => {
        const row = Math.floor(index / cols)
        const col = index % cols
        const total = cellSize * cols + gap * (cols - 1)
        const offset = (16 - total) / 2
        return (
          <rect
            key={index}
            x={offset + col * (cellSize + gap)}
            y={offset + row * (cellSize + gap)}
            width={cellSize}
            height={cellSize}
            rx={0.5}
            fill="currentColor"
          />
        )
      })}
    </svg>
  )
}

const options: { cols: GridCols; label: string }[] = [
  { cols: 1, label: '1x1' },
  { cols: 2, label: '2x2' },
  { cols: 3, label: '3x3' },
  { cols: 4, label: '4x4' },
]

export function GridSizeSelector({ value, onChange }: GridSizeSelectorProps) {
  return (
    <div className="flex items-center gap-1 rounded-md border border-border bg-bg-secondary p-1">
      {options.map(({ cols, label }) => (
        <button
          key={cols}
          title={label}
          aria-label={`${label} kamera grid görünümü`}
          onClick={() => onChange(cols)}
          className={`flex h-8 w-8 items-center justify-center rounded transition-colors ${
            value === cols
              ? 'bg-accent text-white'
              : 'text-text-secondary hover:bg-bg-card hover:text-text-primary'
          }`}
        >
          <GridIcon cols={cols} />
        </button>
      ))}
    </div>
  )
}
