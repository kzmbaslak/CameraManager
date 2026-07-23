// Server-side list pagination controls shared by management tables.
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { Button } from './Button'

interface PaginationControlsProps {
  page: number
  pageSize: number
  total: number
  onPageChange: (page: number) => void
  onPageSizeChange: (pageSize: number) => void
}

export function PaginationControls({
  page,
  pageSize,
  total,
  onPageChange,
  onPageSizeChange,
}: PaginationControlsProps) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize))
  const start = total === 0 ? 0 : (page - 1) * pageSize + 1
  const end = Math.min(total, page * pageSize)

  return (
    <div className="flex flex-col gap-2 rounded-b-xl border-x border-b border-[var(--border)] bg-[var(--bg-card)] px-4 py-3 text-xs text-[var(--text-secondary)] sm:flex-row sm:items-center sm:justify-between">
      <span>
        {start}-{end} / {total} kayit
      </span>
      <div className="flex flex-wrap items-center gap-2">
        <select
          value={pageSize}
          onChange={(e) => onPageSizeChange(Number(e.target.value))}
          aria-label="Sayfa boyutu"
          className="rounded-md border border-[var(--border)] bg-[var(--bg-primary)] px-2 py-1 text-xs text-[var(--text-primary)] outline-none focus:border-[var(--accent)]"
        >
          <option value={10}>10</option>
          <option value={25}>25</option>
          <option value={50}>50</option>
          <option value={100}>100</option>
        </select>
        <Button
          size="sm"
          variant="secondary"
          icon={<ChevronLeft size={13} />}
          disabled={page <= 1}
          onClick={() => onPageChange(page - 1)}
        >
          Onceki
        </Button>
        <span className="min-w-16 text-center">
          {page} / {totalPages}
        </span>
        <Button
          size="sm"
          variant="secondary"
          icon={<ChevronRight size={13} />}
          disabled={page >= totalPages}
          onClick={() => onPageChange(page + 1)}
        >
          Sonraki
        </Button>
      </div>
    </div>
  )
}
