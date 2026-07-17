// Dashboard — canlı kamera izleme, grid boyutu seçimi, alarm sayacı, kamera durum özeti, kamera izleme paneli
import { useState, useEffect, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Bell, Wifi, WifiOff, Video, PanelRight, X, Check, CheckCircle, VolumeX } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { camerasApi } from '../api/cameras'
import { alarmsApi } from '../api/alarms'
import { CameraGrid, type GridCols } from '../components/camera/CameraGrid'
import { GridSizeSelector } from '../components/camera/GridSizeSelector'
import { Spinner } from '../components/ui/Spinner'
import { useAlarmStore } from '../stores/alarmStore'
import type { Alarm, Camera } from '../types/api'

/** localStorage'dan grid tercihini okur; yoksa 2×2 kullanır */
function loadGridPref(): GridCols {
  try {
    const v = localStorage.getItem('dashboard-grid')
    if (v === '1' || v === '2' || v === '3' || v === '4') return Number(v) as GridCols
  } catch {
    // localStorage kapalıysa varsayılan grid kullanılır.
  }
  return 2
}

// ─────────────────────────────────────────────
// Kamera durum özet kartı
// ─────────────────────────────────────────────

interface StatusCardProps {
  icon: React.ReactNode
  label: string
  count: number
  color: string
  cameras: Camera[]
}

/** Çevrimiçi/çevrimdışı/hata durum kartı — üzerine gelinince kamera listesi gösterir */
function StatusCard({ icon, label, count, color, cameras }: StatusCardProps) {
  const [open, setOpen] = useState(false)

  return (
    <div className="relative">
      <button
        onClick={() => count > 0 && setOpen((v) => !v)}
        className={`flex items-center gap-3 px-4 py-3 bg-[var(--bg-card)] border rounded-xl transition-colors w-full text-left ${
          count > 0 ? 'hover:border-[var(--accent)]/50 cursor-pointer' : 'cursor-default'
        } border-[var(--border)]`}
      >
        <span className={color}>{icon}</span>
        <div>
          <p className="text-2xl font-bold text-[var(--text-primary)] leading-none">{count}</p>
          <p className="text-xs text-[var(--text-secondary)] mt-0.5">{label}</p>
        </div>
      </button>

      {/* Açılır kamera listesi */}
      {open && cameras.length > 0 && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute top-full left-0 mt-1.5 z-20 min-w-[200px] bg-[var(--bg-card)] border border-[var(--border)] rounded-xl shadow-xl overflow-hidden">
            <p className="px-3 py-2 text-xs font-semibold text-[var(--text-secondary)] uppercase tracking-wide border-b border-[var(--border)]">
              {label}
            </p>
            <ul className="max-h-48 overflow-y-auto">
              {cameras.map((c) => (
                <li key={c.id} className="flex items-center gap-2 px-3 py-2 hover:bg-[var(--bg-secondary)] transition-colors">
                  <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${color}`} style={{ background: 'currentColor' }} />
                  <span className="text-sm text-[var(--text-primary)]">{c.name}</span>
                  <span className="text-xs text-[var(--text-secondary)] font-mono ml-auto">{c.host}</span>
                </li>
              ))}
            </ul>
          </div>
        </>
      )}
    </div>
  )
}

// ─────────────────────────────────────────────
// Kamera izleme paneli (sağdan kayar)
// İşaretli (tick) = kamera izleniyor (status active/error); işaretsiz = izleme kapalı (inactive).
// Tıklama, kameranın gerçek izleme durumunu (DB) anında değiştirir.
// ─────────────────────────────────────────────

const statusDotColor: Record<string, string> = {
  active: 'bg-[var(--success)]',
  error: 'bg-[var(--danger)]',
  inactive: 'bg-[var(--text-secondary)]/40',
}

const statusLabel: Record<string, string> = {
  active: 'Çevrimiçi',
  error: 'Çevrimdışı',
  inactive: 'İzleme Kapalı',
}

interface CameraPanelProps {
  cameras: Camera[]
  pendingId: number | null
  onToggle: (camera: Camera) => void
  onClose: () => void
}

function CameraPanel({ cameras, pendingId, onToggle, onClose }: CameraPanelProps) {
  const panelRef = useRef<HTMLDivElement>(null)
  const watchedCount = cameras.filter((c) => c.status !== 'inactive').length

  // Dışarı tıklayınca kapat
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        onClose()
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [onClose])

  return (
    <motion.div
      ref={panelRef}
      initial={{ x: '100%', opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: '100%', opacity: 0 }}
      transition={{ type: 'spring', stiffness: 300, damping: 30 }}
      className="absolute top-0 right-0 h-full w-72 bg-[var(--bg-card)] border-l border-[var(--border)] shadow-2xl z-30 flex flex-col"
    >
      {/* Panel başlık */}
      <div className="flex items-center justify-between px-4 py-3.5 border-b border-[var(--border)] shrink-0">
        <div>
          <p className="text-sm font-semibold text-[var(--text-primary)]">Kamera İzleme</p>
          <p className="text-xs text-[var(--text-secondary)] mt-0.5">
            {watchedCount} / {cameras.length} kamera izleniyor
          </p>
        </div>
        <button
          onClick={onClose}
          className="p-1.5 rounded-lg hover:bg-[var(--bg-secondary)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
        >
          <X size={16} />
        </button>
      </div>

      {/* Kamera listesi */}
      <ul className="flex-1 overflow-y-auto py-2">
        {cameras.length === 0 && (
          <li className="px-4 py-8 text-center text-sm text-[var(--text-secondary)]">
            Kamera bulunamadı.
          </li>
        )}
        {cameras.map((cam) => {
          const isWatched = cam.status !== 'inactive'
          const isPending = pendingId === cam.id
          return (
            <li key={cam.id}>
              <button
                onClick={() => !isPending && onToggle(cam)}
                disabled={isPending}
                title={isWatched ? 'İzlemeyi kapatmak için tıkla' : 'İzlemeye almak için tıkla'}
                className={`w-full flex items-center gap-3 px-4 py-2.5 transition-colors text-left ${
                  isWatched
                    ? 'bg-[var(--accent)]/10 hover:bg-[var(--accent)]/15'
                    : 'hover:bg-[var(--bg-secondary)]'
                } ${isPending ? 'opacity-50 cursor-wait' : ''}`}
              >
                {/* Tick kutusu — işaretliyse kamera izleniyor demektir */}
                <div
                  className={`w-4 h-4 rounded shrink-0 flex items-center justify-center border transition-colors ${
                    isWatched
                      ? 'bg-[var(--accent)] border-[var(--accent)]'
                      : 'border-[var(--border)] bg-transparent'
                  }`}
                >
                  {isWatched && <Check size={10} className="text-white" strokeWidth={3} />}
                </div>

                {/* Bağlantı durum noktası */}
                <span className={`w-2 h-2 rounded-full shrink-0 ${statusDotColor[cam.status] ?? 'bg-[var(--border)]'}`} />

                {/* Kamera bilgisi */}
                <div className="min-w-0 flex-1">
                  <p className="text-sm text-[var(--text-primary)] truncate leading-tight">{cam.name}</p>
                  <p className="text-xs text-[var(--text-secondary)] font-mono">{cam.host}</p>
                </div>

                {/* Durum etiketi */}
                <span className={`text-xs shrink-0 ${
                  cam.status === 'active' ? 'text-[var(--success)]' :
                  cam.status === 'error' ? 'text-[var(--danger)]' :
                  'text-[var(--text-secondary)]'
                }`}>
                  {statusLabel[cam.status] ?? cam.status}
                </span>
              </button>
            </li>
          )
        })}
      </ul>

      {/* Alt bilgi */}
      <div className="px-4 py-3 border-t border-[var(--border)] shrink-0">
        <p className="text-xs text-[var(--text-secondary)]">
          İşaretlemek kamerayı <span className="font-medium text-[var(--text-primary)]">izlemeye alır</span>;
          işareti kaldırmak izlemeyi durdurur.
        </p>
      </div>
    </motion.div>
  )
}

// ─────────────────────────────────────────────
// Ana sayfa
// ─────────────────────────────────────────────

/** Dashboard sayfası — izlenen (active) kameraları seçilen grid düzeninde gösterir */
export function DashboardPage() {
  const [cols, setCols] = useState<GridCols>(loadGridPref)
  const [panelOpen, setPanelOpen] = useState(false)
  const qc = useQueryClient()
  const { stopSound, muteSoundFor } = useAlarmStore()

  /** Grid değişince localStorage'a kaydet */
  const handleColsChange = (next: GridCols) => {
    setCols(next)
    try {
      localStorage.setItem('dashboard-grid', String(next))
    } catch {
      // localStorage kapalıysa sadece oturum içi seçim korunur.
    }
  }

  const { data: cameras = [], isLoading } = useQuery({
    queryKey: ['cameras'],
    queryFn: camerasApi.list,
    refetchInterval: 10_000,   // backend health-check döngüsüyle (10s) eşgüdümlü
  })

  // Yeni alarmları 10 saniyede bir getir
  const { data: newAlarms = [] } = useQuery({
    queryKey: ['alarms', 'new'],
    queryFn: () => alarmsApi.listByStatus('new', 50),
    refetchInterval: 10_000,
  })

  /** Panelden tek tıkla izlemeyi aç/kapat — DB'deki gerçek durumu değiştirir */
  const toggleWatch = useMutation({
    mutationFn: ({ id, nextStatus }: { id: number; nextStatus: 'active' | 'inactive' }) =>
      camerasApi.updateStatus(id, nextStatus),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['cameras'] }),
  })

  const acknowledgeAllAlarms = useMutation({
    mutationFn: async (ids: number[]) => Promise.all(ids.map((id) => alarmsApi.acknowledge(id))),
    onSuccess: () => {
      stopSound()
      void qc.invalidateQueries({ queryKey: ['alarms'] })
    },
  })

  // kamera id → son alarm eşlemesi
  const alarmMap = newAlarms.reduce<Record<number, Alarm>>((acc, alarm) => {
    if (!acc[alarm.camera_id]) acc[alarm.camera_id] = alarm
    return acc
  }, {})

  // Kamera durum grupları
  const activeCameras = cameras.filter((c) => c.status === 'active')
  const offlineCameras = cameras.filter((c) => c.status === 'error')
  const inactiveCameras = cameras.filter((c) => c.status === 'inactive')
  // Grid'de izlemeye alınmış tüm kameralar kalır (active + error) — bağlantı
  // koptuğunda kart "Bağlantı Yok" gösterir, ekrandan kaybolmaz; yalnızca
  // kullanıcının bilerek "İzlemeyi Durdur" dediği (inactive) kameralar çıkar.
  const watchedCameras = cameras.filter((c) => c.status !== 'inactive')

  function handleToggle(camera: Camera) {
    const isWatched = camera.status !== 'inactive'
    toggleWatch.mutate({ id: camera.id, nextStatus: isWatched ? 'inactive' : 'active' })
  }

  return (
    <div className="relative p-4 flex flex-col gap-4 h-full overflow-hidden">
      {/* Üst çubuk */}
      <div className="flex items-center justify-between shrink-0">
        <div>
          <h1 className="text-xl font-bold text-[var(--text-primary)]">Dashboard</h1>
          <p className="text-sm text-[var(--text-secondary)] mt-0.5">
            {cameras.length} kamera kayıtlı
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Yeni alarm uyarısı */}
          {newAlarms.length > 0 && (
            <div className="flex items-center gap-2 px-3 py-2 bg-[var(--danger)]/10 border border-[var(--danger)]/30 rounded-lg">
              <Bell size={14} className="text-[var(--danger)]" />
              <span className="text-sm font-medium text-[var(--danger)]">
                {newAlarms.length} yeni alarm
              </span>
              <button
                type="button"
                title="Alarm sesini 5 dakika sessize al"
                aria-label="Alarm sesini 5 dakika sessize al"
                onClick={() => muteSoundFor(5 * 60 * 1000)}
                className="ml-1 rounded p-1 text-[var(--danger)] transition-colors hover:bg-[var(--danger)]/15"
              >
                <VolumeX size={14} />
              </button>
              <button
                type="button"
                title="Tüm yeni alarmları onayla"
                aria-label="Tüm yeni alarmları onayla"
                disabled={acknowledgeAllAlarms.isPending}
                onClick={() => acknowledgeAllAlarms.mutate(newAlarms.map((alarm) => alarm.id))}
                className="rounded p-1 text-[var(--danger)] transition-colors hover:bg-[var(--danger)]/15 disabled:opacity-50"
              >
                <CheckCircle size={14} />
              </button>
            </div>
          )}

          {/* Grid boyutu seçici */}
          <GridSizeSelector value={cols} onChange={handleColsChange} />

          {/* Kamera izleme paneli toggle butonu */}
          <button
            onClick={() => setPanelOpen((v) => !v)}
            title="Kamera izleme listesini aç/kapat"
            className={`p-2 rounded-lg border transition-colors ${
              panelOpen
                ? 'bg-[var(--accent)] border-[var(--accent)] text-white'
                : 'bg-[var(--bg-card)] border-[var(--border)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:border-[var(--accent)]/40'
            }`}
          >
            <PanelRight size={18} />
          </button>
        </div>
      </div>

      {/* Kamera durum özeti */}
      {!isLoading && cameras.length > 0 && (
        <div className="grid grid-cols-3 gap-3 shrink-0">
          <StatusCard
            icon={<Wifi size={20} />}
            label="Çevrimiçi"
            count={activeCameras.length}
            color="text-[var(--success)]"
            cameras={activeCameras}
          />
          <StatusCard
            icon={<WifiOff size={20} />}
            label="Çevrimdışı / Hata"
            count={offlineCameras.length}
            color="text-[var(--danger)]"
            cameras={offlineCameras}
          />
          <StatusCard
            icon={<Video size={20} className="opacity-50" />}
            label="İzleme Kapalı"
            count={inactiveCameras.length}
            color="text-[var(--text-secondary)]"
            cameras={inactiveCameras}
          />
        </div>
      )}

      {/* Ana içerik + yan panel */}
      <div className="relative flex-1 min-h-0">
        {/* Kamera grid — izlemeye alınmış tüm kameralar (active + error) gösterilir */}
        {isLoading ? (
          <div className="flex justify-center py-16">
            <Spinner size="lg" />
          </div>
        ) : (
          <div className="h-full overflow-y-auto">
            <CameraGrid cameras={watchedCameras} alarmMap={alarmMap} cols={cols} />
          </div>
        )}

        {/* Kamera izleme paneli */}
        <AnimatePresence>
          {panelOpen && (
            <CameraPanel
              cameras={cameras}
              pendingId={toggleWatch.isPending ? toggleWatch.variables?.id ?? null : null}
              onToggle={handleToggle}
              onClose={() => setPanelOpen(false)}
            />
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}
