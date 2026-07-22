// Alarm yönetimi sayfası — filtreleme (kamera, tip, durum, tarih), listeleme, onaylama
import { useEffect, useMemo, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { CheckCircle, Filter, Play, RotateCcw, X } from 'lucide-react'
import { alarmsApi } from '../api/alarms'
import { camerasApi } from '../api/cameras'
import { AlarmRow } from '../components/alarm/AlarmRow'
import { Button } from '../components/ui/Button'
import { Spinner } from '../components/ui/Spinner'
import { useAlarmStore } from '../stores/alarmStore'
import type { Alarm, AlarmStatus, AlarmType } from '../types/api'
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

/** Belirli bir tarih aralığı başlangıcını döner */
function dateRangeStart(range: DateRange): Date | null {
  if (range === 'all') return null
  if (range === 'today') return dayjs().startOf('day').toDate()
  if (range === '7d') return dayjs().subtract(7, 'day').toDate()
  return dayjs().subtract(30, 'day').toDate()
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
  snapshotLoading,
  onClose,
  onOpenLive,
  onAcknowledge,
  onSave,
  onResolve,
  acknowledging,
  saving,
  resolving,
}: {
  alarm: Alarm
  cameraName?: string
  snapshotUrl: string | null
  snapshotLoading: boolean
  onClose: () => void
  onOpenLive: () => void
  onAcknowledge: () => void
  onSave: (payload: { assigned_to: string | null; operator_note: string | null }) => void
  onResolve: (payload: { resolution_reason: string | null }) => void
  acknowledging: boolean
  saving: boolean
  resolving: boolean
}) {
  const [assignedTo, setAssignedTo] = useState(alarm.assigned_to ?? '')
  const [operatorNote, setOperatorNote] = useState(alarm.operator_note ?? '')
  const [resolutionReason, setResolutionReason] = useState(alarm.resolution_reason ?? '')

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
              <img src={snapshotUrl} alt="Alarm snapshot" className="h-full w-full object-contain" />
            ) : (
              <div className="flex h-full items-center justify-center text-sm text-text-secondary">Snapshot yok</div>
            )}
          </div>

          <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
            <div>
              <dt className="text-xs uppercase tracking-wide text-text-secondary">Tip</dt>
              <dd className="mt-1 text-text-primary">{TYPE_OPTIONS.find((item) => item.value === alarm.alarm_type)?.label ?? alarm.alarm_type}</dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-wide text-text-secondary">Durum</dt>
              <dd className="mt-1 text-text-primary">{STATUS_OPTIONS.find((item) => item.value === alarm.status)?.label ?? alarm.status}</dd>
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
              <Button
                size="sm"
                variant="secondary"
                loading={resolving}
                onClick={() => onResolve({ resolution_reason: resolutionReason.trim() || null })}
              >
                Cozuldu Olarak Kapat
              </Button>
            )}
          </div>
        </div>

        <div className="flex shrink-0 gap-2 border-t border-border p-4">
          <Button variant="secondary" icon={<Play size={14} />} onClick={onOpenLive} className="flex-1">
            Canli Ac
          </Button>
          {alarm.status === 'new' && (
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
  const [cameraFilter, setCameraFilter] = useState<number | 'all'>('all')
  const [statusFilter, setStatusFilter] = useState<AlarmStatus | 'all'>('all')
  const [typeFilter, setTypeFilter] = useState<AlarmType | 'all'>('all')
  const [dateRange, setDateRange] = useState<DateRange>('all')
  const [selectedAlarm, setSelectedAlarm] = useState<Alarm | null>(null)
  const [snapshotUrl, setSnapshotUrl] = useState<string | null>(null)
  const [snapshotLoading, setSnapshotLoading] = useState(false)
  const { setExpandedCamera } = useAlarmStore()
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
    },
  })

  const updateAlarm = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: { assigned_to: string | null; operator_note: string | null } }) =>
      alarmsApi.update(id, payload),
    onSuccess: (alarm) => {
      setSelectedAlarm(alarm)
      qc.invalidateQueries({ queryKey: ['alarms'] })
    },
  })

  const resolveAlarm = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: { resolution_reason: string | null } }) =>
      alarmsApi.resolve(id, payload),
    onSuccess: (alarm) => {
      setSelectedAlarm(alarm)
      qc.invalidateQueries({ queryKey: ['alarms'] })
    },
  })

  const acknowledgeFiltered = useMutation({
    mutationFn: async (ids: number[]) => Promise.all(ids.map((id) => alarmsApi.acknowledge(id))),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['alarms'] }),
  })

  const cameraNameMap = Object.fromEntries(cameras.map((c) => [c.id, c.name]))

  const hasActiveFilter =
    cameraFilter !== 'all' || statusFilter !== 'all' || typeFilter !== 'all' || dateRange !== 'all'
  const filteredNewAlarmIds = filtered.filter((alarm) => alarm.status === 'new').map((alarm) => alarm.id)

  const handleReset = () => {
    setCameraFilter('all')
    setStatusFilter('all')
    setTypeFilter('all')
    setDateRange('all')
  }

  useEffect(() => {
    if (!selectedAlarm?.snapshot_path) {
      setSnapshotUrl(null)
      setSnapshotLoading(false)
      return
    }
    let objectUrl: string | null = null
    let cancelled = false
    setSnapshotLoading(true)
    alarmsApi.snapshot(selectedAlarm.id)
      .then((blob) => {
        if (cancelled) return
        objectUrl = URL.createObjectURL(blob)
        setSnapshotUrl(objectUrl)
      })
      .catch(() => {
        if (!cancelled) setSnapshotUrl(null)
      })
      .finally(() => {
        if (!cancelled) setSnapshotLoading(false)
      })
    return () => {
      cancelled = true
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [selectedAlarm])

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
        {filteredNewAlarmIds.length > 0 && (
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
                    onAcknowledge={(id) => acknowledge.mutate(id)}
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
          alarm={selectedAlarm}
          cameraName={cameraNameMap[selectedAlarm.camera_id]}
          snapshotUrl={snapshotUrl}
          snapshotLoading={snapshotLoading}
          onClose={() => setSelectedAlarm(null)}
          onOpenLive={() => {
            setExpandedCamera(selectedAlarm.camera_id, selectedAlarm.id)
            setSelectedAlarm(null)
          }}
          onAcknowledge={() => acknowledge.mutate(selectedAlarm.id)}
          onSave={(payload) => updateAlarm.mutate({ id: selectedAlarm.id, payload })}
          onResolve={(payload) => resolveAlarm.mutate({ id: selectedAlarm.id, payload })}
          acknowledging={acknowledge.isPending && acknowledge.variables === selectedAlarm.id}
          saving={updateAlarm.isPending && updateAlarm.variables?.id === selectedAlarm.id}
          resolving={resolveAlarm.isPending && resolveAlarm.variables?.id === selectedAlarm.id}
        />
      )}
    </div>
  )
}
