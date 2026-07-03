// Grid boyutu seçici — 1×1, 2×2, 3×3, 4×4 seçenekleri sunar
import type { GridCols } from './CameraGrid'

interface GridSizeSelectorProps {
  value: GridCols
  onChange: (cols: GridCols) => void
}

/** Grid ızgarasını temsil eden küçük SVG ikonları */
const GridIcon = ({ cols }: { cols: GridCols }) => {
  const n = cols
  const cells = Array.from({ length: n * n })
  const gap = 1
  const cellSize = cols === 1 ? 10 : cols === 2 ? 5 : cols === 3 ? 3 : 2.5

  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
      {cells.map((_, i) => {
        const row = Math.floor(i / n)
        const col = i % n
        const total = cellSize * n + gap * (n - 1)
        const offset = (16 - total) / 2
        const x = offset + col * (cellSize + gap)
        const y = offset + row * (cellSize + gap)
        return (
          <rect
            key={i}
            x={x}
            y={y}
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
  { cols: 1, label: '1×1' },
  { cols: 2, label: '2×2' },
  { cols: 3, label: '3×3' },
  { cols: 4, label: '4×4' },
]

/** Kullanıcının dashboard'da kaç sütunlu grid göreceğini seçmesini sağlar */
export function GridSizeSelector({ value, onChange }: GridSizeSelectorProps) {
  return (
    <div className="flex items-center gap-1 bg-[var(--bg-card)] border border-[var(--border)] rounded-lg p-1">
      {options.map(({ cols, label }) => (
        <button
          key={cols}
          title={label}
          onClick={() => onChange(cols)}
          className={`
            flex items-center justify-center w-8 h-8 rounded transition-colors
            ${value === cols
              ? 'bg-[var(--accent)] text-white'
              : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-secondary)]'
            }
          `}
        >
          <GridIcon cols={cols} />
        </button>
      ))}
    </div>
  )
}
