// Alarm yönetimi sayfası — filtreleme (kamera, tip, durum, tarih), listeleme, onaylama
import { useEffect, useMemo, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { CheckCircle, Download, Filter, Play, RotateCcw, X } from 'lucide-react'
import { alarmsApi } from '../api/alarms'
import { camerasApi } from '../api/cameras'
import { AlarmRow } from '../components/alarm/AlarmRow'
import { Button } from '../components/ui/Button'
import { Spinner } from '../components/ui/Spinner'
import { usePermissions } from '../hooks/usePermissions'
import { useAlarmStore } from '../stores/alarmStore'
import { useToastStore } from '../stores/toastStore'
import { getApiErrorMessage } from '../utils/apiError'
import type { Alarm, AlarmSeverity, AlarmStatus, AlarmTrainingFeedbackItem, AlarmType } from '../types/api'
import dayjs from 'dayjs'

// ────────────────────────────────────────────
// Filtre tipleri
// ────────────────────────────────────────────

const STATUS_OPTIONS: { value: AlarmStatus | 'all'; label: string }[] = [
  { value: 'all', label: 'Tüm Durumlar' },
  { value: 'new', label: 'Yeni' },
  { value: 'acknowledged', label: 'Onaylandı' },
  { value: 'resolved', label: 'Çözüldü' },
]

const TYPE_OPTIONS: { value: AlarmType | 'all'; label: string }[] = [
  { value: 'all', label: 'Tüm Tipler' },
  { value: 'human_detected', label: 'İnsan Tespiti' },
  { value: 'motion_detected', label: 'Hareket Tespiti' },
  { value: 'camera_offline', label: 'Kamera Çevrimdışı' },
]

type DateRange = 'today' | '7d' | '30d' | 'all'

const DATE_RANGE_OPTIONS: { value: DateRange; label: string }[] = [
  { value: 'today', label: 'Bugün' },
  { value: '7d', label: 'Son 7 Gün' },
  { value: '30d', label: 'Son 30 Gün' },
  { value: 'all', label: 'Tümü' },
]

const SEVERITY_OPTIONS: { value: AlarmSeverity; label: string }[] = [
  { value: 'low', label: 'Dusuk' },
  { value: 'medium', label: 'Orta' },
  { value: 'high', label: 'Yuksek' },
  { value: 'critical', label: 'Kritik' },
]

/** Belirli bir tarih aralığı başlangıcını döner */
function dateRangeStart(range: DateRange): Date | null {
  if (range === 'all') return null
  if (range === 'today') return dayjs().startOf('day').toDate()
  if (range === '7d') return dayjs().subtract(7, 'day').toDate()
  return dayjs().subtract(30, 'day').toDate()
}

const optionLabel = <T extends string>(options: { value: T | 'all'; label: string }[], value: T) =>
  options.find((item) => item.value === value)?.label ?? value

const severityLabel = (value: AlarmSeverity) =>
  SEVERITY_OPTIONS.find((item) => item.value === value)?.label ?? value

const csvCell = (value: unknown) => {
  const text = value == null ? '' : String(value)
  return `"${text.replace(/"/g, '""')}"`
}

const resolutionMinutes = (alarm: Alarm) => {
  if (!alarm.created_at || !alarm.resolved_at) return null
  const minutes = dayjs(alarm.resolved_at).diff(dayjs(alarm.created_at), 'minute')
  return Number.isFinite(minutes) && minutes >= 0 ? minutes : null
}

function buildAlarmCsv(alarms: Alarm[], cameraNames: Record<number, string>) {
  const headers = [
    'Alarm ID',
    'Kamera',
    'Tip',
    'Durum',
    'Onem',
    'Yanlis Alarm',
    'Guven',
    'Atanan',
    'Operator Notu',
    'Cozum Nedeni',
    'Olusturma',
    'Onaylama',
    'Cozme',
    'Cozum Dk',
    'Snapshot SHA-256',
    'Kutulu Snapshot SHA-256',
  ]
  const rows = alarms.map((alarm) => [
    alarm.id,
    cameraNames[alarm.camera_id] ?? `Kamera #${alarm.camera_id}`,
    optionLabel(TYPE_OPTIONS, alarm.alarm_type),
    alarm.false_positive ? 'Yanlis Alarm' : optionLabel(STATUS_OPTIONS, alarm.status),
    severityLabel(alarm.severity),
    alarm.false_positive ? 'Evet' : 'Hayir',
    alarm.confidence == null ? '' : `${Math.round(alarm.confidence * 100)}%`,
    alarm.assigned_to ?? '',
    alarm.operator_note ?? '',
    alarm.resolution_reason ?? '',
    alarm.created_at ? dayjs(alarm.created_at).format('YYYY-MM-DD HH:mm:ss') : '',
    alarm.acknowledged_at ? dayjs(alarm.acknowledged_at).format('YYYY-MM-DD HH:mm:ss') : '',
    alarm.resolved_at ? dayjs(alarm.resolved_at).format('YYYY-MM-DD HH:mm:ss') : '',
    resolutionMinutes(alarm) ?? '',
    alarm.snapshot_sha256 ?? '',
    alarm.snapshot_annotated_sha256 ?? '',
  ])
  return [headers, ...rows].map((row) => row.map(csvCell).join(',')).join('\r\n')
}

function bboxText(item: AlarmTrainingFeedbackItem) {
  if (!item.bounding_box) return ''
  const { x, y, width, height } = item.bounding_box
  return `${x}:${y}:${width}:${height}`
}

function buildTrainingFeedbackCsv(items: AlarmTrainingFeedbackItem[], cameraNames: Record<number, string>) {
  const headers = [
    'Alarm ID',
    'Kamera',
    'Olusturma',
    'Guven',
    'Bounding Box',
    'Yanlis Alarm',
    'Onem',
    'Operator Notu',
    'Cozum Nedeni',
    'Snapshot SHA-256',
    'Kutulu Snapshot SHA-256',
  ]
  const rows = items.map((item) => [
    item.alarm_id,
    cameraNames[item.camera_id] ?? `Kamera #${item.camera_id}`,
    item.created_at ? dayjs(item.created_at).format('YYYY-MM-DD HH:mm:ss') : '',
    item.confidence == null ? '' : `${Math.round(item.confidence * 100)}%`,
    bboxText(item),
    item.false_positive ? 'Evet' : 'Hayir',
    severityLabel(item.severity),
    item.operator_note ?? '',
    item.resolution_reason ?? '',
    item.snapshot_sha256 ?? '',
    item.snapshot_annotated_sha256 ?? '',
  ])
  return [headers, ...rows].map((row) => row.map(csvCell).join(',')).join('\r\n')
}

// ────────────────────────────────────────────
// Filtre çubuğu alt bileşeni
// ────────────────────────────────────────────

interface FilterBarProps {
  cameras: { id: number; name: string; host: string }[]
  cameraFilter: number | 'all'
  statusFilter: AlarmStatus | 'all'
  typeFilter: AlarmType | 'all'
  dateRange: DateRange
  onCamera: (v: number | 'all') => void
  onStatus: (v: AlarmStatus | 'all') => void
  onType: (v: AlarmType | 'all') => void
  onDate: (v: DateRange) => void
  onReset: () => void
  hasActiveFilter: boolean
}

/** Alarm listeleme filtre satırı */
function FilterBar({
  cameras, cameraFilter, statusFilter, typeFilter, dateRange,
  onCamera, onStatus, onType, onDate, onReset, hasActiveFilter,
}: FilterBarProps) {
  const selectCls = `
    rounded-lg px-3 py-1.5 text-sm border border-border
    bg-bg-card text-text-primary
    focus:outline-none focus:border-accent transition-colors cursor-pointer
  `

  return (
    <div className="flex flex-wrap items-center gap-2">
      <Filter size={14} className="text-text-secondary shrink-0" />

      {/* Kamera filtresi */}
      <select
        value={cameraFilter}
        onChange={(e) => onCamera(e.target.value === 'all' ? 'all' : Number(e.target.value))}
        className={selectCls}
      >
        <option value="all">Tüm Kameralar</option>
        {cameras.map((c) => (
          <option key={c.id} value={c.id}>
            {c.name} ({c.host})
          </option>
        ))}
      </select>

      {/* Durum filtresi */}
      <select value={statusFilter} onChange={(e) => onStatus(e.target.value as AlarmStatus | 'all')} className={selectCls}>
        {STATUS_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>

      {/* Tip filtresi */}
      <select value={typeFilter} onChange={(e) => onType(e.target.value as AlarmType | 'all')} className={selectCls}>
        {TYPE_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>

      {/* Tarih aralığı */}
      <div className="flex items-center gap-1 bg-bg-card border border-border rounded-lg p-1">
        {DATE_RANGE_OPTIONS.map((o) => (
          <button
            key={o.value}
            onClick={() => onDate(o.value)}
            className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
              dateRange === o.value
                ? 'bg-accent text-white'
                : 'text-text-secondary hover:text-text-primary'
            }`}
          >
            {o.label}
          </button>
        ))}
      </div>

      {/* Filtreleri sıfırla */}
      {hasActiveFilter && (
        <button
          onClick={onReset}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-text-secondary hover:text-danger hover:bg-danger/10 transition-colors"
        >
          <RotateCcw size={12} />
          Sıfırla
        </button>
      )}
    </div>
  )
}

// ────────────────────────────────────────────
// Ana sayfa
// ────────────────────────────────────────────

/** Alarm geçmişi sayfası — kamera/tip/durum/tarih filtreli, onaylama destekli */
function AlarmDetailDrawer({
  alarm,
  cameraName,
  snapshotUrl,
  snapshotSha256,
  rawSnapshotUrl,
  rawSnapshotSha256,
  snapshotLoading,
  canOperateAlarms,
  canExportEvidence,
  onClose,
  onOpenLive,
  onAcknowledge,
  onSave,
  onResolve,
  onFalsePositive,
  acknowledging,
  saving,
  resolving,
  falsePositiveSaving,
}: {
  alarm: Alarm
  cameraName?: string
  snapshotUrl: string | null
  snapshotSha256: string | null
  rawSnapshotUrl: string | null
  rawSnapshotSha256: string | null
  snapshotLoading: boolean
  canOperateAlarms: boolean
  canExportEvidence: boolean
  onClose: () => void
  onOpenLive: () => void
  onAcknowledge: () => void
  onSave: (payload: { assigned_to: string | null; operator_note: string | null; severity: AlarmSeverity }) => void
  onResolve: (payload: { resolution_reason: string | null; false_positive?: boolean }) => void
  onFalsePositive: () => void
  acknowledging: boolean
  saving: boolean
  resolving: boolean
  falsePositiveSaving: boolean
}) {
  const [assignedTo, setAssignedTo] = useState(alarm.assigned_to ?? '')
  const [operatorNote, setOperatorNote] = useState(alarm.operator_note ?? '')
  const [resolutionReason, setResolutionReason] = useState(alarm.resolution_reason ?? '')
  const [severity, setSeverity] = useState<AlarmSeverity>(alarm.severity)
  const snapshotFilename = alarm.snapshot_annotated_path ? `alarm-${alarm.id}-kutulu-kanit.jpg` : `alarm-${alarm.id}-snapshot.jpg`
  const rawSnapshotFilename = `alarm-${alarm.id}-ham-kanit.jpg`

  function handleDownloadSnapshot() {
    if (!snapshotUrl) return
    const link = document.createElement('a')
    link.href = snapshotUrl
    link.download = snapshotFilename
    document.body.appendChild(link)
    link.click()
    link.remove()
  }

  function handleDownloadRawSnapshot() {
    if (!rawSnapshotUrl) return
    const link = document.createElement('a')
    link.href = rawSnapshotUrl
    link.download = rawSnapshotFilename
    document.body.appendChild(link)
    link.click()
    link.remove()
  }

  return (
    <div className="fixed inset-0 z-[160] flex justify-end bg-black/35">
      <button className="flex-1" aria-label="Alarm detay panelini kapat" onClick={onClose} />
      <aside className="flex h-full w-full max-w-md flex-col border-l border-border bg-bg-card shadow-2xl">
        <div className="flex items-center justify-between border-b border-border px-4 py-3">
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-text-primary">{cameraName ?? `Kamera #${alarm.camera_id}`}</p>
            <p className="text-xs text-text-secondary">Alarm #{alarm.id}</p>
          </div>
          <button
            type="button"
            aria-label="Alarm detay panelini kapat"
            onClick={onClose}
            className="rounded-md p-1.5 text-text-secondary transition-colors hover:bg-bg-secondary hover:text-text-primary"
          >
            <X size={18} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-4">
          <div className="aspect-video overflow-hidden rounded-md border border-border bg-bg-primary">
            {snapshotLoading ? (
              <div className="flex h-full items-center justify-center"><Spinner size="sm" /></div>
            ) : snapshotUrl ? (
              <img src={snapshotUrl} alt="Alarm kanit snapshot" className="h-full w-full object-contain" />
            ) : (
              <div className="flex h-full items-center justify-center text-sm text-text-secondary">Snapshot yok</div>
            )}
          </div>

          <div className="mt-2 flex items-center justify-between gap-2">
            <div className="min-w-0 text-xs text-text-secondary">
              <p>{snapshotUrl ? snapshotFilename : 'Indirilebilir kanit snapshot bulunmuyor.'}</p>
              {snapshotSha256 && (
                <p className="mt-0.5 truncate font-mono" title={snapshotSha256}>
                  SHA-256: {snapshotSha256}
                </p>
              )}
              {rawSnapshotSha256 && rawSnapshotSha256 !== snapshotSha256 && (
                <p className="mt-0.5 truncate font-mono" title={rawSnapshotSha256}>
                  Ham SHA-256: {rawSnapshotSha256}
                </p>
              )}
            </div>
            {canExportEvidence && (
              <div className="flex shrink-0 flex-col gap-2">
                <Button
                  size="sm"
                  variant="secondary"
                  icon={<Download size={14} />}
                  disabled={!snapshotUrl || snapshotLoading}
                  onClick={handleDownloadSnapshot}
                >
                  Kaniti Indir
                </Button>
                {rawSnapshotUrl && rawSnapshotUrl !== snapshotUrl && (
                  <Button
                    size="sm"
                    variant="ghost"
                    icon={<Download size={14} />}
                    disabled={snapshotLoading}
                    onClick={handleDownloadRawSnapshot}
                  >
                    Ham Kanit
                  </Button>
                )}
              </div>
            )}
          </div>

          <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
            <div>
              <dt className="text-xs uppercase tracking-wide text-text-secondary">Tip</dt>
              <dd className="mt-1 text-text-primary">{TYPE_OPTIONS.find((item) => item.value === alarm.alarm_type)?.label ?? alarm.alarm_type}</dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-wide text-text-secondary">Durum</dt>
              <dd className="mt-1 text-text-primary">{alarm.false_positive ? 'Yanlis Alarm' : STATUS_OPTIONS.find((item) => item.value === alarm.status)?.label ?? alarm.status}</dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-wide text-text-secondary">Guven</dt>
              <dd className="mt-1 text-text-primary">{alarm.confidence != null ? `%${Math.round(alarm.confidence * 100)}` : '-'}</dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-wide text-text-secondary">Zaman</dt>
              <dd className="mt-1 text-text-primary">{alarm.created_at ? dayjs(alarm.created_at).format('DD.MM.YYYY HH:mm:ss') : '-'}</dd>
            </div>
          </dl>

          {alarm.message && (
            <p className="mt-4 rounded-md border border-border bg-bg-secondary px-3 py-2 text-sm text-text-secondary">
              {alarm.message}
            </p>
          )}

          {canOperateAlarms && (
            <>
              <div className="mt-4 flex flex-col gap-3 rounded-md border border-border bg-bg-secondary p-3">
                <p className="text-xs font-semibold uppercase tracking-wide text-text-secondary">Operasyon</p>
                <label className="flex flex-col gap-1 text-sm text-text-primary">
                  Atanan kisi
                  <input
                    value={assignedTo}
                    onChange={(e) => setAssignedTo(e.target.value)}
                    placeholder="Operator veya ekip"
                    className="rounded-md border border-border bg-bg-card px-3 py-2 text-sm text-text-primary outline-none focus:border-accent"
                  />
                </label>
                <label className="flex flex-col gap-1 text-sm text-text-primary">
                  Onem seviyesi
                  <select
                    value={severity}
                    onChange={(e) => setSeverity(e.target.value as AlarmSeverity)}
                    className="rounded-md border border-border bg-bg-card px-3 py-2 text-sm text-text-primary outline-none focus:border-accent"
                  >
                    {SEVERITY_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>{option.label}</option>
                    ))}
                  </select>
                </label>
                <label className="flex flex-col gap-1 text-sm text-text-primary">
                  Operator notu
                  <textarea
                    value={operatorNote}
                    onChange={(e) => setOperatorNote(e.target.value)}
                    placeholder="Olay inceleme notu"
                    className="min-h-24 rounded-md border border-border bg-bg-card px-3 py-2 text-sm text-text-primary outline-none focus:border-accent"
                  />
                </label>
                <Button
                  size="sm"
                  variant="secondary"
                  loading={saving}
                  onClick={() => onSave({
                    assigned_to: assignedTo.trim() || null,
                    operator_note: operatorNote.trim() || null,
                    severity,
                  })}
                >
                  Notu Kaydet
                </Button>
              </div>

              <div className="mt-3 flex flex-col gap-2 rounded-md border border-border bg-bg-secondary p-3">
                <label className="flex flex-col gap-1 text-sm text-text-primary">
                  Cozum nedeni
                  <input
                    value={resolutionReason}
                    onChange={(e) => setResolutionReason(e.target.value)}
                    placeholder="Gercek alarm, yanlis alarm, test, vb."
                    className="rounded-md border border-border bg-bg-card px-3 py-2 text-sm text-text-primary outline-none focus:border-accent"
                  />
                </label>
                {alarm.status !== 'resolved' && (
                  <div className="grid grid-cols-2 gap-2">
                    <Button
                      size="sm"
                      variant="secondary"
                      loading={resolving}
                      onClick={() => onResolve({ resolution_reason: resolutionReason.trim() || null })}
                    >
                      Kapat
                    </Button>
                    <Button
                      size="sm"
                      variant="danger"
                      loading={falsePositiveSaving}
                      onClick={onFalsePositive}
                    >
                      Yanlis Alarm
                    </Button>
                  </div>
                )}
              </div>
            </>
          )}
        </div>

        <div className="flex shrink-0 gap-2 border-t border-border p-4">
          <Button variant="secondary" icon={<Play size={14} />} onClick={onOpenLive} className="flex-1">
            Canli Ac
          </Button>
          {canOperateAlarms && alarm.status === 'new' && (
            <Button variant="danger" icon={<CheckCircle size={14} />} loading={acknowledging} onClick={onAcknowledge} className="flex-1">
              Onayla
            </Button>
          )}
        </div>
      </aside>
    </div>
  )
}

export function AlarmsPage() {
  const { canAcknowledgeAlarms, canOperateAlarms, canExportEvidence } = usePermissions()
  const [cameraFilter, setCameraFilter] = useState<number | 'all'>('all')
  const [statusFilter, setStatusFilter] = useState<AlarmStatus | 'all'>('all')
  const [typeFilter, setTypeFilter] = useState<AlarmType | 'all'>('all')
  const [dateRange, setDateRange] = useState<DateRange>('all')
  const [selectedAlarm, setSelectedAlarm] = useState<Alarm | null>(null)
  const { setExpandedCamera } = useAlarmStore()
  const showToast = useToastStore((state) => state.showToast)
  const qc = useQueryClient()

  const { data: cameras = [] } = useQuery({
    queryKey: ['cameras'],
    queryFn: camerasApi.list,
  })

  // Backend'e sadece desteklenen filtreleri gönder; tarih client-side filtrelenir
  const queryParams = useMemo(() => ({
    camera_id: cameraFilter !== 'all' ? cameraFilter : undefined,
    alarm_type: typeFilter !== 'all' ? typeFilter : undefined,
    status: statusFilter !== 'all' ? statusFilter : undefined,
    limit: 300,
  }), [cameraFilter, typeFilter, statusFilter])

  const { data: alarms = [], isLoading } = useQuery({
    queryKey: ['alarms', queryParams],
    queryFn: () => alarmsApi.listAll(queryParams),
    refetchInterval: 15_000,
  })

  const selectedSnapshotAlarmId = selectedAlarm?.snapshot_path || selectedAlarm?.snapshot_annotated_path ? selectedAlarm.id : null
  const selectedSnapshotVariant = selectedAlarm?.snapshot_annotated_path ? 'annotated' : 'raw'
  const { data: snapshotData, isFetching: snapshotLoading } = useQuery({
    queryKey: ['alarm-snapshot', selectedSnapshotAlarmId, selectedSnapshotVariant],
    queryFn: () => alarmsApi.snapshot(selectedSnapshotAlarmId as number, selectedSnapshotVariant),
    enabled: selectedSnapshotAlarmId !== null,
  })
  const selectedRawSnapshotAlarmId = selectedAlarm?.snapshot_annotated_path && selectedAlarm.snapshot_path ? selectedAlarm.id : null
  const { data: rawSnapshotData } = useQuery({
    queryKey: ['alarm-snapshot', selectedRawSnapshotAlarmId, 'raw'],
    queryFn: () => alarmsApi.snapshot(selectedRawSnapshotAlarmId as number, 'raw'),
    enabled: selectedRawSnapshotAlarmId !== null,
  })
  const snapshotUrl = useMemo(
    () => (snapshotData?.blob ? URL.createObjectURL(snapshotData.blob) : null),
    [snapshotData],
  )
  const rawSnapshotUrl = useMemo(
    () => (rawSnapshotData?.blob ? URL.createObjectURL(rawSnapshotData.blob) : null),
    [rawSnapshotData],
  )
  const snapshotSha256 = snapshotData?.sha256
    ?? selectedAlarm?.snapshot_annotated_sha256
    ?? selectedAlarm?.snapshot_sha256
    ?? null
  const rawSnapshotSha256 = rawSnapshotData?.sha256 ?? selectedAlarm?.snapshot_sha256 ?? null

  useEffect(() => {
    return () => {
      if (snapshotUrl) URL.revokeObjectURL(snapshotUrl)
    }
  }, [snapshotUrl])

  useEffect(() => {
    return () => {
      if (rawSnapshotUrl) URL.revokeObjectURL(rawSnapshotUrl)
    }
  }, [rawSnapshotUrl])

  // Tarih filtresi client-side
  const filtered = useMemo(() => {
    const since = dateRangeStart(dateRange)
    if (!since) return alarms
    return alarms.filter((a) => a.created_at && new Date(a.created_at) >= since)
  }, [alarms, dateRange])

  const acknowledge = useMutation({
    mutationFn: alarmsApi.acknowledge,
    onSuccess: (alarm) => {
      setSelectedAlarm((current) => current?.id === alarm.id ? alarm : current)
      qc.invalidateQueries({ queryKey: ['alarms'] })
      showToast({ variant: 'success', title: 'Alarm onaylandi', description: `Alarm #${alarm.id}` })
    },
    onError: (err) => showToast({ variant: 'danger', title: 'Alarm onaylanamadi', description: getApiErrorMessage(err, 'Alarm onaylama islemi tamamlanamadi.') }),
  })

  const updateAlarm = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: { assigned_to: string | null; operator_note: string | null; severity: AlarmSeverity } }) =>
      alarmsApi.update(id, payload),
    onSuccess: (alarm) => {
      setSelectedAlarm(alarm)
      qc.invalidateQueries({ queryKey: ['alarms'] })
      showToast({ variant: 'success', title: 'Alarm notu kaydedildi', description: `Alarm #${alarm.id}` })
    },
    onError: (err) => showToast({ variant: 'danger', title: 'Alarm guncellenemedi', description: getApiErrorMessage(err, 'Not veya atama kaydedilemedi.') }),
  })

  const resolveAlarm = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: { resolution_reason: string | null; false_positive?: boolean } }) =>
      alarmsApi.resolve(id, payload),
    onSuccess: (alarm) => {
      setSelectedAlarm(alarm)
      qc.invalidateQueries({ queryKey: ['alarms'] })
      showToast({ variant: 'success', title: 'Alarm kapatildi', description: `Alarm #${alarm.id}` })
    },
    onError: (err) => showToast({ variant: 'danger', title: 'Alarm kapatilamadi', description: getApiErrorMessage(err, 'Cozum islemi tamamlanamadi.') }),
  })

  const falsePositiveAlarm = useMutation({
    mutationFn: alarmsApi.markFalsePositive,
    onSuccess: (alarm) => {
      setSelectedAlarm(alarm)
      qc.invalidateQueries({ queryKey: ['alarms'] })
      showToast({ variant: 'success', title: 'Yanlis alarm olarak kapatildi', description: `Alarm #${alarm.id}` })
    },
    onError: (err) => showToast({ variant: 'danger', title: 'Yanlis alarm isaretlenemedi', description: getApiErrorMessage(err, 'Yanlis alarm islemi tamamlanamadi.') }),
  })

  const acknowledgeFiltered = useMutation({
    mutationFn: async (ids: number[]) => Promise.all(ids.map((id) => alarmsApi.acknowledge(id))),
    onSuccess: (items) => {
      qc.invalidateQueries({ queryKey: ['alarms'] })
      showToast({ variant: 'success', title: 'Alarmlar onaylandi', description: `${items.length} alarm onaylandi.` })
    },
    onError: (err) => showToast({ variant: 'danger', title: 'Alarmlar onaylanamadi', description: getApiErrorMessage(err, 'Toplu onay islemi tamamlanamadi.') }),
  })

  const trainingFeedbackExport = useMutation({
    mutationFn: () => alarmsApi.trainingFeedback({ limit: 5000, false_positive_only: true }),
  })

  const cameraNameMap = Object.fromEntries(cameras.map((c) => [c.id, c.name]))

  const hasActiveFilter =
    cameraFilter !== 'all' || statusFilter !== 'all' || typeFilter !== 'all' || dateRange !== 'all'
  const filteredNewAlarmIds = filtered.filter((alarm) => alarm.status === 'new').map((alarm) => alarm.id)
  const filteredHighPriority = filtered.filter((alarm) => alarm.severity === 'high' || alarm.severity === 'critical').length
  const filteredFalsePositive = filtered.filter((alarm) => alarm.false_positive).length
  const filteredHumanDetections = filtered.filter((alarm) => alarm.alarm_type === 'human_detected').length
  const falsePositiveRate = filteredHumanDetections > 0
    ? Math.round((filteredFalsePositive / filteredHumanDetections) * 100)
    : 0
  const resolutionSamples = filtered
    .map(resolutionMinutes)
    .filter((value): value is number => value !== null)
  const averageResolutionMinutes = resolutionSamples.length > 0
    ? Math.round(resolutionSamples.reduce((sum, value) => sum + value, 0) / resolutionSamples.length)
    : null

  const handleReset = () => {
    setCameraFilter('all')
    setStatusFilter('all')
    setTypeFilter('all')
    setDateRange('all')
  }

  const handleExportCsv = () => {
    const csv = buildAlarmCsv(filtered, cameraNameMap)
    const blob = new Blob([`\uFEFF${csv}`], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `alarm-raporu-${dayjs().format('YYYYMMDD-HHmmss')}.csv`
    document.body.appendChild(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(url)
  }

  const handleExportTrainingFeedback = async () => {
    try {
      const items = await trainingFeedbackExport.mutateAsync()
      if (items.length === 0) {
        showToast({ variant: 'info', title: 'Geri bildirim verisi yok', description: 'Yanlis alarm olarak kapatilmis insan tespiti bulunamadi.' })
        return
      }
      const csv = buildTrainingFeedbackCsv(items, cameraNameMap)
      const blob = new Blob([`\uFEFF${csv}`], { type: 'text/csv;charset=utf-8' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `ai-geri-bildirim-${dayjs().format('YYYYMMDD-HHmmss')}.csv`
      document.body.appendChild(link)
      link.click()
      link.remove()
      URL.revokeObjectURL(url)
      showToast({ variant: 'success', title: 'AI geri bildirimi indirildi', description: `${items.length} yanlis alarm ornegi CSV olarak hazirlandi.` })
    } catch (err) {
      showToast({ variant: 'danger', title: 'AI geri bildirimi alinamadi', description: getApiErrorMessage(err, 'Geri bildirim verisi indirilemedi.') })
    }
  }

  return (
    <div className="p-6 flex flex-col gap-5">
      {/* Başlık */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-text-primary">Alarmlar</h1>
          <p className="text-sm text-text-secondary mt-0.5">
            {filtered.length} kayıt
            {hasActiveFilter && <span className="text-accent ml-1">· Filtre aktif</span>}
          </p>
        </div>
        <div className="flex flex-wrap justify-end gap-2">
          {canExportEvidence && (
            <Button
              size="sm"
              variant="secondary"
              icon={<Download size={14} />}
              disabled={filtered.length === 0}
              onClick={handleExportCsv}
            >
              CSV Rapor
            </Button>
          )}
          {canExportEvidence && (
            <Button
              size="sm"
              variant="secondary"
              icon={<Download size={14} />}
              loading={trainingFeedbackExport.isPending}
              onClick={handleExportTrainingFeedback}
            >
              AI Geri Bildirim
            </Button>
          )}
          {canAcknowledgeAlarms && filteredNewAlarmIds.length > 0 && (
            <Button
              size="sm"
              variant="danger"
              icon={<CheckCircle size={14} />}
              loading={acknowledgeFiltered.isPending}
              onClick={() => acknowledgeFiltered.mutate(filteredNewAlarmIds)}
            >
              Görünen Yeni Alarmları Onayla ({filteredNewAlarmIds.length})
            </Button>
          )}
        </div>
      </div>

      {/* Filtre çubuğu */}
      <FilterBar
        cameras={cameras}
        cameraFilter={cameraFilter}
        statusFilter={statusFilter}
        typeFilter={typeFilter}
        dateRange={dateRange}
        onCamera={setCameraFilter}
        onStatus={setStatusFilter}
        onType={setTypeFilter}
        onDate={setDateRange}
        onReset={handleReset}
        hasActiveFilter={hasActiveFilter}
      />

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <div className="rounded-md border border-border bg-bg-card px-4 py-3">
          <p className="text-xs uppercase tracking-wide text-text-secondary">Açık Alarm</p>
          <p className="mt-1 text-2xl font-semibold text-text-primary">{filteredNewAlarmIds.length}</p>
        </div>
        <div className="rounded-md border border-border bg-bg-card px-4 py-3">
          <p className="text-xs uppercase tracking-wide text-text-secondary">Yüksek Öncelik</p>
          <p className="mt-1 text-2xl font-semibold text-danger">{filteredHighPriority}</p>
        </div>
        <div className="rounded-md border border-border bg-bg-card px-4 py-3">
          <p className="text-xs uppercase tracking-wide text-text-secondary">Yanlış Alarm Oranı</p>
          <p className="mt-1 text-2xl font-semibold text-warning">{falsePositiveRate}%</p>
        </div>
        <div className="rounded-md border border-border bg-bg-card px-4 py-3">
          <p className="text-xs uppercase tracking-wide text-text-secondary">Ort. Çözüm</p>
          <p className="mt-1 text-2xl font-semibold text-text-primary">
            {averageResolutionMinutes == null ? '-' : `${averageResolutionMinutes} dk`}
          </p>
        </div>
      </div>

      {/* Tablo */}
      {isLoading ? (
        <div className="flex justify-center py-16"><Spinner size="lg" /></div>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-border">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-bg-secondary">
                <th className="px-4 py-3 text-left text-xs font-medium text-text-secondary uppercase tracking-wide">Kamera</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-text-secondary uppercase tracking-wide">Tip</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-text-secondary uppercase tracking-wide">Durum</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-text-secondary uppercase tracking-wide">Güven</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-text-secondary uppercase tracking-wide">Zaman</th>
                <th className="px-4 py-3 w-48" />
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-12 text-center">
                    <p className="text-text-secondary">
                      {hasActiveFilter ? 'Filtrelerle eşleşen alarm bulunamadı.' : 'Henüz alarm kaydı yok.'}
                    </p>
                    {hasActiveFilter && (
                      <Button size="sm" variant="secondary" onClick={handleReset} className="mt-3">
                        Filtreleri Sıfırla
                      </Button>
                    )}
                  </td>
                </tr>
              ) : (
                filtered.map((alarm) => (
                  <AlarmRow
                    key={alarm.id}
                    alarm={alarm}
                    cameraName={cameraNameMap[alarm.camera_id]}
                    onAcknowledge={canAcknowledgeAlarms ? (id) => acknowledge.mutate(id) : undefined}
                    onInspect={setSelectedAlarm}
                    acknowledging={acknowledge.isPending && acknowledge.variables === alarm.id}
                  />
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
      {selectedAlarm && (
        <AlarmDetailDrawer
          key={selectedAlarm.id}
          alarm={selectedAlarm}
          cameraName={cameraNameMap[selectedAlarm.camera_id]}
          snapshotUrl={snapshotUrl}
          snapshotSha256={snapshotSha256}
          rawSnapshotUrl={rawSnapshotUrl}
          rawSnapshotSha256={rawSnapshotSha256}
          snapshotLoading={snapshotLoading}
          canOperateAlarms={canOperateAlarms}
          canExportEvidence={canExportEvidence}
          onClose={() => setSelectedAlarm(null)}
          onOpenLive={() => {
            setExpandedCamera(selectedAlarm.camera_id, selectedAlarm.id)
            setSelectedAlarm(null)
          }}
          onAcknowledge={() => acknowledge.mutate(selectedAlarm.id)}
          onSave={(payload) => updateAlarm.mutate({ id: selectedAlarm.id, payload })}
          onResolve={(payload) => resolveAlarm.mutate({ id: selectedAlarm.id, payload })}
          onFalsePositive={() => falsePositiveAlarm.mutate(selectedAlarm.id)}
          acknowledging={acknowledge.isPending && acknowledge.variables === selectedAlarm.id}
          saving={updateAlarm.isPending && updateAlarm.variables?.id === selectedAlarm.id}
          resolving={resolveAlarm.isPending && resolveAlarm.variables?.id === selectedAlarm.id}
          falsePositiveSaving={falsePositiveAlarm.isPending && falsePositiveAlarm.variables === selectedAlarm.id}
        />
      )}
    </div>
  )
}
