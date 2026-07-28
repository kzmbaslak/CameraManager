// Kayit segmentleri ve playback envanteri ekrani.
import { useMemo, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import dayjs from 'dayjs'
import { Database, Film, Filter, RotateCcw, Trash2 } from 'lucide-react'
import { camerasApi } from '../api/cameras'
import { recordingsApi } from '../api/recordings'
import { Badge } from '../components/ui/Badge'
import { Button } from '../components/ui/Button'
import { Input } from '../components/ui/Input'
import { Spinner } from '../components/ui/Spinner'
import { Table } from '../components/ui/Table'
import { usePermissions } from '../hooks/usePermissions'
import { useToastStore } from '../stores/toastStore'
import { getApiErrorMessage } from '../utils/apiError'
import type { Camera, RecordingSegment } from '../types/api'

type DateRange = '24h' | '7d' | '30d' | 'all'

const DATE_RANGE_OPTIONS: { value: DateRange; label: string }[] = [
  { value: '24h', label: 'Son 24 Saat' },
  { value: '7d', label: 'Son 7 Gun' },
  { value: '30d', label: 'Son 30 Gun' },
  { value: 'all', label: 'Tumu' },
]

function dateRangeStart(range: DateRange) {
  if (range === 'all') return undefined
  if (range === '24h') return dayjs().subtract(24, 'hour').toISOString()
  if (range === '7d') return dayjs().subtract(7, 'day').toISOString()
  return dayjs().subtract(30, 'day').toISOString()
}

function formatBytes(value: number | null) {
  if (value == null) return '-'
  if (value < 1024) return `${value} B`
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`
  if (value < 1024 * 1024 * 1024) return `${(value / (1024 * 1024)).toFixed(1)} MB`
  return `${(value / (1024 * 1024 * 1024)).toFixed(2)} GB`
}

function formatDate(value: string | null) {
  return value ? dayjs(value).format('YYYY-MM-DD HH:mm:ss') : '-'
}

function recordingStatusVariant(status: string) {
  if (status === 'complete') return 'success'
  if (status === 'recording') return 'info'
  if (status === 'failed') return 'danger'
  return 'neutral'
}

function cameraName(cameraById: Record<number, Camera>, cameraId: number) {
  return cameraById[cameraId]?.name ?? `Kamera #${cameraId}`
}

export function RecordingsPage() {
  const { canViewRecordings, canManageRecordings } = usePermissions()
  const showToast = useToastStore((state) => state.showToast)
  const [selectedCameraId, setSelectedCameraId] = useState('all')
  const [range, setRange] = useState<DateRange>('24h')
  const [limit, setLimit] = useState(100)

  const { data: cameras = [] } = useQuery({
    queryKey: ['cameras'],
    queryFn: camerasApi.list,
    enabled: canViewRecordings,
  })

  const queryParams = {
    camera_id: selectedCameraId === 'all' ? undefined : Number(selectedCameraId),
    since: dateRangeStart(range),
    limit,
  }

  const recordingsQuery = useQuery({
    queryKey: ['recordings', queryParams],
    queryFn: () => recordingsApi.list(queryParams),
    enabled: canViewRecordings,
  })

  const pruneMutation = useMutation({
    mutationFn: () => recordingsApi.prune(),
    onSuccess: (result) => {
      showToast({
        variant: 'success',
        title: 'Kayit temizligi tamamlandi',
        description: `${result.removed_count} segment silindi, ${formatBytes(result.removed_bytes)} alan acildi.`,
      })
      void recordingsQuery.refetch()
    },
    onError: (err) => showToast({
      variant: 'danger',
      title: 'Kayit temizligi basarisiz',
      description: getApiErrorMessage(err, 'Retention ve disk kotasi ayarlarini kontrol edin.'),
    }),
  })

  const cameraById = useMemo(
    () => Object.fromEntries(cameras.map((camera) => [camera.id, camera])),
    [cameras],
  )
  const segments = recordingsQuery.data?.items ?? []
  const totalBytes = segments.reduce((sum, segment) => sum + (segment.size_bytes ?? 0), 0)
  const eventCount = segments.filter((segment) => segment.recording_type === 'event').length
  const openCount = segments.filter((segment) => segment.status === 'recording').length

  const columns = [
    {
      key: 'time',
      header: 'Zaman',
      render: (segment: RecordingSegment) => (
        <div className="min-w-36">
          <p className="font-medium text-text-primary">{formatDate(segment.started_at)}</p>
          <p className="text-xs text-text-secondary">{segment.duration_seconds == null ? 'Devam ediyor' : `${segment.duration_seconds.toFixed(1)} sn`}</p>
        </div>
      ),
    },
    {
      key: 'camera',
      header: 'Kamera',
      render: (segment: RecordingSegment) => cameraName(cameraById, segment.camera_id),
    },
    {
      key: 'type',
      header: 'Tip',
      render: (segment: RecordingSegment) => (
        <Badge variant={segment.recording_type === 'event' ? 'warning' : 'neutral'}>
          {segment.recording_type === 'event' ? 'Olay' : 'Surekli'}
        </Badge>
      ),
    },
    {
      key: 'status',
      header: 'Durum',
      render: (segment: RecordingSegment) => (
        <Badge variant={recordingStatusVariant(segment.status)}>{segment.status}</Badge>
      ),
    },
    {
      key: 'media',
      header: 'Medya',
      render: (segment: RecordingSegment) => (
        <div className="min-w-40">
          <p className="truncate font-mono text-xs text-text-primary">{segment.filename}</p>
          <p className="text-xs text-text-secondary">
            {[segment.codec, segment.width && segment.height ? `${segment.width}x${segment.height}` : null, segment.fps ? `${segment.fps} FPS` : null]
              .filter(Boolean)
              .join(' / ') || '-'}
          </p>
        </div>
      ),
    },
    {
      key: 'size',
      header: 'Boyut',
      render: (segment: RecordingSegment) => formatBytes(segment.size_bytes),
    },
    {
      key: 'hash',
      header: 'SHA-256',
      render: (segment: RecordingSegment) => (
        <span className="block max-w-44 truncate font-mono text-xs text-text-secondary" title={segment.file_sha256 ?? undefined}>
          {segment.file_sha256 ?? '-'}
        </span>
      ),
    },
  ]

  if (!canViewRecordings) {
    return (
      <div className="p-6">
        <div className="rounded-lg border border-border bg-bg-card p-5 text-sm text-text-secondary">
          Kayit envanterini goruntuleme yetkiniz yok.
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-5 p-6">
      <div className="flex flex-col gap-3 border-b border-border pb-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h1 className="flex items-center gap-2 text-xl font-semibold text-text-primary">
            <Film size={21} />
            Kayitlar ve Playback
          </h1>
          <p className="mt-1 text-sm text-text-secondary">Olay klipleri, segment envanteri ve kayit bakimi</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="secondary" icon={<RotateCcw size={15} />} onClick={() => recordingsQuery.refetch()}>
            Yenile
          </Button>
          {canManageRecordings && (
            <Button
              variant="danger"
              icon={<Trash2 size={15} />}
              loading={pruneMutation.isPending}
              onClick={() => pruneMutation.mutate()}
            >
              Retention Temizle
            </Button>
          )}
        </div>
      </div>

      <div className="grid gap-3 md:grid-cols-3">
        <div className="rounded-lg border border-border bg-bg-card p-4">
          <p className="text-xs font-semibold uppercase text-text-secondary">Segment</p>
          <p className="mt-1 text-2xl font-semibold text-text-primary">{segments.length}</p>
        </div>
        <div className="rounded-lg border border-border bg-bg-card p-4">
          <p className="text-xs font-semibold uppercase text-text-secondary">Olay Kaydi</p>
          <p className="mt-1 text-2xl font-semibold text-warning">{eventCount}</p>
        </div>
        <div className="rounded-lg border border-border bg-bg-card p-4">
          <p className="text-xs font-semibold uppercase text-text-secondary">Toplam Boyut</p>
          <p className="mt-1 text-2xl font-semibold text-text-primary">{formatBytes(totalBytes)}</p>
          {openCount > 0 && <p className="mt-1 text-xs text-info">{openCount} segment yaziliyor</p>}
        </div>
      </div>

      <div className="rounded-lg border border-border bg-bg-card p-4">
        <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-text-primary">
          <Filter size={16} />
          Filtreler
        </div>
        <div className="grid gap-3 md:grid-cols-[minmax(180px,1fr)_minmax(180px,1fr)_140px]">
          <label className="flex flex-col gap-1.5 text-sm font-medium text-text-secondary">
            Kamera
            <select
              aria-label="Kayit kamera filtresi"
              value={selectedCameraId}
              onChange={(event) => setSelectedCameraId(event.target.value)}
              className="rounded-lg border border-border bg-bg-primary px-3 py-2 text-sm text-text-primary outline-none focus:border-accent"
            >
              <option value="all">Tum kameralar</option>
              {cameras.map((camera) => (
                <option key={camera.id} value={camera.id}>{camera.name}</option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1.5 text-sm font-medium text-text-secondary">
            Zaman
            <select
              aria-label="Kayit zaman filtresi"
              value={range}
              onChange={(event) => setRange(event.target.value as DateRange)}
              className="rounded-lg border border-border bg-bg-primary px-3 py-2 text-sm text-text-primary outline-none focus:border-accent"
            >
              {DATE_RANGE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          </label>
          <Input
            label="Limit"
            type="number"
            min={1}
            max={500}
            value={limit}
            onChange={(event) => setLimit(Math.min(Math.max(Number(event.target.value) || 1, 1), 500))}
          />
        </div>
      </div>

      {recordingsQuery.isLoading ? (
        <div className="flex min-h-48 items-center justify-center">
          <Spinner />
        </div>
      ) : recordingsQuery.isError ? (
        <div className="rounded-lg border border-danger/30 bg-danger/10 p-4 text-sm text-danger">
          {getApiErrorMessage(recordingsQuery.error, 'Kayit segmentleri yuklenemedi.')}
        </div>
      ) : (
        <Table
          caption="Kayit segmentleri"
          columns={columns}
          data={segments}
          keyFn={(segment) => segment.id}
          emptyText="Kayit segmenti bulunamadi"
        />
      )}

      <div className="rounded-lg border border-border bg-bg-secondary p-4 text-xs text-text-secondary">
        <div className="flex items-center gap-2 font-semibold text-text-primary">
          <Database size={15} />
          Kanit Butunlugu
        </div>
        <p className="mt-1">
          Segment listesi fiziksel dosya yolunu gostermez; dosya adi, SHA-256 ve alarm bagi uzerinden takip edilir.
        </p>
      </div>
    </div>
  )
}
