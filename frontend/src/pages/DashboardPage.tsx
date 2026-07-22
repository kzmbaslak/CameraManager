// Operator dashboard: live camera grid, alarm status bar and camera watch control.
import { useEffect, useMemo, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { useMutation, useQueries, useQuery, useQueryClient } from '@tanstack/react-query'
import { Activity, Bell, Check, CheckCircle, Gauge, MapPinned, PanelRight, Search, ShieldCheck, Video, VolumeX, Wifi, WifiOff, X } from 'lucide-react'
import { alarmsApi } from '../api/alarms'
import { camerasApi } from '../api/cameras'
import { systemApi } from '../api/system'
import { CameraGrid, type GridCols } from '../components/camera/CameraGrid'
import { GridSizeSelector } from '../components/camera/GridSizeSelector'
import { Spinner } from '../components/ui/Spinner'
import { Toggle } from '../components/ui/Toggle'
import { useAlarmStore } from '../stores/alarmStore'
import type { Alarm, Camera, CameraStreamDiagnostics, SecurityPosture } from '../types/api'

const DASHBOARD_GRID_KEY = 'dashboard-grid'
const DASHBOARD_LOW_BANDWIDTH_KEY = 'dashboard-low-bandwidth'
const DASHBOARD_CAMERA_ORDER_KEY = 'dashboard-camera-order'

function loadGridPref(): GridCols {
  try {
    const value = localStorage.getItem(DASHBOARD_GRID_KEY)
    if (value === '1' || value === '2' || value === '3' || value === '4') return Number(value) as GridCols
  } catch {
    // Fall back to the default grid when storage is unavailable.
  }
  return 2
}

function loadLowBandwidthPref() {
  try {
    return localStorage.getItem(DASHBOARD_LOW_BANDWIDTH_KEY) === 'true'
  } catch {
    return false
  }
}

function loadCameraOrderPref() {
  try {
    const parsed = JSON.parse(localStorage.getItem(DASHBOARD_CAMERA_ORDER_KEY) ?? '[]')
    return Array.isArray(parsed) ? parsed.filter((item): item is number => Number.isInteger(item)) : []
  } catch {
    return []
  }
}

function saveCameraOrderPref(order: number[]) {
  try {
    localStorage.setItem(DASHBOARD_CAMERA_ORDER_KEY, JSON.stringify(order))
  } catch {
    // Keep the in-memory order when storage is unavailable.
  }
}

function matchesCameraSearch(camera: Camera, query: string) {
  if (!query) return true
  const haystack = `${camera.name} ${camera.host} ${camera.status}`.toLocaleLowerCase('tr-TR')
  return haystack.includes(query)
}

function sortCamerasByPreference(cameras: Camera[], order: number[]) {
  const orderIndex = new Map(order.map((id, index) => [id, index]))
  return [...cameras].sort((left, right) => {
    const leftIndex = orderIndex.get(left.id) ?? Number.MAX_SAFE_INTEGER
    const rightIndex = orderIndex.get(right.id) ?? Number.MAX_SAFE_INTEGER
    if (leftIndex !== rightIndex) return leftIndex - rightIndex
    return left.id - right.id
  })
}

function Kbd({ children }: { children: string }) {
  return (
    <kbd className="rounded border border-danger/30 bg-danger/10 px-1.5 py-0.5 font-mono text-[10px] font-semibold text-danger">
      {children}
    </kbd>
  )
}

interface StatusCardProps {
  icon: React.ReactNode
  label: string
  count: number
  color: string
  cameras: Camera[]
}

function StatusCard({ icon, label, count, color, cameras }: StatusCardProps) {
  const [open, setOpen] = useState(false)

  return (
    <div className="relative">
      <button
        onClick={() => count > 0 && setOpen((value) => !value)}
        className={`flex w-full items-center gap-3 rounded-md border border-border bg-bg-secondary px-3 py-2 text-left transition-colors ${
          count > 0 ? 'cursor-pointer hover:border-border-strong hover:bg-bg-card' : 'cursor-default'
        }`}
      >
        <span className={color}>{icon}</span>
        <div className="min-w-0">
          <p className="text-xl font-semibold leading-none text-text-primary">{count}</p>
          <p className="mt-0.5 text-xs uppercase tracking-wide text-text-secondary">{label}</p>
        </div>
      </button>

      {open && cameras.length > 0 && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute left-0 top-full z-20 mt-1.5 min-w-[240px] overflow-hidden rounded-md border border-border bg-bg-card shadow-2xl">
            <p className="border-b border-border px-3 py-2 text-xs font-semibold uppercase tracking-wide text-text-secondary">
              {label}
            </p>
            <ul className="max-h-56 overflow-y-auto">
              {cameras.map((camera) => (
                <li key={camera.id} className="flex items-center gap-2 px-3 py-2 transition-colors hover:bg-bg-secondary">
                  <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${color}`} style={{ background: 'currentColor' }} />
                  <span className="min-w-0 flex-1 truncate text-sm text-text-primary">{camera.name}</span>
                  <span className="font-mono text-xs text-text-secondary">{camera.host}</span>
                </li>
              ))}
            </ul>
          </div>
        </>
      )}
    </div>
  )
}

const statusDotColor: Record<string, string> = {
  active: 'bg-success',
  error: 'bg-danger',
  inactive: 'bg-text-muted',
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
  const watchedCount = cameras.filter((camera) => camera.status !== 'inactive').length

  useEffect(() => {
    function handleClick(event: MouseEvent) {
      if (panelRef.current && !panelRef.current.contains(event.target as Node)) onClose()
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
      className="absolute right-0 top-0 z-30 flex h-full w-80 flex-col border-l border-border bg-bg-secondary shadow-2xl"
    >
      <div className="flex shrink-0 items-center justify-between border-b border-border px-4 py-3">
        <div>
          <p className="text-sm font-semibold text-text-primary">Kamera İzleme</p>
          <p className="mt-0.5 text-xs text-text-secondary">{watchedCount} / {cameras.length} kamera izleniyor</p>
        </div>
        <button
          onClick={onClose}
          aria-label="Kamera izleme panelini kapat"
          className="rounded-md p-1.5 text-text-secondary transition-colors hover:bg-bg-card hover:text-text-primary"
        >
          <X size={16} />
        </button>
      </div>

      <ul className="flex-1 overflow-y-auto py-2">
        {cameras.length === 0 && (
          <li className="px-4 py-8 text-center text-sm text-text-secondary">Kamera bulunamadı.</li>
        )}
        {cameras.map((camera) => {
          const isWatched = camera.status !== 'inactive'
          const isPending = pendingId === camera.id
          return (
            <li key={camera.id}>
              <button
                onClick={() => !isPending && onToggle(camera)}
                disabled={isPending}
                title={isWatched ? 'İzlemeyi kapat' : 'İzlemeye al'}
                className={`flex w-full items-center gap-3 px-4 py-2.5 text-left transition-colors ${
                  isWatched ? 'bg-accent/10 hover:bg-accent/15' : 'hover:bg-bg-card'
                } ${isPending ? 'cursor-wait opacity-50' : ''}`}
              >
                <div
                  className={`flex h-4 w-4 shrink-0 items-center justify-center rounded border transition-colors ${
                    isWatched ? 'border-accent bg-accent' : 'border-border bg-transparent'
                  }`}
                >
                  {isWatched && <Check size={10} className="text-white" strokeWidth={3} />}
                </div>
                <span className={`h-2 w-2 shrink-0 rounded-full ${statusDotColor[camera.status] ?? 'bg-border'}`} />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm leading-tight text-text-primary">{camera.name}</p>
                  <p className="font-mono text-xs text-text-secondary">{camera.host}</p>
                </div>
                <span className={`shrink-0 text-xs ${
                  camera.status === 'active' ? 'text-success' :
                  camera.status === 'error' ? 'text-danger' :
                  'text-text-secondary'
                }`}>
                  {statusLabel[camera.status] ?? camera.status}
                </span>
              </button>
            </li>
          )
        })}
      </ul>

      <div className="shrink-0 border-t border-border px-4 py-3">
        <p className="text-xs leading-relaxed text-text-secondary">
          İşaretli kameralar canlı grid içinde kalır. İşareti kaldırmak izlemeyi durdurur.
        </p>
      </div>
    </motion.div>
  )
}

function OperatorAssistPanel({
  newAlarmCount,
  watchedCount,
  health,
  security,
}: {
  newAlarmCount: number
  watchedCount: number
  health: CameraStreamDiagnostics[]
  security: SecurityPosture | null
}) {
  const runningCount = health.filter((item) => item.producer_running).length
  const staleCount = health.filter((item) => (item.last_frame_age_seconds ?? 0) > 10).length
  const aiBusyCount = health.filter((item) => item.ai_task_running).length

  return (
    <div className="grid shrink-0 grid-cols-1 gap-2 lg:grid-cols-3">
      <div className="flex items-center gap-3 rounded-md border border-border bg-bg-secondary px-3 py-2">
        <Activity size={18} className={newAlarmCount > 0 ? 'text-danger' : 'text-success'} />
        <div className="min-w-0">
          <p className="text-xs uppercase tracking-wide text-text-secondary">Alarm Akisi</p>
          <p className="truncate text-sm text-text-primary">
            {newAlarmCount > 0 ? `${newAlarmCount} yeni alarm inceleme bekliyor` : 'Yeni alarm yok'}
          </p>
        </div>
      </div>

      <div className="flex items-center gap-3 rounded-md border border-border bg-bg-secondary px-3 py-2">
        <Video size={18} className={staleCount > 0 ? 'text-warning' : 'text-success'} />
        <div className="min-w-0">
          <p className="text-xs uppercase tracking-wide text-text-secondary">Canli Saglik</p>
          <p className="truncate text-sm text-text-primary">
            {runningCount} / {Math.min(watchedCount, health.length || watchedCount)} uretici aktif
            {aiBusyCount > 0 ? ` · ${aiBusyCount} AI gorevi` : ''}
            {staleCount > 0 ? ` · ${staleCount} geciken kare` : ''}
          </p>
        </div>
      </div>

      <div className="flex items-center gap-3 rounded-md border border-border bg-bg-secondary px-3 py-2">
        <ShieldCheck size={18} className={security?.status === 'hardened' ? 'text-success' : 'text-warning'} />
        <div className="min-w-0">
          <p className="text-xs uppercase tracking-wide text-text-secondary">Guvenlik Kontrolu</p>
          <p className="truncate text-sm text-text-primary">
            {security
              ? security.findings.length > 0
                ? `${security.findings.length} sertlestirme maddesi bekliyor · token ${security.stream_token_ttl_seconds} sn`
                : 'Temel kontroller temiz · stream token ilk WS mesajinda'
              : 'Guvenlik durusu okunuyor'}
          </p>
        </div>
      </div>

      <div className="flex items-center gap-3 rounded-md border border-border bg-bg-secondary px-3 py-2 lg:col-span-3">
        <MapPinned size={18} className="text-accent" />
        <div className="flex min-w-0 flex-1 flex-wrap items-center gap-x-4 gap-y-1 text-xs text-text-secondary">
          <span>Olay akisi: kamera kartina tikla, kutulu canli goruntuyu ac.</span>
          <span><Kbd>Space</Kbd> alarm sesini susturur.</span>
          <span><Kbd>A</Kbd> aktif alarmi onaylar.</span>
          <span><Kbd>Esc</Kbd> detay/tam ekran kapatir.</span>
        </div>
      </div>
    </div>
  )
}

export function DashboardPage() {
  const [cols, setCols] = useState<GridCols>(loadGridPref)
  const [cameraSearch, setCameraSearch] = useState('')
  const [lowBandwidth, setLowBandwidth] = useState(loadLowBandwidthPref)
  const [cameraOrder, setCameraOrder] = useState<number[]>(loadCameraOrderPref)
  const [panelOpen, setPanelOpen] = useState(false)
  const qc = useQueryClient()
  const { stopSound, muteSoundFor } = useAlarmStore()

  const handleColsChange = (next: GridCols) => {
    setCols(next)
    try {
      localStorage.setItem(DASHBOARD_GRID_KEY, String(next))
    } catch {
      // Keep the in-memory selection when storage is unavailable.
    }
  }

  const handleLowBandwidthChange = (next: boolean) => {
    setLowBandwidth(next)
    try {
      localStorage.setItem(DASHBOARD_LOW_BANDWIDTH_KEY, String(next))
    } catch {
      // Keep the in-memory selection when storage is unavailable.
    }
  }

  const { data: cameras = [], isLoading } = useQuery({
    queryKey: ['cameras'],
    queryFn: camerasApi.list,
    refetchInterval: 10_000,
  })

  const { data: newAlarms = [] } = useQuery({
    queryKey: ['alarms', 'new'],
    queryFn: () => alarmsApi.listByStatus('new', 50),
    refetchInterval: 10_000,
  })

  const { data: securityPosture = null } = useQuery({
    queryKey: ['security-posture'],
    queryFn: systemApi.securityPosture,
    refetchInterval: 60_000,
  })

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

  const alarmMap = newAlarms.reduce<Record<number, Alarm>>((acc, alarm) => {
    if (!acc[alarm.camera_id]) acc[alarm.camera_id] = alarm
    return acc
  }, {})

  const activeCameras = cameras.filter((camera) => camera.status === 'active')
  const offlineCameras = cameras.filter((camera) => camera.status === 'error')
  const inactiveCameras = cameras.filter((camera) => camera.status === 'inactive')
  const watchedCameras = cameras.filter((camera) => camera.status !== 'inactive')
  const normalizedCameraSearch = cameraSearch.trim().toLocaleLowerCase('tr-TR')
  const orderedWatchedCameras = useMemo(
    () => sortCamerasByPreference(watchedCameras, cameraOrder),
    [watchedCameras, cameraOrder],
  )
  const visibleWatchedCameras = useMemo(
    () => orderedWatchedCameras.filter((camera) => matchesCameraSearch(camera, normalizedCameraSearch)),
    [orderedWatchedCameras, normalizedCameraSearch],
  )
  const healthQueries = useQueries({
    queries: watchedCameras.slice(0, 8).map((camera) => ({
      queryKey: ['camera-stream-diagnostics', camera.id],
      queryFn: () => camerasApi.diagnoseStream(camera.id),
      enabled: camera.status === 'active',
      refetchInterval: 15_000,
    })),
  })
  const health = healthQueries
    .map((query) => query.data)
    .filter((item): item is CameraStreamDiagnostics => Boolean(item))

  function handleToggle(camera: Camera) {
    const isWatched = camera.status !== 'inactive'
    toggleWatch.mutate({ id: camera.id, nextStatus: isWatched ? 'inactive' : 'active' })
  }

  function handleCameraReorder(sourceId: number, targetId: number) {
    if (sourceId === targetId) return
    const watchedIds = watchedCameras.map((camera) => camera.id)
    setCameraOrder((current) => {
      const currentSet = new Set(current)
      const next = [
        ...current.filter((id) => watchedIds.includes(id)),
        ...watchedIds.filter((id) => !currentSet.has(id)),
      ]
      const sourceIndex = next.indexOf(sourceId)
      const targetIndex = next.indexOf(targetId)
      if (sourceIndex < 0 || targetIndex < 0) return current
      const [moved] = next.splice(sourceIndex, 1)
      next.splice(next.indexOf(targetId), 0, moved)
      saveCameraOrderPref(next)
      return next
    })
  }

  return (
    <div className="relative flex h-full flex-col gap-3 overflow-hidden bg-bg-primary p-3">
      <div className="flex shrink-0 items-center justify-between border-b border-border pb-3">
        <div>
          <h1 className="text-lg font-semibold tracking-wide text-text-primary">Dashboard</h1>
          <p className="mt-0.5 text-xs text-text-secondary">{cameras.length} kamera kayıtlı</p>
        </div>

        <div className="flex items-center gap-2">
          {newAlarms.length > 0 && (
            <div className="flex items-center gap-2 rounded-md border border-danger/35 bg-danger/15 px-3 py-2">
              <Bell size={14} className="text-danger" />
              <span className="text-sm font-semibold text-danger">{newAlarms.length} yeni alarm</span>
              <button
                type="button"
                title="Alarm sesini 5 dakika sessize al"
                aria-label="Alarm sesini 5 dakika sessize al"
                onClick={() => muteSoundFor(5 * 60 * 1000)}
                className="ml-1 rounded p-1 text-danger transition-colors hover:bg-danger/15"
              >
                <VolumeX size={14} />
              </button>
              <button
                type="button"
                title="Tüm yeni alarmları onayla"
                aria-label="Tüm yeni alarmları onayla"
                disabled={acknowledgeAllAlarms.isPending}
                onClick={() => acknowledgeAllAlarms.mutate(newAlarms.map((alarm) => alarm.id))}
                className="rounded p-1 text-danger transition-colors hover:bg-danger/15 disabled:opacity-50"
              >
                <CheckCircle size={14} />
              </button>
              <span className="hidden items-center gap-1.5 border-l border-danger/25 pl-2 text-[11px] text-danger lg:flex">
                <Kbd>Space</Kbd><span>Sustur</span>
                <Kbd>A</Kbd><span>Onayla</span>
              </span>
            </div>
          )}

          <div className="relative hidden md:block">
            <Search size={14} className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-text-secondary" />
            <input
              value={cameraSearch}
              onChange={(event) => setCameraSearch(event.target.value)}
              placeholder="Kamera ara"
              aria-label="Canli grid kamera ara"
              className="h-9 w-44 rounded-md border border-border bg-bg-secondary pl-8 pr-3 text-sm text-text-primary outline-none transition-colors placeholder:text-text-secondary focus:border-accent"
            />
          </div>

          <div
            title="Grid akisini daha dusuk bant profiliyle al"
            className="hidden items-center gap-2 rounded-md border border-border bg-bg-secondary px-2.5 py-2 text-xs text-text-secondary lg:flex"
          >
            <Gauge size={14} />
            <span id="dashboard-low-bandwidth-label">Düşük bant</span>
            <Toggle checked={lowBandwidth} onChange={handleLowBandwidthChange} label="Düşük bant modu" />
          </div>

          <GridSizeSelector value={cols} onChange={handleColsChange} />

          <button
            onClick={() => setPanelOpen((value) => !value)}
            title="Kamera izleme listesini aç/kapat"
            aria-label="Kamera izleme listesini aç/kapat"
            className={`rounded-md border p-2 transition-colors ${
              panelOpen
                ? 'border-accent bg-accent text-white'
                : 'border-border bg-bg-secondary text-text-secondary hover:border-accent/40 hover:text-text-primary'
            }`}
          >
            <PanelRight size={18} />
          </button>
        </div>
      </div>

      {!isLoading && cameras.length > 0 && (
        <div className="grid shrink-0 grid-cols-3 gap-2">
          <StatusCard icon={<Wifi size={20} />} label="Çevrimiçi" count={activeCameras.length} color="text-success" cameras={activeCameras} />
          <StatusCard icon={<WifiOff size={20} />} label="Çevrimdışı / Hata" count={offlineCameras.length} color="text-danger" cameras={offlineCameras} />
          <StatusCard icon={<Video size={20} className="opacity-60" />} label="İzleme Kapalı" count={inactiveCameras.length} color="text-text-secondary" cameras={inactiveCameras} />
        </div>
      )}

      {!isLoading && cameras.length > 0 && (
        <OperatorAssistPanel
          newAlarmCount={newAlarms.length}
          watchedCount={watchedCameras.length}
          health={health}
          security={securityPosture}
        />
      )}

      <div className="relative min-h-0 flex-1">
        {isLoading ? (
          <div className="flex justify-center py-16">
            <Spinner size="lg" />
          </div>
        ) : (
          <div className="h-full overflow-y-auto pr-1">
            <div className="mb-2 flex gap-2 md:hidden">
              <div className="relative flex-1">
                <Search size={14} className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-text-secondary" />
                <input
                  value={cameraSearch}
                  onChange={(event) => setCameraSearch(event.target.value)}
                  placeholder="Kamera ara"
                  aria-label="Canli grid kamera ara"
                  className="h-9 w-full rounded-md border border-border bg-bg-secondary pl-8 pr-3 text-sm text-text-primary outline-none transition-colors placeholder:text-text-secondary focus:border-accent"
                />
              </div>
              <div
                title="Grid akisini daha dusuk bant profiliyle al"
                className="flex items-center gap-2 rounded-md border border-border bg-bg-secondary px-2.5 py-2 text-xs text-text-secondary"
              >
                <Gauge size={14} />
                <Toggle checked={lowBandwidth} onChange={handleLowBandwidthChange} label="Düşük bant modu" />
              </div>
            </div>
            {visibleWatchedCameras.length === 0 && watchedCameras.length > 0 ? (
              <div className="flex h-64 flex-col items-center justify-center rounded-md border border-dashed border-border bg-bg-secondary text-text-secondary">
                <p className="text-sm">Arama ile eşleşen izlenen kamera yok.</p>
              </div>
            ) : (
              <CameraGrid
                cameras={visibleWatchedCameras}
                alarmMap={alarmMap}
                cols={cols}
                lowBandwidth={lowBandwidth}
                onReorder={handleCameraReorder}
              />
            )}
          </div>
        )}

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
