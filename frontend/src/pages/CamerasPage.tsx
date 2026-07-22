// Kamera listesi, ekleme, düzenleme, silme ve AI tespiti yönetimi sayfası
import { useMemo, useState, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Activity, Plus, Trash2, Power, Pencil, Play, Search } from 'lucide-react'
import { camerasApi, type CameraUpdate } from '../api/cameras'
import { usePermissions } from '../hooks/usePermissions'
import { Table } from '../components/ui/Table'
import { Button } from '../components/ui/Button'
import { Badge } from '../components/ui/Badge'
import { Modal } from '../components/ui/Modal'
import { Input } from '../components/ui/Input'
import { Toggle } from '../components/ui/Toggle'
import { Spinner } from '../components/ui/Spinner'
import { ConfirmDialog } from '../components/ui/ConfirmDialog'
import { PasswordInput } from '../components/ui/PasswordInput'
import { useAlarmStore } from '../stores/alarmStore'
import { useToastStore } from '../stores/toastStore'
import type { Camera, CameraCreate, CameraStatus, CameraScanResult, CameraRtspDiagnostics } from '../types/api'

const statusVariant = { active: 'success', inactive: 'neutral', error: 'danger' } as const
const statusLabel = { active: 'Aktif', inactive: 'Pasif', error: 'Hata' }

/** API hatasını kullanıcıya okunabilir tek cümleye çevirir. */
function getErrorMessage(error: unknown, fallback: string): string {
  const err = error as { response?: { data?: { detail?: string } }; message?: string }
  if (!err.response && err.message === 'Network Error') {
    return 'Backend yanıt vermedi veya işlem zaman aşımına uğradı. Backend servisinin açık olduğunu kontrol edin; i610 için RTSP portunu 7778 ve path değerini /primarystream girin.'
  }
  return err.response?.data?.detail || err.message || fallback
}

/** Yeni kamera ekleme modal'ı */
function AddCameraModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const qc = useQueryClient()
  const showToast = useToastStore((state) => state.showToast)
  const [form, setForm] = useState<CameraCreate>({ name: '', host: '', rtsp_path: '', username: '', password: '', auto_rtsp_ports: false })

  const { mutate, isPending, error } = useMutation({
    mutationFn: camerasApi.add,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['cameras'] })
      showToast({ variant: 'success', title: 'Kamera eklendi', description: form.name })
      onClose()
      setForm({ name: '', host: '', rtsp_path: '', username: '', password: '', auto_rtsp_ports: false })
    },
    onError: (err) => showToast({ variant: 'danger', title: 'Kamera eklenemedi', description: getErrorMessage(err, 'IP, port, RTSP path ve kullanici/sifre bilgisini kontrol edin.') }),
  })

  const set = (field: keyof CameraCreate, value: string | number) =>
    setForm((f) => ({ ...f, [field]: value }))

  return (
    <Modal open={open} onClose={onClose} title="Kamera Ekle">
      <form onSubmit={(e) => { e.preventDefault(); mutate(form) }} className="flex flex-col gap-4">
        <div className="rounded-lg border border-[var(--border)] bg-[var(--bg-secondary)] px-3 py-2">
          <p className="text-xs text-[var(--text-secondary)] leading-5">
            RTSP Path boş bırakılırsa sistem yaygın kamera yollarını dener. Illustra/i610 için genelde
            <span className="font-mono text-[var(--text-primary)]"> /videoStreamId=1</span>,
            <span className="font-mono text-[var(--text-primary)]"> /stream1</span> veya
            <span className="font-mono text-[var(--text-primary)]"> /ufirststream</span> çalışır.
            i610 cihazında VLC ile çalışan değer çoğunlukla <span className="font-mono text-[var(--text-primary)]">7778</span> portu ve
            <span className="font-mono text-[var(--text-primary)]"> /primarystream</span> path değeridir.
            Tam RTSP URL de yapıştırabilirsiniz.
          </p>
        </div>
        <Input label="Ad" value={form.name} onChange={(e) => set('name', e.target.value)} required />
        <Input label="IP / Host" value={form.host} onChange={(e) => set('host', e.target.value)} required placeholder="192.168.1.100" />
        <div className="grid grid-cols-2 gap-3">
          <Input label="RTSP Port" type="number" defaultValue={554} onChange={(e) => set('rtsp_port', Number(e.target.value))} />
          <Input label="ONVIF Port" type="number" defaultValue={80} onChange={(e) => set('onvif_port', Number(e.target.value))} />
        </div>
        <label className="flex items-center gap-3 rounded-lg border border-[var(--border)] bg-[var(--bg-card)] px-3 py-2 text-xs text-[var(--text-secondary)] cursor-pointer">
          <input
            type="checkbox"
            checked={Boolean(form.auto_rtsp_ports)}
            onChange={(e) => setForm((f) => ({ ...f, auto_rtsp_ports: e.target.checked }))}
            className="h-4 w-4 rounded border-[var(--border)] bg-[var(--bg-primary)] text-[var(--accent)] focus:ring-[var(--accent)]"
          />
          <span>Seçili port çalışmazsa yaygın RTSP portlarını da dene: 554, 8554, 10554, 7070, 7777, 7778.</span>
        </label>
        <Input label="RTSP Path veya tam RTSP URL" placeholder="/videoStreamId=1 veya rtsp://192.168.1.100:554/stream1" value={form.rtsp_path ?? ''} onChange={(e) => set('rtsp_path', e.target.value)} />
        <Input label="Kullanıcı Adı" value={form.username ?? ''} onChange={(e) => set('username', e.target.value)} />
        <PasswordInput label="Şifre" value={form.password ?? ''} onChange={(e) => set('password', e.target.value)} />
        {error && (
          <div className="rounded-lg border border-[var(--danger)]/30 bg-[var(--danger)]/10 px-3 py-2">
            <p className="text-xs text-[var(--danger)] leading-5">
              {getErrorMessage(error, 'Kamera eklenemedi. IP, port, RTSP path ve kullanıcı/şifre bilgisini kontrol edin.')}
            </p>
          </div>
        )}
        <div className="flex gap-3 justify-end mt-1">
          <Button variant="secondary" type="button" onClick={onClose}>İptal</Button>
          <Button type="submit" loading={isPending}>{isPending ? 'Bağlantı Doğrulanıyor' : 'Ekle'}</Button>
        </div>
      </form>
    </Modal>
  )
}

/** Kameraları tara modal'ı */
function ScanCamerasModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const qc = useQueryClient()
  const showToast = useToastStore((state) => state.showToast)
  const [ipRange, setIpRange] = useState('192.168.1.0/24')
  const [rtspPort, setRtspPort] = useState(554)
  const [autoRtspPorts, setAutoRtspPorts] = useState(true)
  const [username, setUsername] = useState('admin')
  const [password, setPassword] = useState('admin123')
  const [results, setResults] = useState<(CameraScanResult & { name: string; selected: boolean })[]>([])
  const abortRef = useRef<AbortController | null>(null)

  const { mutate: startScan, isPending: isScanning, error: scanError, reset: resetScan } = useMutation({
    mutationFn: () => {
      abortRef.current = new AbortController()
      return camerasApi.scan(
        { ip_range: ipRange, rtsp_port: rtspPort, auto_rtsp_ports: autoRtspPorts, username, password },
        abortRef.current.signal,
      )
    },
    onSuccess: (data) => {
      setResults(
        data.map((item) => ({
          ...item,
          name: `Kamera_${item.ip.split('.').join('_')}_${(item.brand || 'Generic').replace(/\s+/g, '')}`,
          selected: true,
        }))
      )
    },
    onError: () => {
      // Kullanıcı "Durdur" bastıysa hata gösterme — sadece idle'a dön
      if (abortRef.current?.signal.aborted) resetScan()
    },
  })

  const handleStop = () => {
    abortRef.current?.abort()
  }

  const { mutate: saveCameras, isPending: isSaving, error: saveError } = useMutation({
    mutationFn: (payload: CameraCreate[]) => camerasApi.bulkAdd(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['cameras'] })
      showToast({ variant: 'success', title: 'Kameralar eklendi', description: `${results.filter((r) => r.selected).length} kamera kaydedildi.` })
      onClose()
      setResults([])
    },
    onError: (err) => showToast({ variant: 'danger', title: 'Kameralar eklenemedi', description: getErrorMessage(err, 'Toplu ekleme sirasinda hata olustu.') }),
  })

  const toggleSelect = (index: number) => {
    setResults((prev) =>
      prev.map((item, idx) => (idx === index ? { ...item, selected: !item.selected } : item))
    )
  }

  const toggleSelectAll = () => {
    const allSelected = results.every((r) => r.selected)
    setResults((prev) => prev.map((item) => ({ ...item, selected: !allSelected })))
  }

  const handleNameChange = (index: number, newName: string) => {
    setResults((prev) =>
      prev.map((item, idx) => (idx === index ? { ...item, name: newName } : item))
    )
  }

  const handleSave = () => {
    const selectedList = results
      .filter((r) => r.selected)
      .map((r) => ({
        name: r.name,
        host: r.ip,
        rtsp_port: r.port,
        rtsp_path: r.path,
        onvif_port: 80,
        username,
        password,
        brand: r.brand,
      }))
    if (selectedList.length === 0) return
    saveCameras(selectedList)
  }

  return (
    <Modal open={open} onClose={onClose} title="Ağdaki Kameraları Tara" width="max-w-2xl">
      <div className="flex flex-col gap-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="flex flex-col gap-3">
            <Input
              label="IP Aralığı"
              value={ipRange}
              onChange={(e) => setIpRange(e.target.value)}
              placeholder="192.168.1.0/24 veya 192.168.1.10-50"
              required
            />
            <span className="text-[10px] text-[var(--text-secondary)] -mt-2">
              Örnekler: CIDR (192.168.1.0/24), IP aralığı (192.168.1.10-50) veya virgüllü liste (192.168.1.10,192.168.1.12)
            </span>
            <Input
              label="RTSP Port"
              type="number"
              value={rtspPort}
              onChange={(e) => setRtspPort(Number(e.target.value))}
            />
            <span className="text-[10px] text-[var(--text-secondary)] -mt-2">
              Standart kameralar genelde 554 kullanır; Illustra i610 için 7778 deneyin.
            </span>
            <label className="flex items-center gap-2 text-xs text-[var(--text-secondary)] cursor-pointer">
              <input
                type="checkbox"
                checked={autoRtspPorts}
                onChange={(e) => setAutoRtspPorts(e.target.checked)}
                className="h-4 w-4 rounded border-[var(--border)] bg-[var(--bg-primary)] text-[var(--accent)] focus:ring-[var(--accent)]"
              />
              <span>Seçili port bulunamazsa alternatif RTSP portlarını da dene.</span>
            </label>
          </div>
          <div className="flex flex-col gap-3">
            <Input
              label="Kullanıcı Adı"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
            <PasswordInput
              label="Şifre"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
        </div>

        <div className="rounded-lg border border-[var(--border)] bg-[var(--bg-secondary)] px-3 py-2">
          <p className="text-xs text-[var(--text-secondary)] leading-5">
            Tarama yalnızca gerçekten kare okunabilen RTSP yayınlarını listeler. Şifresiz görüntü veren cihazlar,
            kamera tarafında anonim RTSP erişimi açık olduğu için yanlış şifreyle de bulunabilir.
            i610 arıyorsanız portu 7778 yapın veya alternatif port denemeyi açın; sistem /primarystream yolunu da otomatik dener.
          </p>
        </div>

        <div className="flex justify-end gap-3 border-b border-[var(--border)] pb-4">
          <Button variant="secondary" type="button" onClick={onClose} disabled={isScanning || isSaving}>
            İptal
          </Button>
          <Button onClick={() => startScan()} loading={isScanning} disabled={isSaving} icon={<Search size={15} />}>
            Taramayı Başlat
          </Button>
        </div>

        {isScanning && (
          <div className="flex flex-col items-center justify-center py-10 gap-3">
            <Spinner size="lg" />
            <p className="text-sm text-[var(--text-primary)] font-medium mt-2">RTSP yayınları doğrulanıyor...</p>
            <p className="text-xs text-[var(--text-secondary)] text-center max-w-sm">
              Sistem IP aralığını tarar, bilinen stream yollarını dener ve gerçek frame okuyabildiği kameraları gösterir.
            </p>
            <Button variant="secondary" size="sm" onClick={handleStop}>
              Durdur
            </Button>
          </div>
        )}

        {!isScanning && results.length > 0 && (
          <div className="flex flex-col gap-3">
            <div className="flex items-center justify-between text-xs text-[var(--text-secondary)] font-medium border-b border-[var(--border)] pb-2 px-1">
              <label className="flex items-center gap-2 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={results.every((r) => r.selected)}
                  onChange={toggleSelectAll}
                  className="rounded border-[var(--border)] bg-[var(--bg-primary)] text-[var(--accent)] focus:ring-[var(--accent)] h-4 w-4"
                />
                <span>Hepsini Seç ({results.length} kamera bulundu)</span>
              </label>
              <span>Eklenecek isimleri özelleştirebilirsiniz.</span>
            </div>

            <div className="flex flex-col gap-2 max-h-[260px] overflow-y-auto pr-1">
              {results.map((row, index) => (
                <div
                  key={index}
                  className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3 rounded-lg border border-[var(--border)] bg-[var(--bg-card)] hover:bg-[var(--bg-hover)] transition-colors"
                >
                  <div className="flex items-start gap-3">
                    <input
                      type="checkbox"
                      checked={row.selected}
                      onChange={() => toggleSelect(index)}
                      className="rounded border-[var(--border)] bg-[var(--bg-primary)] text-[var(--accent)] focus:ring-[var(--accent)] mt-1 h-4 w-4 cursor-pointer"
                    />
                    <div className="flex flex-col">
                      <span className="text-sm font-semibold text-[var(--text-primary)]">{row.ip}:{row.port}</span>
                      <span className="text-xs text-[var(--text-secondary)] font-mono">{row.path}</span>
                      <span className="text-[10px] text-[var(--accent)] mt-0.5">{row.brand} - {row.desc}</span>
                      <span className="text-[10px] text-[var(--text-secondary)] font-mono mt-0.5">{row.url}</span>
                    </div>
                  </div>
                  <div className="sm:w-1/2 flex items-center">
                    <Input
                      placeholder="Kamera Adı"
                      value={row.name}
                      onChange={(e) => handleNameChange(index, e.target.value)}
                      className="w-full"
                    />
                  </div>
                </div>
              ))}
            </div>

            {saveError && (
              <p className="text-xs text-[var(--danger)]">
                {getErrorMessage(saveError, 'Kameralar eklenirken hata oluştu.')}
              </p>
            )}
            
            <div className="flex justify-end gap-3 pt-3 border-t border-[var(--border)]">
              <Button variant="secondary" onClick={onClose} disabled={isSaving}>
                İptal
              </Button>
              <Button
                onClick={handleSave}
                loading={isSaving}
                disabled={!results.some((r) => r.selected)}
              >
                {results.every((r) => r.selected)
                  ? `Tümünü Ekle (${results.length})`
                  : `Seçilenleri Ekle (${results.filter((r) => r.selected).length})`}
              </Button>
            </div>
          </div>
        )}

        {!isScanning && results.length === 0 && !scanError && (
          <p className="text-sm text-center text-[var(--text-secondary)] py-8 bg-[var(--bg-card)] rounded-lg border border-dashed border-[var(--border)]">
            Henüz tarama başlatılmadı veya son taramada kamera bulunamadı. Lütfen üstten IP aralığı girip "Taramayı Başlat" tuşuna basın.
          </p>
        )}

        {scanError != null && (
          <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/20 text-sm text-[var(--danger)]">
            {getErrorMessage(scanError, 'Tarama sırasında hata oluştu.')}
          </div>
        )}
      </div>
    </Modal>
  )
}

/** Mevcut kamerayı düzenleme modal'ı — `key={camera.id}` ile her kamera için yeniden mount edilir (bkz. çağıran yer) */
function EditCameraModal({ camera, onClose }: { camera: Camera | null; onClose: () => void }) {
  const qc = useQueryClient()
  const showToast = useToastStore((state) => state.showToast)
  const [form, setForm] = useState<CameraUpdate>(() => camera ? {
    name: camera.name,
    host: camera.host,
    rtsp_port: camera.rtsp_port,
    rtsp_path: camera.rtsp_path,
    onvif_port: camera.onvif_port,
    username: camera.username ?? '',
    ai_confidence_threshold: camera.ai_confidence_threshold,
    ai_iou_threshold: camera.ai_iou_threshold,
    ai_alarm_cooldown_seconds: camera.ai_alarm_cooldown_seconds,
    ai_active_start: camera.ai_active_start ?? '',
    ai_active_end: camera.ai_active_end ?? '',
    ai_roi_polygon: camera.ai_roi_polygon ?? '',
  } : {})

  const { mutate, isPending, error } = useMutation({
    mutationFn: (payload: CameraUpdate) => camerasApi.update(camera!.id, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['cameras'] })
      showToast({ variant: 'success', title: 'Kamera guncellendi', description: camera?.name })
      onClose()
    },
    onError: (err) => showToast({ variant: 'danger', title: 'Kamera guncellenemedi', description: getErrorMessage(err, 'Kamera bilgileri kaydedilemedi.') }),
  })

  const {
    mutate: testConnection,
    data: testResult,
    isPending: isTestingConnection,
    error: testError,
  } = useMutation({
    mutationFn: () => camerasApi.diagnoseRtsp(camera!.id),
  })

  if (!camera) return null

  const connectionChanged =
    form.host !== camera.host ||
    form.rtsp_port !== camera.rtsp_port ||
    form.rtsp_path !== camera.rtsp_path ||
    form.username !== (camera.username ?? '') ||
    Boolean(form.password)

  return (
    <Modal open onClose={onClose} title={`Düzenle — ${camera.name}`}>
      <form onSubmit={(e) => { e.preventDefault(); mutate(form) }} className="flex flex-col gap-4">
        <Input label="Ad" value={form.name ?? ''} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} required />
        <Input label="IP / Host" value={form.host ?? ''} onChange={(e) => setForm((f) => ({ ...f, host: e.target.value }))} required />
        <div className="grid grid-cols-2 gap-3">
          <Input label="RTSP Port" type="number" value={form.rtsp_port ?? 554} onChange={(e) => setForm((f) => ({ ...f, rtsp_port: Number(e.target.value) }))} />
          <Input label="ONVIF Port" type="number" value={form.onvif_port ?? 80} onChange={(e) => setForm((f) => ({ ...f, onvif_port: Number(e.target.value) }))} />
        </div>
        <Input label="RTSP Path" value={form.rtsp_path ?? ''} onChange={(e) => setForm((f) => ({ ...f, rtsp_path: e.target.value }))} />
        <Input label="Kullanıcı Adı" value={form.username ?? ''} onChange={(e) => setForm((f) => ({ ...f, username: e.target.value }))} />
        <PasswordInput label="Yeni Şifre" placeholder="Değiştirmek için doldurun" onChange={(e) => setForm((f) => ({ ...f, password: e.target.value || undefined }))} />
        <div className="rounded-lg border border-[var(--border)] bg-[var(--bg-secondary)] p-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">Baglanti Testi</p>
              <p className="mt-1 text-xs text-[var(--text-secondary)]">
                Kayitli RTSP baglantisi sifre gosterilmeden test edilir.
              </p>
            </div>
            <Button
              type="button"
              size="sm"
              variant="secondary"
              icon={<Activity size={13} />}
              loading={isTestingConnection}
              onClick={() => testConnection()}
            >
              Test Et
            </Button>
          </div>
          {connectionChanged && (
            <p className="mt-2 text-xs text-[var(--warning)]">
              Kaydedilmemis degisiklikler var; test mevcut kayitli baglanti degerleriyle calisir.
            </p>
          )}
          {testError && (
            <p className="mt-2 text-xs text-[var(--danger)]">
              {getErrorMessage(testError, 'RTSP baglanti testi calistirilamadi.')}
            </p>
          )}
          {testResult && (
            <div className="mt-3 flex flex-col gap-2">
              <p className={testResult.frame_ok ? 'text-xs text-[var(--success)]' : 'text-xs text-[var(--danger)]'}>
                {testResult.message}
              </p>
              <div className="grid grid-cols-3 gap-2 text-xs">
                <Badge variant={testResult.tcp_open ? 'success' : 'danger'}>TCP {testResult.tcp_open ? 'Acik' : 'Kapali'}</Badge>
                <Badge variant={testResult.describe_ok ? 'success' : 'danger'}>DESCRIBE {testResult.describe_ok ? 'OK' : 'Hata'}</Badge>
                <Badge variant={testResult.frame_ok ? 'success' : 'danger'}>Frame {testResult.frame_ok ? 'OK' : 'Yok'}</Badge>
              </div>
              <p className="break-all font-mono text-[11px] text-[var(--text-secondary)]">
                {testResult.authenticated_url_masked}
              </p>
            </div>
          )}
        </div>
        <div className="rounded-lg border border-[var(--border)] bg-[var(--bg-secondary)] p-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">AI Alarm Ayarlari</p>
          <div className="mt-3 grid grid-cols-3 gap-3">
            <Input label="Confidence" type="number" step="0.05" min="0.05" max="0.95" value={form.ai_confidence_threshold ?? 0.5} onChange={(e) => setForm((f) => ({ ...f, ai_confidence_threshold: Number(e.target.value) }))} />
            <Input label="IoU" type="number" step="0.05" min="0.05" max="0.95" value={form.ai_iou_threshold ?? 0.45} onChange={(e) => setForm((f) => ({ ...f, ai_iou_threshold: Number(e.target.value) }))} />
            <Input label="Cooldown sn" type="number" min="5" max="3600" value={form.ai_alarm_cooldown_seconds ?? 60} onChange={(e) => setForm((f) => ({ ...f, ai_alarm_cooldown_seconds: Number(e.target.value) }))} />
          </div>
          <div className="mt-3 grid grid-cols-2 gap-3">
            <Input label="Aktif Baslangic" placeholder="00:00" value={form.ai_active_start ?? ''} onChange={(e) => setForm((f) => ({ ...f, ai_active_start: e.target.value || null }))} />
            <Input label="Aktif Bitis" placeholder="23:59" value={form.ai_active_end ?? ''} onChange={(e) => setForm((f) => ({ ...f, ai_active_end: e.target.value || null }))} />
          </div>
          <label className="mt-3 flex flex-col gap-1 text-sm font-medium text-[var(--text-primary)]">
            ROI Poligon JSON
            <textarea
              value={form.ai_roi_polygon ?? ''}
              onChange={(e) => setForm((f) => ({ ...f, ai_roi_polygon: e.target.value || null }))}
              placeholder='[{"x":0.1,"y":0.1},{"x":0.9,"y":0.1},{"x":0.9,"y":0.9},{"x":0.1,"y":0.9}]'
              className="min-h-20 rounded-lg border border-[var(--border)] bg-[var(--bg-card)] px-3 py-2 font-mono text-xs text-[var(--text-primary)] outline-none transition-colors focus:border-[var(--accent)]"
            />
            <span className="text-[10px] font-normal text-[var(--text-secondary)]">
              Bos birakilirsa tum goruntu izlenir. Koordinatlar 0-1 araliginda normalize edilmelidir.
            </span>
          </label>
        </div>
        {error && <p className="text-xs text-[var(--danger)]">{getErrorMessage(error, 'Kamera güncellenemedi.')}</p>}
        <div className="flex gap-3 justify-end mt-1">
          <Button variant="secondary" type="button" onClick={onClose}>İptal</Button>
          <Button type="submit" loading={isPending}>Kaydet</Button>
        </div>
      </form>
    </Modal>
  )
}

/** Kameralar sayfası — listeleme, ekleme, düzenleme, silme, AI tespiti yönetimi */
export function CamerasPage() {
  const [showAdd, setShowAdd] = useState(false)
  const [showScan, setShowScan] = useState(false)
  const [editCamera, setEditCamera] = useState<Camera | null>(null)
  const [diagnosticResult, setDiagnosticResult] = useState<CameraRtspDiagnostics | null>(null)
  const [diagnosticError, setDiagnosticError] = useState<string | null>(null)
  const [cameraSearch, setCameraSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<CameraStatus | 'all'>('all')
  const [aiFilter, setAiFilter] = useState<'all' | 'enabled' | 'disabled'>('all')
  const [deleteTarget, setDeleteTarget] = useState<Camera | null>(null)
  const qc = useQueryClient()
  const showToast = useToastStore((state) => state.showToast)
  const { canManageCameras, canEditCameras } = usePermissions()
  const { setExpandedCamera } = useAlarmStore()

  const { data: cameras = [], isLoading } = useQuery({
    queryKey: ['cameras'],
    queryFn: camerasApi.list,
  })

  const filteredCameras = useMemo(() => {
    const needle = cameraSearch.trim().toLowerCase()
    return cameras.filter((camera) => {
      const matchesSearch = !needle || [
        camera.name,
        camera.host,
        camera.rtsp_path,
        camera.brand ?? '',
        camera.model ?? '',
        camera.nvr_id ? `nvr ${camera.nvr_id}` : '',
      ].some((value) => value.toLowerCase().includes(needle))
      const matchesStatus = statusFilter === 'all' || camera.status === statusFilter
      const matchesAi =
        aiFilter === 'all' ||
        (aiFilter === 'enabled' && camera.ai_detection_enabled) ||
        (aiFilter === 'disabled' && !camera.ai_detection_enabled)
      return matchesSearch && matchesStatus && matchesAi
    })
  }, [aiFilter, cameraSearch, cameras, statusFilter])

  const hasCameraFilter = cameraSearch.trim() !== '' || statusFilter !== 'all' || aiFilter !== 'all'

  const resetCameraFilters = () => {
    setCameraSearch('')
    setStatusFilter('all')
    setAiFilter('all')
  }

  /** Kamera durumunu değiştirir; ACTIVE ↔ INACTIVE */
  const toggleStatus = useMutation({
    mutationFn: ({ id, status }: { id: number; status: CameraStatus }) =>
      camerasApi.updateStatus(id, status),
    onSuccess: (camera) => {
      qc.invalidateQueries({ queryKey: ['cameras'] })
      showToast({ variant: 'success', title: 'Izleme durumu guncellendi', description: camera.name })
    },
    onError: (err) => showToast({ variant: 'danger', title: 'Durum guncellenemedi', description: getErrorMessage(err, 'Kamera izleme durumu degistirilemedi.') }),
  })

  /** AI insan tespitini açar veya kapatır */
  const toggleAI = useMutation({
    mutationFn: ({ id, enabled }: { id: number; enabled: boolean }) =>
      camerasApi.toggleAI(id, enabled),
    onSuccess: (camera) => {
      qc.invalidateQueries({ queryKey: ['cameras'] })
      showToast({ variant: 'success', title: 'AI tespiti guncellendi', description: camera.name })
    },
    onError: (err) => showToast({ variant: 'danger', title: 'AI ayari guncellenemedi', description: getErrorMessage(err, 'AI tespiti degistirilemedi.') }),
  })

  /** Kamerayı sistemden siler */
  const deleteCam = useMutation({
    mutationFn: camerasApi.delete,
    onSuccess: () => {
      showToast({ variant: 'success', title: 'Kamera silindi', description: deleteTarget?.name })
      setDeleteTarget(null)
      qc.invalidateQueries({ queryKey: ['cameras'] })
    },
    onError: (err) => showToast({ variant: 'danger', title: 'Kamera silinemedi', description: getErrorMessage(err, 'Silme islemi tamamlanamadi.') }),
  })

  /** Kayıtlı kameranın RTSP host/port/path erişimini test eder. */
  const diagnoseRtsp = useMutation({
    mutationFn: camerasApi.diagnoseRtsp,
    onMutate: () => {
      setDiagnosticError(null)
      setDiagnosticResult(null)
    },
    onSuccess: setDiagnosticResult,
    onError: (error) => setDiagnosticError(getErrorMessage(error, 'RTSP bağlantı testi çalıştırılamadı.')),
  })

  const { data: streamDiagnostic } = useQuery({
    queryKey: ['camera-stream-diagnostic', diagnosticResult?.camera_id],
    queryFn: () => camerasApi.diagnoseStream(diagnosticResult!.camera_id),
    enabled: diagnosticResult !== null && diagnosticError === null,
  })

  const { data: healthHistory } = useQuery({
    queryKey: ['camera-health-history', diagnosticResult?.camera_id],
    queryFn: () => camerasApi.diagnoseHealthHistory(diagnosticResult!.camera_id),
    enabled: diagnosticResult !== null && diagnosticError === null,
    refetchInterval: 15000,
  })

  const columns = [
    { key: 'name', header: 'Ad', render: (c: Camera) => (
      <span className="font-medium">{c.name}</span>
    )},
    { key: 'host', header: 'Host', render: (c: Camera) => (
      <span className="font-mono text-xs text-[var(--text-secondary)]">{c.host}:{c.rtsp_port}</span>
    )},
    {
      key: 'status',
      header: 'İzleme Durumu',
      render: (c: Camera) => (
        <div className="flex flex-col gap-0.5">
          <Badge variant={statusVariant[c.status]}>{statusLabel[c.status]}</Badge>
          <span className="text-[10px] text-[var(--text-secondary)]">
            {c.status === 'active' ? 'Sistem bu kamerayı izliyor' :
             c.status === 'inactive' ? 'İzleme kapalı' : 'Bağlantı kurulamıyor'}
          </span>
        </div>
      ),
    },
    {
      key: 'ai',
      header: 'AI Tespiti',
      render: (c: Camera) => (
        <div className="flex items-center gap-2">
          <Toggle
            checked={c.ai_detection_enabled}
            disabled={!canEditCameras || toggleAI.isPending}
            label="AI tespiti"
            onChange={(enabled) => toggleAI.mutate({ id: c.id, enabled })}
          />
          <span className={`text-xs ${c.ai_detection_enabled ? 'text-[var(--success)]' : 'text-[var(--text-secondary)]'}`}>
            {c.ai_detection_enabled ? 'Açık' : 'Kapalı'}
          </span>
        </div>
      ),
    },
    {
      key: 'actions',
      header: '',
      width: '200px',
      render: (c: Camera) => (
        <div className="flex items-center gap-1.5">
          {(c.status === 'active' || c.status === 'error') && (
            <Button
              size="sm"
              variant="secondary"
              icon={<Play size={12} />}
              onClick={() => setExpandedCamera(c.id)}
            >
              İzle
            </Button>
          )}
          {canEditCameras && (
            <>
              <Button
                size="sm"
                variant="secondary"
                icon={<Activity size={12} />}
                loading={diagnoseRtsp.isPending && diagnoseRtsp.variables === c.id}
                onClick={() => diagnoseRtsp.mutate(c.id)}
              >
                Test Et
              </Button>
              <Button
                size="sm"
                variant="secondary"
                icon={<Pencil size={12} />}
                onClick={() => setEditCamera(c)}
              >
                Düzenle
              </Button>
              <Button
                size="sm"
                variant={c.status === 'active' ? 'secondary' : 'primary'}
                icon={<Power size={12} />}
                loading={toggleStatus.isPending && toggleStatus.variables?.id === c.id}
                title={c.status === 'active'
                  ? 'Bu kamerayı sistemin izlemesini durdur'
                  : 'Bu kamerayı sisteme al ve izlemeye başla'}
                onClick={() => toggleStatus.mutate({
                  id: c.id,
                  status: c.status === 'active' ? 'inactive' : 'active',
                })}
              >
                {c.status === 'active' ? 'İzlemeyi Durdur' : 'İzlemeye Al'}
              </Button>
            </>
          )}
          {canManageCameras && (
            <Button
              size="sm"
              variant="danger"
              icon={<Trash2 size={12} />}
              loading={deleteCam.isPending && deleteCam.variables === c.id}
              onClick={() => setDeleteTarget(c)}
            >
              Sil
            </Button>
          )}
        </div>
      ),
    },
  ]

  return (
    <div className="p-6 flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-[var(--text-primary)]">Kameralar</h1>
          <p className="text-sm text-[var(--text-secondary)] mt-0.5">
            {filteredCameras.length} / {cameras.length} kamera — {cameras.filter((c) => c.ai_detection_enabled).length} AI aktif
          </p>
        </div>
        {canManageCameras && (
          <div className="flex gap-2">
            <Button variant="secondary" icon={<Search size={15} />} onClick={() => setShowScan(true)}>
              Kameraları Tara
            </Button>
            <Button icon={<Plus size={15} />} onClick={() => setShowAdd(true)}>
              Kamera Ekle
            </Button>
          </div>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <Input
          value={cameraSearch}
          onChange={(e) => setCameraSearch(e.target.value)}
          placeholder="Kamera adi, IP, marka veya NVR ara"
          className="w-full sm:w-80"
        />
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as CameraStatus | 'all')}
          className="rounded-lg border border-[var(--border)] bg-[var(--bg-card)] px-3 py-2 text-sm text-[var(--text-primary)] outline-none transition-colors focus:border-[var(--accent)]"
        >
          <option value="all">Tum Durumlar</option>
          <option value="active">Aktif</option>
          <option value="inactive">Pasif</option>
          <option value="error">Hata</option>
        </select>
        <select
          value={aiFilter}
          onChange={(e) => setAiFilter(e.target.value as 'all' | 'enabled' | 'disabled')}
          className="rounded-lg border border-[var(--border)] bg-[var(--bg-card)] px-3 py-2 text-sm text-[var(--text-primary)] outline-none transition-colors focus:border-[var(--accent)]"
        >
          <option value="all">Tum AI</option>
          <option value="enabled">AI Acik</option>
          <option value="disabled">AI Kapali</option>
        </select>
        {hasCameraFilter && (
          <Button size="sm" variant="secondary" onClick={resetCameraFilters}>
            Filtreleri Sifirla
          </Button>
        )}
      </div>

      {isLoading ? (
        <div className="flex justify-center py-16"><Spinner size="lg" /></div>
      ) : (
        <Table columns={columns} data={filteredCameras} keyFn={(c) => c.id} emptyText={hasCameraFilter ? 'Filtrelerle eslesen kamera bulunamadi.' : 'Henüz kamera eklenmedi.'} />
      )}

      <AddCameraModal open={showAdd} onClose={() => setShowAdd(false)} />
      <ScanCamerasModal open={showScan} onClose={() => setShowScan(false)} />
      <EditCameraModal key={editCamera?.id ?? 'none'} camera={editCamera} onClose={() => setEditCamera(null)} />
      <ConfirmDialog
        open={deleteTarget !== null}
        title="Kamera Sil"
        description={deleteTarget ? `"${deleteTarget.name}" kamerasi silinecek. Bu islem kamera kaydini sistemden kaldirir.` : ''}
        confirmLabel="Sil"
        loading={deleteCam.isPending}
        onClose={() => !deleteCam.isPending && setDeleteTarget(null)}
        onConfirm={() => deleteTarget && deleteCam.mutate(deleteTarget.id)}
      />
      <Modal open={diagnosticResult !== null || diagnosticError !== null} onClose={() => { setDiagnosticResult(null); setDiagnosticError(null) }} title="RTSP Bağlantı Testi">
        {diagnosticError && (
          <div className="flex flex-col gap-3 text-sm">
            <p className="text-[var(--danger)]">{diagnosticError}</p>
            <div className="flex justify-end">
              <Button variant="secondary" onClick={() => { setDiagnosticResult(null); setDiagnosticError(null) }}>Kapat</Button>
            </div>
          </div>
        )}
        {diagnosticResult && (
          <div className="flex flex-col gap-3 text-sm">
            <p className={diagnosticResult.frame_ok ? 'text-[var(--success)]' : 'text-[var(--danger)]'}>
              {diagnosticResult.message}
            </p>
            <div className="rounded-lg border border-[var(--border)] bg-[var(--bg-secondary)] p-3 font-mono text-xs text-[var(--text-secondary)] break-all">
              {diagnosticResult.authenticated_url_masked}
            </div>
            <div className="grid grid-cols-3 gap-2 text-xs">
              <Badge variant={diagnosticResult.tcp_open ? 'success' : 'danger'}>TCP {diagnosticResult.tcp_open ? 'Açık' : 'Kapalı'}</Badge>
              <Badge variant={diagnosticResult.describe_ok ? 'success' : 'danger'}>DESCRIBE {diagnosticResult.describe_ok ? 'OK' : 'Hata'}</Badge>
              <Badge variant={diagnosticResult.frame_ok ? 'success' : 'danger'}>Frame {diagnosticResult.frame_ok ? 'OK' : 'Yok'}</Badge>
            </div>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <Badge variant={diagnosticResult.authenticated_frame_ok ? 'success' : 'danger'}>Auth Frame {diagnosticResult.authenticated_frame_ok ? 'OK' : 'Yok'}</Badge>
              <Badge variant={diagnosticResult.anonymous_frame_ok ? 'success' : 'danger'}>Anon Frame {diagnosticResult.anonymous_frame_ok ? 'OK' : 'Yok'}</Badge>
            </div>
            <p className="text-xs text-[var(--text-secondary)]">
              Host: {diagnosticResult.host}:{diagnosticResult.rtsp_port} · Path: {diagnosticResult.rtsp_path || '/'} ·
              {diagnosticResult.nvr_id ? ` NVR ID: ${diagnosticResult.nvr_id}` : ' Bağımsız kamera'}
            </p>
            {streamDiagnostic && (
              <div className="rounded-lg border border-[var(--border)] bg-[var(--bg-secondary)] p-3">
                <div className="flex items-center justify-between gap-3 text-xs">
                  <span className="font-medium text-[var(--text-primary)]">Canlı Akış Telemetrisi</span>
                  <Badge variant={streamDiagnostic.producer_running ? 'success' : 'danger'}>
                    {streamDiagnostic.producer_running ? 'Producer Açık' : 'Producer Kapalı'}
                  </Badge>
                </div>
                <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-[var(--text-secondary)]">
                  <span>Profil: <strong className="text-[var(--text-primary)]">{streamDiagnostic.active_profile}</strong></span>
                  <span>Subscriber: <strong className="text-[var(--text-primary)]">{streamDiagnostic.subscriber_count}</strong></span>
                  <span>AI Görevi: <strong className="text-[var(--text-primary)]">{streamDiagnostic.ai_task_running ? 'Açık' : 'Kapalı'}</strong></span>
                  <span>Cache: <strong className="text-[var(--text-primary)]">{streamDiagnostic.cached_frame_available ? 'Var' : 'Yok'}</strong></span>
                  <span>Open Deneme: <strong className="text-[var(--text-primary)]">{streamDiagnostic.open_attempts}</strong></span>
                  <span>Open Hata: <strong className="text-[var(--text-primary)]">{streamDiagnostic.open_failures}</strong></span>
                </div>
                <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-[var(--text-secondary)]">
                  <span>Son Frame: <strong className="text-[var(--text-primary)]">{streamDiagnostic.last_frame_age_seconds !== null ? `${streamDiagnostic.last_frame_age_seconds.toFixed(1)} sn önce` : 'Yok'}</strong></span>
                  <span>Retry Backoff: <strong className="text-[var(--text-primary)]">{streamDiagnostic.retry_cooldown_seconds.toFixed(1)} sn</strong></span>
                  <span>Warmup Reads: <strong className="text-[var(--text-primary)]">{streamDiagnostic.warmup_reads}</strong></span>
                  <span>Failure Count: <strong className="text-[var(--text-primary)]">{streamDiagnostic.failure_count}</strong></span>
                  <span>Open Timeout: <strong className="text-[var(--text-primary)]">{streamDiagnostic.open_timeout_ms} ms</strong></span>
                  <span>Read Timeout: <strong className="text-[var(--text-primary)]">{streamDiagnostic.read_timeout_ms} ms</strong></span>
                </div>
              </div>
            )}
            {healthHistory && (
              <div className="rounded-lg border border-[var(--border)] bg-[var(--bg-secondary)] p-3">
                <div className="flex items-center justify-between gap-3 text-xs">
                  <span className="font-medium text-[var(--text-primary)]">Saglik Gecmisi</span>
                  <Badge variant={healthHistory.unreachable_count === 0 ? 'success' : 'danger'}>
                    {healthHistory.availability_percent !== null ? `%${healthHistory.availability_percent}` : 'Veri Yok'}
                  </Badge>
                </div>
                <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-[var(--text-secondary)]">
                  <span>Olcum: <strong className="text-[var(--text-primary)]">{healthHistory.sample_count}</strong></span>
                  <span>Kopma: <strong className="text-[var(--text-primary)]">{healthHistory.unreachable_count}</strong></span>
                  <span>Son Latency: <strong className="text-[var(--text-primary)]">{healthHistory.latest_latency_ms !== null ? `${healthHistory.latest_latency_ms.toFixed(0)} ms` : 'Yok'}</strong></span>
                  <span>Son Hata: <strong className="text-[var(--text-primary)]">{healthHistory.latest_failure_reason || 'Yok'}</strong></span>
                </div>
                <div className="mt-3 flex h-8 items-end gap-1 overflow-hidden" aria-label="Kamera saglik gecmisi">
                  {[...healthHistory.samples].reverse().map((sample) => (
                    <span
                      key={sample.id}
                      title={`${new Date(sample.checked_at).toLocaleString()} - ${sample.reachable ? 'Erisilebilir' : sample.failure_reason || 'Erisilemiyor'}`}
                      className={`min-w-[3px] flex-1 rounded-sm ${sample.reachable ? 'bg-[var(--success)]' : 'bg-[var(--danger)]'}`}
                      style={{ height: sample.reachable ? '55%' : '100%' }}
                    />
                  ))}
                  {healthHistory.samples.length === 0 && (
                    <span className="text-xs text-[var(--text-secondary)]">Saglik gecmisi henuz olusmadi.</span>
                  )}
                </div>
              </div>
            )}
            <div className="flex justify-end">
              <Button variant="secondary" onClick={() => { setDiagnosticResult(null); setDiagnosticError(null) }}>Kapat</Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  )
}
