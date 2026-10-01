// Kayit segmentleri ve playback envanteri ekrani.
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import dayjs from 'dayjs'
import { Clock3, Database, Download, Film, Filter, Gauge, PlayCircle, RotateCcw, Trash2, X } from 'lucide-react'
import { camerasApi } from '../api/cameras'
import { recordingsApi } from '../api/recordings'
import { Badge } from '../components/ui/Badge'
import { Button } from '../components/ui/Button'
import { Input } from '../components/ui/Input'
import { Spinner } from '../components/ui/Spinner'
import { Table } from '../components/ui/Table'
import { BoundingBoxOverlay } from '../components/camera/BoundingBoxOverlay'
import { usePermissions } from '../hooks/usePermissions'
import { useSystemSettingsStore } from '../stores/systemSettingsStore'
import { useToastStore } from '../stores/toastStore'
import { getApiErrorMessage } from '../utils/apiError'
import type { Camera, RecordingMetadata, RecordingSegment } from '../types/api'

type DateRange = '24h' | '7d' | '30d' | 'all'

const DATE_RANGE_OPTIONS: { value: DateRange; label: string }[] = [
  { value: '24h', label: 'Son 24 Saat' },
  { value: '7d', label: 'Son 7 Gun' },
  { value: '30d', label: 'Son 30 Gun' },
  { value: 'all', label: 'Tumu' },
]
const PLAYBACK_SPEED_OPTIONS = [0.5, 1, 2, 4]

function dateRangeStart(range: DateRange, anchorMs = Date.now()) {
  if (range === 'all') return undefined
  const anchor = dayjs(anchorMs)
  if (range === '24h') return anchor.subtract(24, 'hour').toISOString()
  if (range === '7d') return anchor.subtract(7, 'day').toISOString()
  return anchor.subtract(30, 'day').toISOString()
}

function formatBytes(value: number | null | undefined) {
  if (value == null) return '-'
  if (value < 1024) return `${value} B`
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`
  if (value < 1024 * 1024 * 1024) return `${(value / (1024 * 1024)).toFixed(1)} MB`
  return `${(value / (1024 * 1024 * 1024)).toFixed(2)} GB`
}

function formatDate(value: string | null | undefined) {
  return value ? dayjs(value).format('YYYY-MM-DD HH:mm:ss') : '-'
}

function formatConfidence(value: number | null | undefined) {
  return value == null ? '-' : `${Math.round(value * 100)}%`
}

function formatPercent(value: number | null | undefined) {
  return value == null ? '-' : `%${value.toFixed(1)}`
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

function timelineBounds(segments: RecordingSegment[], range: DateRange, anchorMs: number) {
  const rangeStart = dateRangeStart(range, anchorMs)
  const fallbackEnd = dayjs(anchorMs)
  const fallbackStart = rangeStart ? dayjs(rangeStart) : fallbackEnd.subtract(24, 'hour')
  const timestamps = segments.flatMap((segment) => [
    dayjs(segment.started_at).valueOf(),
    segment.ended_at ? dayjs(segment.ended_at).valueOf() : fallbackEnd.valueOf(),
  ]).filter(Number.isFinite)
  if (!timestamps.length) {
    return { start: fallbackStart.valueOf(), end: fallbackEnd.valueOf() }
  }
  const start = range === 'all' ? Math.min(...timestamps) : Math.min(fallbackStart.valueOf(), ...timestamps)
  const end = Math.max(fallbackEnd.valueOf(), ...timestamps)
  return end <= start ? { start, end: start + 60_000 } : { start, end }
}

function clampPercent(value: number) {
  return Math.min(Math.max(value, 0), 100)
}

function segmentTimelineStyle(segment: RecordingSegment, start: number, end: number) {
  const total = Math.max(end - start, 1)
  const segmentStart = dayjs(segment.started_at).valueOf()
  const segmentEnd = segment.ended_at ? dayjs(segment.ended_at).valueOf() : Date.now()
  const left = clampPercent(((segmentStart - start) / total) * 100)
  const width = Math.max(1.2, clampPercent(((segmentEnd - segmentStart) / total) * 100))
  return { left: `${left}%`, width: `${Math.min(width, 100 - left)}%` }
}

function detectionOffsetSeconds(segment: RecordingSegment, metadata: RecordingMetadata | null) {
  if (!metadata?.detected_at) return null
  const startedAt = dayjs(segment.started_at)
  const detectedAt = dayjs(metadata.detected_at)
  if (!startedAt.isValid() || !detectedAt.isValid()) return null
  const offset = detectedAt.diff(startedAt, 'millisecond') / 1000
  if (offset < 0) return 0
  if (segment.duration_seconds != null) return Math.min(offset, segment.duration_seconds)
  return offset
}

export function RecordingsPage() {
  const { canViewRecordings, canManageRecordings } = usePermissions()
  const showToast = useToastStore((state) => state.showToast)
  const showHumanDetectionBoxes = useSystemSettingsStore((s) => s.humanDetectionBoxesVisible)
  const [searchParams, setSearchParams] = useSearchParams()
  const linkedAlarmId = Number(searchParams.get('alarm_id') || 0) || null
  const initialCameraId = searchParams.get('camera_id')
  const initialRange = searchParams.get('range') as DateRange | null
  const [selectedCameraId, setSelectedCameraId] = useState(initialCameraId && /^\d+$/.test(initialCameraId) ? initialCameraId : 'all')
  const [range, setRange] = useState<DateRange>(
    initialRange && DATE_RANGE_OPTIONS.some((option) => option.value === initialRange) ? initialRange : '24h',
  )
  const [rangeAnchorMs, setRangeAnchorMs] = useState(() => Date.now())
  const [limit, setLimit] = useState(100)
  const previewFrameRef = useRef<HTMLDivElement>(null)
  const previewVideoRef = useRef<HTMLVideoElement>(null)
  const autoOpenedAlarmRef = useRef<number | null>(null)
  const [previewDims, setPreviewDims] = useState({ w: 960, h: 540 })
  const [preview, setPreview] = useState<{ segment: RecordingSegment; url: string; metadata: RecordingMetadata | null } | null>(null)
  const [playbackSpeed, setPlaybackSpeed] = useState(1)
  const [loadingAction, setLoadingAction] = useState<{ id: number; action: 'play' | 'download' } | null>(null)
  const previewDetectionOffset = preview ? detectionOffsetSeconds(preview.segment, preview.metadata) : null
  const previewDuration = preview?.segment.duration_seconds ?? null
  const previewDetectionPercent = previewDetectionOffset !== null && previewDuration && Number.isFinite(previewDuration)
    ? clampPercent((previewDetectionOffset / previewDuration) * 100)
    : null
  const previewDetections = preview?.metadata?.detections ?? []
  const previewMotionPercent = preview?.metadata?.motion?.changed_percent ?? null
  const previewTamper = preview?.metadata?.tamper ?? null
  const previewMaxConfidence = previewDetections.length
    ? Math.max(...previewDetections.map((detection) => detection.confidence))
    : null

  const { data: cameras = [] } = useQuery({
    queryKey: ['cameras'],
    queryFn: camerasApi.list,
    enabled: canViewRecordings,
  })

  const rangeSince = useMemo(() => dateRangeStart(range, rangeAnchorMs), [range, rangeAnchorMs])
  const queryParams = useMemo(() => ({
    camera_id: selectedCameraId === 'all' ? undefined : Number(selectedCameraId),
    alarm_id: linkedAlarmId ?? undefined,
    since: rangeSince,
    limit,
  }), [limit, linkedAlarmId, rangeSince, selectedCameraId])

  const clearLinkedAlarm = () => {
    const next = new URLSearchParams(searchParams)
    next.delete('alarm_id')
    setSearchParams(next, { replace: true })
  }

  const recordingsQuery = useQuery({
    queryKey: ['recordings', queryParams],
    queryFn: () => recordingsApi.list(queryParams),
    enabled: canViewRecordings,
    refetchOnWindowFocus: false,
  })

  const refreshRecordings = () => {
    if (range === 'all') {
      void recordingsQuery.refetch()
      return
    }
    setRangeAnchorMs(Date.now())
  }

  const pruneMutation = useMutation({
    mutationFn: () => recordingsApi.prune(),
    onSuccess: (result) => {
      showToast({
        variant: 'success',
        title: 'Kayit temizligi tamamlandi',
        description: `${result.removed_count} segment silindi, ${formatBytes(result.removed_bytes)} alan acildi.`,
      })
      refreshRecordings()
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
  const segments = useMemo(() => recordingsQuery.data?.items ?? [], [recordingsQuery.data?.items])
  const totalBytes = segments.reduce((sum, segment) => sum + (segment.size_bytes ?? 0), 0)
  const eventCount = segments.filter((segment) => segment.recording_type === 'event').length
  const openCount = segments.filter((segment) => segment.status === 'recording').length
  const timeline = useMemo(() => {
    const bounds = timelineBounds(segments, range, rangeAnchorMs)
    const grouped = new Map<number, RecordingSegment[]>()
    for (const segment of segments) {
      const items = grouped.get(segment.camera_id) ?? []
      items.push(segment)
      grouped.set(segment.camera_id, items)
    }
    return {
      ...bounds,
      rows: Array.from(grouped.entries())
        .map(([cameraId, items]) => ({
          cameraId,
          items: items.sort((left, right) => dayjs(left.started_at).valueOf() - dayjs(right.started_at).valueOf()),
        }))
        .sort((left, right) => cameraName(cameraById, left.cameraId).localeCompare(cameraName(cameraById, right.cameraId))),
    }
  }, [cameraById, range, rangeAnchorMs, segments])

  useEffect(() => () => {
    if (preview?.url) URL.revokeObjectURL(preview.url)
  }, [preview?.url])

  useEffect(() => {
    if (!preview || !previewFrameRef.current) return
    const observer = new ResizeObserver((entries) => {
      const { width, height } = entries[0].contentRect
      setPreviewDims({ w: Math.round(width), h: Math.round(height) })
    })
    observer.observe(previewFrameRef.current)
    return () => observer.disconnect()
  }, [preview])

  useEffect(() => {
    if (previewVideoRef.current) {
      previewVideoRef.current.playbackRate = playbackSpeed
    }
  }, [playbackSpeed, preview])

  const fetchSegmentBlob = useCallback(async (segment: RecordingSegment, action: 'play' | 'download') => {
    if (segment.status !== 'complete') {
      showToast({
        variant: 'warning',
        title: 'Kayit tamamlanmamis',
        description: 'Devam eden segmentler tamamlanmadan oynatilamaz veya indirilemez.',
      })
      return null
    }
    setLoadingAction({ id: segment.id, action })
    try {
      return await recordingsApi.fileBlob(segment.id)
    } catch (err) {
      showToast({
        variant: 'danger',
        title: action === 'play' ? 'Kayit oynatilamadi' : 'Kayit indirilemedi',
        description: getApiErrorMessage(err, 'Dosya erisimi, yetki veya retention durumunu kontrol edin.'),
      })
      return null
    } finally {
      setLoadingAction(null)
    }
  }, [showToast])

  const playSegment = useCallback(async (segment: RecordingSegment) => {
    const blob = await fetchSegmentBlob(segment, 'play')
    if (!blob) return
    const metadata = await recordingsApi.metadata(segment.id).catch((err) => {
      showToast({
        variant: 'warning',
        title: 'Detection metadata alinamadi',
        description: getApiErrorMessage(err, 'Kayit video olarak acildi; insan kutulari gosterilemeyebilir.'),
      })
      return null
    })
    const url = URL.createObjectURL(blob)
    setPreview((current) => {
      if (current?.url) URL.revokeObjectURL(current.url)
      return { segment, url, metadata }
    })
  }, [fetchSegmentBlob, showToast])

  useEffect(() => {
    if (!linkedAlarmId || recordingsQuery.isLoading || recordingsQuery.isError) return
    if (autoOpenedAlarmRef.current === linkedAlarmId) return
    if (preview?.segment.alarm_id === linkedAlarmId) return
    const segment = segments.find((item) => item.alarm_id === linkedAlarmId && item.status === 'complete')
    if (!segment) return
    autoOpenedAlarmRef.current = linkedAlarmId
    const timer = window.setTimeout(() => {
      void playSegment(segment)
    }, 0)
    return () => window.clearTimeout(timer)
  }, [linkedAlarmId, playSegment, preview?.segment.alarm_id, recordingsQuery.isError, recordingsQuery.isLoading, segments])

  const downloadSegment = useCallback(async (segment: RecordingSegment) => {
    const blob = await fetchSegmentBlob(segment, 'download')
    if (!blob) return
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = segment.filename || `recording-${segment.id}.mp4`
    document.body.appendChild(anchor)
    anchor.click()
    anchor.remove()
    URL.revokeObjectURL(url)
  }, [fetchSegmentBlob])

  const seekPreview = (seconds: number) => {
    const video = previewVideoRef.current
    if (!video) return
    const duration = Number.isFinite(video.duration) ? video.duration : preview?.segment.duration_seconds ?? seconds
    video.currentTime = Math.min(Math.max(seconds, 0), Math.max(duration, 0))
    void video.play().catch(() => undefined)
  }

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
    {
      key: 'actions',
      header: 'Islem',
      render: (segment: RecordingSegment) => (
        <div className="flex items-center justify-end gap-1">
          <Button
            size="sm"
            variant="secondary"
            icon={<PlayCircle size={14} />}
            loading={loadingAction?.id === segment.id && loadingAction.action === 'play'}
            onClick={() => playSegment(segment)}
            title="Kaydi oynat"
          >
            Oynat
          </Button>
          <Button
            size="sm"
            variant="secondary"
            icon={<Download size={14} />}
            loading={loadingAction?.id === segment.id && loadingAction.action === 'download'}
            onClick={() => downloadSegment(segment)}
            title="Kaydi indir"
          >
            Indir
          </Button>
        </div>
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
          <Button variant="secondary" icon={<RotateCcw size={15} />} onClick={refreshRecordings}>
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
        {linkedAlarmId && (
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2 rounded-md border border-warning/30 bg-warning/10 px-3 py-2 text-xs text-text-secondary">
            <span>Alarm #{linkedAlarmId} olay kayitlari gosteriliyor. Tamamlanmis ilk klip otomatik acilir.</span>
            <Button size="sm" variant="secondary" onClick={clearLinkedAlarm}>
              Alarm Filtresini Kaldir
            </Button>
          </div>
        )}
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
              onChange={(event) => {
                setRange(event.target.value as DateRange)
                setRangeAnchorMs(Date.now())
              }}
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

      <div className="rounded-lg border border-border bg-bg-card p-4">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2 text-sm font-semibold text-text-primary">
            <Clock3 size={16} />
            Kamera Zaman Cizelgesi
          </div>
          <div className="flex items-center gap-2 text-xs text-text-secondary">
            <span>{dayjs(timeline.start).format('DD.MM HH:mm')}</span>
            <span className="h-px w-8 bg-border" />
            <span>{dayjs(timeline.end).format('DD.MM HH:mm')}</span>
          </div>
        </div>
        {timeline.rows.length === 0 ? (
          <div className="rounded-md border border-dashed border-border bg-bg-secondary p-4 text-sm text-text-secondary">
            Secili filtrelerde zaman cizelgesi icin kayit bulunamadi.
          </div>
        ) : (
          <div className="space-y-3">
            {timeline.rows.map((row) => (
              <div key={row.cameraId} className="grid gap-2 lg:grid-cols-[180px_minmax(0,1fr)]">
                <div className="flex min-w-0 items-center justify-between gap-2">
                  <span className="truncate text-sm font-medium text-text-primary">{cameraName(cameraById, row.cameraId)}</span>
                  <Badge variant="neutral">{row.items.length}</Badge>
                </div>
                <div className="relative h-9 rounded-md border border-border bg-bg-secondary">
                  <div className="absolute left-1/3 top-0 h-full w-px bg-border/70" />
                  <div className="absolute left-2/3 top-0 h-full w-px bg-border/70" />
                  {row.items.map((segment) => (
                    <button
                      key={segment.id}
                      type="button"
                      aria-label={`${cameraName(cameraById, segment.camera_id)} ${formatDate(segment.started_at)} kaydini oynat`}
                      title={`${formatDate(segment.started_at)} - ${segment.recording_type === 'event' ? 'Olay' : 'Surekli'} - ${segment.status}`}
                      onClick={() => playSegment(segment)}
                      className={`absolute top-1 h-7 rounded-sm border transition-all hover:top-0.5 hover:h-8 focus:outline-none focus:ring-2 focus:ring-accent ${
                        segment.recording_type === 'event'
                          ? 'border-warning bg-warning/80 hover:bg-warning'
                          : 'border-info bg-info/60 hover:bg-info'
                      } ${segment.status !== 'complete' ? 'opacity-60' : ''}`}
                      style={segmentTimelineStyle(segment, timeline.start, timeline.end)}
                    />
                  ))}
                </div>
              </div>
            ))}
            <div className="flex flex-wrap items-center gap-3 text-xs text-text-secondary">
              <span className="inline-flex items-center gap-1.5"><span className="h-2.5 w-5 rounded-sm bg-warning" /> Olay</span>
              <span className="inline-flex items-center gap-1.5"><span className="h-2.5 w-5 rounded-sm bg-info" /> Surekli</span>
              <span>Bloklara tiklayarak kaydi oynatin.</span>
            </div>
          </div>
        )}
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

      {preview && (
        <div className="rounded-lg border border-border bg-bg-card">
          <div className="flex items-center justify-between border-b border-border px-4 py-3">
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-text-primary">
                {cameraName(cameraById, preview.segment.camera_id)} - {preview.segment.filename}
              </p>
              <p className="text-xs text-text-secondary">
                {formatDate(preview.segment.started_at)} / {preview.segment.duration_seconds == null ? '-' : `${preview.segment.duration_seconds.toFixed(1)} sn`}
              </p>
            </div>
            <div className="flex shrink-0 flex-wrap items-center justify-end gap-2">
              {previewDetectionOffset !== null && (
                <div className="flex items-center gap-1 rounded-md border border-border bg-bg-secondary p-1" aria-label="Olay ani hizli atlama">
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => seekPreview(Math.max(previewDetectionOffset - 5, 0))}
                    title="Alarm anindan 5 saniye onceye git"
                  >
                    -5 sn
                  </Button>
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => seekPreview(previewDetectionOffset)}
                    title="Alarm anina git"
                  >
                    Alarm ani
                  </Button>
                </div>
              )}
              <div className="flex items-center gap-1 rounded-md border border-border bg-bg-secondary p-1" aria-label="Playback hiz kontrolu">
                <Gauge size={14} className="mx-1 text-text-secondary" />
                {PLAYBACK_SPEED_OPTIONS.map((speed) => (
                  <button
                    key={speed}
                    type="button"
                    aria-label={`Playback hizi ${speed}x`}
                    title={`Playback hizi ${speed}x`}
                    onClick={() => setPlaybackSpeed(speed)}
                    className={`h-7 min-w-9 rounded px-2 text-xs font-semibold transition-colors ${
                      playbackSpeed === speed ? 'bg-accent text-white' : 'text-text-secondary hover:bg-bg-card hover:text-text-primary'
                    }`}
                  >
                    {speed}x
                  </button>
                ))}
              </div>
              <Button
                size="sm"
                variant="secondary"
                icon={<X size={14} />}
                onClick={() => setPreview((current) => {
                  if (current?.url) URL.revokeObjectURL(current.url)
                  return null
                })}
                title="Oynaticiyi kapat"
              >
                Kapat
              </Button>
            </div>
          </div>
          <div ref={previewFrameRef} className="relative aspect-video w-full bg-black">
            <video
              ref={previewVideoRef}
              src={preview.url}
              controls
              className="h-full w-full object-contain"
              aria-label={`${cameraName(cameraById, preview.segment.camera_id)} kayit oynatici`}
            />
            {showHumanDetectionBoxes && (
              <BoundingBoxOverlay
                detections={preview.metadata?.detections ?? []}
                containerWidth={previewDims.w}
                containerHeight={previewDims.h}
                sourceWidth={preview.metadata?.frame_width ?? preview.segment.width}
                sourceHeight={preview.metadata?.frame_height ?? preview.segment.height}
                fit="contain"
              />
            )}
          </div>
          <div className="border-t border-border px-4 py-3">
            <div className="mb-3 grid gap-2 md:grid-cols-4">
              <div className="rounded-md border border-border bg-bg-secondary px-3 py-2">
                <p className="text-[11px] font-semibold uppercase text-text-secondary">Olay Inceleme</p>
                <p className="mt-1 text-sm font-semibold text-text-primary">
                  {preview.segment.alarm_id ? `Alarm #${preview.segment.alarm_id}` : 'Alarm bagi yok'}
                </p>
              </div>
              <div className="rounded-md border border-border bg-bg-secondary px-3 py-2">
                <p className="text-[11px] font-semibold uppercase text-text-secondary">Kutu Sayisi</p>
                <p className="mt-1 text-sm font-semibold text-text-primary">{previewDetections.length}</p>
              </div>
              <div className="rounded-md border border-border bg-bg-secondary px-3 py-2">
                <p className="text-[11px] font-semibold uppercase text-text-secondary">
                  {previewTamper ? 'Sabotaj' : previewMotionPercent !== null ? 'Hareket Orani' : 'En Yuksek Guven'}
                </p>
                <p className="mt-1 text-sm font-semibold text-text-primary">
                  {previewTamper
                    ? previewTamper.reason
                    : previewMotionPercent !== null
                    ? formatPercent(previewMotionPercent)
                    : formatConfidence(previewMaxConfidence)}
                </p>
              </div>
              <div className="rounded-md border border-border bg-bg-secondary px-3 py-2">
                <p className="text-[11px] font-semibold uppercase text-text-secondary">Kanit Hash</p>
                <p className="mt-1 truncate font-mono text-xs text-text-primary" title={preview.segment.file_sha256 ?? undefined}>
                  {preview.segment.file_sha256 ?? '-'}
                </p>
              </div>
            </div>
            <div className="mb-2 flex flex-wrap items-center justify-between gap-2 text-xs text-text-secondary">
              <span>
                Olay penceresi: {preview.segment.duration_seconds == null ? '-' : `${preview.segment.duration_seconds.toFixed(1)} sn`}
              </span>
              {previewTamper && (
                <span>
                  Parlaklik {previewTamper.brightness_mean.toFixed(1)} · Duzluk {previewTamper.brightness_stddev.toFixed(1)} · Bulaniklik {previewTamper.blur_variance.toFixed(1)}
                </span>
              )}
              <span>
                {previewDetectionOffset !== null
                  ? `Alarm ani: ${previewDetectionOffset.toFixed(1)} sn`
                  : 'Alarm ani metadata bulunamadi'}
              </span>
            </div>
            <div className="relative h-3 rounded-full border border-border bg-bg-secondary">
              <div className="absolute inset-y-0 left-0 w-1/3 rounded-l-full bg-info/25" title="Alarm oncesi pencere" />
              <div className="absolute inset-y-0 left-1/3 w-1/3 bg-warning/25" title="Alarm ani cevresi" />
              <div className="absolute inset-y-0 right-0 w-1/3 rounded-r-full bg-success/20" title="Alarm sonrasi pencere" />
              {previewDetectionPercent !== null && (
                <button
                  type="button"
                  aria-label="Alarm ani isaretine git"
                  title="Alarm anina git"
                  onClick={() => seekPreview(previewDetectionOffset ?? 0)}
                  className="absolute top-1/2 h-5 w-1.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-danger shadow-[0_0_0_2px_rgba(0,0,0,0.35)] focus:outline-none focus:ring-2 focus:ring-accent"
                  style={{ left: `${previewDetectionPercent}%` }}
                />
              )}
            </div>
            <div className="mt-2 flex flex-wrap items-center gap-3 text-[11px] text-text-secondary">
              <span className="inline-flex items-center gap-1.5"><span className="h-2 w-4 rounded-sm bg-info/40" /> Oncesi</span>
              <span className="inline-flex items-center gap-1.5"><span className="h-2 w-4 rounded-sm bg-warning/40" /> Olay</span>
              <span className="inline-flex items-center gap-1.5"><span className="h-2 w-4 rounded-sm bg-success/30" /> Sonrasi</span>
            </div>
          </div>
        </div>
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
