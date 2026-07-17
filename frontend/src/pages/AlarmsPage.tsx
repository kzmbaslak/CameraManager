// Alarm yönetimi sayfası — filtreleme (kamera, tip, durum, tarih), listeleme, onaylama
import { useMemo, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { CheckCircle, Filter, RotateCcw } from 'lucide-react'
import { alarmsApi } from '../api/alarms'
import { camerasApi } from '../api/cameras'
import { AlarmRow } from '../components/alarm/AlarmRow'
import { Button } from '../components/ui/Button'
import { Spinner } from '../components/ui/Spinner'
import type { AlarmStatus, AlarmType } from '../types/api'
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
export function AlarmsPage() {
  const [cameraFilter, setCameraFilter] = useState<number | 'all'>('all')
  const [statusFilter, setStatusFilter] = useState<AlarmStatus | 'all'>('all')
  const [typeFilter, setTypeFilter] = useState<AlarmType | 'all'>('all')
  const [dateRange, setDateRange] = useState<DateRange>('all')
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
    onSuccess: () => qc.invalidateQueries({ queryKey: ['alarms'] }),
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
                <th className="px-4 py-3 w-28" />
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
                    acknowledging={acknowledge.isPending && acknowledge.variables === alarm.id}
                  />
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
