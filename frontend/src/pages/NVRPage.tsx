// NVR cihazı yönetimi sayfası — listeleme, ekleme, düzenleme, silme, kanal tarama ve seçili içe aktarma
import { useMemo, useState, useEffect, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Trash2, Search, Download, Pencil, Power } from 'lucide-react'
import { nvrsApi, type NVRUpdate } from '../api/nvrs'
import { usePermissions } from '../hooks/usePermissions'
import { Table } from '../components/ui/Table'
import { Button } from '../components/ui/Button'
import { Badge } from '../components/ui/Badge'
import { Modal } from '../components/ui/Modal'
import { Input } from '../components/ui/Input'
import { Spinner } from '../components/ui/Spinner'
import { ConfirmDialog } from '../components/ui/ConfirmDialog'
import { PasswordInput } from '../components/ui/PasswordInput'
import { useToastStore } from '../stores/toastStore'
import type { NVR, NVRCreate, NVRChannelInfo, NVRProbeDiagnostics } from '../types/api'

type NVRBulkAddPayload = NVRCreate[]

/** API hatasını kullanıcıya okunabilir tek cümleye çevirir. */
function getErrorMessage(error: unknown, fallback: string): string {
  const err = error as { response?: { data?: { detail?: string } }; message?: string }
  if (!err.response && err.message === 'Network Error') {
    return 'Backend yanıt vermedi veya işlem zaman aşımına uğradı. Backend servisinin açık olduğunu ve NVR/kamera RTSP portlarının erişilebilir olduğunu kontrol edin.'
  }
  return err.response?.data?.detail || err.message || fallback
}

/** Yeni NVR ekleme modal'ı */
function AddNVRModal({
  open,
  onClose,
  initialValues,
}: {
  open: boolean
  onClose: () => void
  initialValues?: { host: string; port: number; username?: string; password?: string; brand?: string } | null
}) {
  const qc = useQueryClient()
  const showToast = useToastStore((state) => state.showToast)
  const [form, setForm] = useState<NVRCreate>({ name: '', host: '', onvif_port: 80 })

  // initialValues değiştiğinde veya modal açıldığında formu prefill et
  useEffect(() => {
    if (initialValues) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setForm({
        name: `${initialValues.brand || 'NVR'} (${initialValues.host})`,
        host: initialValues.host,
        onvif_port: initialValues.port,
        username: initialValues.username || '',
        password: initialValues.password || '',
        brand: initialValues.brand,
      })
    } else {
      setForm({ name: '', host: '', onvif_port: 80, username: '', password: '' })
    }
  }, [initialValues, open])

  const { mutate, isPending, error } = useMutation({
    mutationFn: nvrsApi.add,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['nvrs'] })
      showToast({ variant: 'success', title: 'NVR eklendi', description: form.name })
      onClose()
      setForm({ name: '', host: '', onvif_port: 80, username: '', password: '' })
    },
    onError: (err) => showToast({ variant: 'danger', title: 'NVR eklenemedi', description: getErrorMessage(err, 'Kayit cihazi eklenemedi.') }),
  })

  const set = (field: keyof NVRCreate, value: string | number) =>
    setForm((f) => ({ ...f, [field]: value }))

  return (
    <Modal open={open} onClose={onClose} title="NVR Ekle">
      <form onSubmit={(e) => { e.preventDefault(); mutate(form) }} className="flex flex-col gap-4">
        <div className="rounded-lg border border-[var(--border)] bg-[var(--bg-secondary)] px-3 py-2">
          <p className="text-xs text-[var(--text-secondary)] leading-5">
            NVR kaydı yönetim bağlantısını saklar. Kanal tarama sırasında önce ONVIF profilleri, gerekirse bilinen RTSP kanal yolları denenir.
          </p>
        </div>
        <Input label="Ad" value={form.name} onChange={(e) => set('name', e.target.value)} required />
        <Input label="IP / Host" value={form.host} onChange={(e) => set('host', e.target.value)} required placeholder="192.168.1.200" />
        <Input label="ONVIF Port" type="number" value={form.onvif_port ?? 80} onChange={(e) => set('onvif_port', Number(e.target.value))} />
        <Input label="Kullanıcı Adı" value={form.username ?? ''} onChange={(e) => set('username', e.target.value)} />
        <PasswordInput label="Şifre" value={form.password ?? ''} onChange={(e) => set('password', e.target.value)} />
        {error && <p className="text-xs text-[var(--danger)]">{getErrorMessage(error, 'NVR eklenemedi.')}</p>}
        <div className="flex gap-3 justify-end mt-1">
          <Button variant="secondary" type="button" onClick={onClose}>İptal</Button>
          <Button type="submit" loading={isPending}>Ekle</Button>
        </div>
      </form>
    </Modal>
  )
}

/** Mevcut NVR'ı düzenleme modal'ı */
function EditNVRModal({ nvr, onClose }: { nvr: NVR | null; onClose: () => void }) {
  const qc = useQueryClient()
  const showToast = useToastStore((state) => state.showToast)
  const [form, setForm] = useState<NVRUpdate>({})
  const [lastId, setLastId] = useState<number | null>(null)

  if (nvr && nvr.id !== lastId) {
    setLastId(nvr.id)
    setForm({
      name: nvr.name,
      host: nvr.host,
      onvif_port: nvr.onvif_port,
      username: nvr.username ?? '',
    })
  }

  const { mutate, isPending, error } = useMutation({
    mutationFn: (payload: NVRUpdate) => nvrsApi.update(nvr!.id, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['nvrs'] })
      showToast({ variant: 'success', title: 'NVR guncellendi', description: nvr?.name })
      onClose()
    },
    onError: (err) => showToast({ variant: 'danger', title: 'NVR guncellenemedi', description: getErrorMessage(err, 'Kayit cihazi bilgileri kaydedilemedi.') }),
  })

  if (!nvr) return null

  return (
    <Modal open onClose={onClose} title={`Düzenle — ${nvr.name}`}>
      <form onSubmit={(e) => { e.preventDefault(); mutate(form) }} className="flex flex-col gap-4">
        <Input label="Ad" value={form.name ?? ''} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} required />
        <Input label="IP / Host" value={form.host ?? ''} onChange={(e) => setForm((f) => ({ ...f, host: e.target.value }))} required />
        <Input label="ONVIF Port" type="number" value={form.onvif_port ?? 80} onChange={(e) => setForm((f) => ({ ...f, onvif_port: Number(e.target.value) }))} />
        <Input label="Kullanıcı Adı" value={form.username ?? ''} onChange={(e) => setForm((f) => ({ ...f, username: e.target.value }))} />
        <PasswordInput label="Yeni Şifre" placeholder="Değiştirmek için doldurun" onChange={(e) => setForm((f) => ({ ...f, password: e.target.value || undefined }))} />
        {error && <p className="text-xs text-[var(--danger)]">{getErrorMessage(error, 'Kayit cihazi bilgileri kaydedilemedi.')}</p>}
        <div className="flex gap-3 justify-end mt-1">
          <Button variant="secondary" type="button" onClick={onClose}>İptal</Button>
          <Button type="submit" loading={isPending}>Kaydet</Button>
        </div>
      </form>
    </Modal>
  )
}

/** ONVIF veya RTSP kanal önizleme ve seçili/tümü içe aktarma modal'ı */
function ChannelModal({
  nvr, open, onClose,
}: {
  nvr: NVR | null
  open: boolean
  onClose: () => void
}) {
  const qc = useQueryClient()
  const showToast = useToastStore((state) => state.showToast)
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [channels, setChannels] = useState<NVRChannelInfo[]>([])
  const [diagnostics, setDiagnostics] = useState<NVRProbeDiagnostics | null>(null)
  const [importMessage, setImportMessage] = useState<string | null>(null)

  const { mutate: scanChannels, isPending, error } = useMutation({
    mutationFn: () => nvrsApi.probeDiagnostics(nvr!.id),
    onSuccess: (data) => {
      setImportMessage(null)
      setDiagnostics(data)
      setChannels(data.channels)
      setSelected(new Set(data.channels.map((c) => c.profile_token)))
    },
  })

  // Modal her açıldığında taramayı başlat
  useEffect(() => {
    if (open && nvr) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setChannels([])
      setDiagnostics(null)
      setSelected(new Set())
      setImportMessage(null)
      scanChannels()
    }
  }, [open, nvr, scanChannels])

  const toggle = (token: string) =>
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(token)) {
        next.delete(token)
      } else {
        next.add(token)
      }
      return next
    })

  const allSelected = channels.length > 0 && selected.size === channels.length
  const toggleAll = () =>
    setSelected(allSelected ? new Set() : new Set(channels.map((c) => c.profile_token)))

  const importSelected = useMutation({
    mutationFn: (selectedChannels: NVRChannelInfo[]) =>
      nvrsApi.importSelected(nvr!.id, selectedChannels),
    onSuccess: (imported) => {
      qc.invalidateQueries({ queryKey: ['cameras'] })
      setImportMessage(`${imported.length} kamera başarıyla eklendi. Kameralar sayfasından izlemeye alabilirsiniz.`)
      showToast({ variant: 'success', title: 'Kanallar aktarildi', description: `${imported.length} kamera eklendi.` })
    },
    onError: (err) => showToast({ variant: 'danger', title: 'Kanallar aktarilamadi', description: getErrorMessage(err, 'NVR kanallari kamera olarak eklenemedi.') }),
  })

  return (
    <Modal open={open} onClose={onClose} title={`${nvr?.name || 'NVR'} — Kanalları Tara`} width="max-w-2xl">
      <div className="flex flex-col gap-4">
        {isPending && (
          <div className="flex flex-col items-center justify-center py-12 gap-2">
            <Spinner size="lg" />
            <p className="text-sm text-[var(--text-primary)] font-medium mt-2">NVR kanalları taranıyor...</p>
            <p className="text-xs text-[var(--text-secondary)] text-center max-w-sm">
              Önce ONVIF bağlantısı sorgulanıyor, yanıt alınamazsa standart RTSP kanalları otomatik taranacaktır.
            </p>
          </div>
        )}

        {error && (
          <div className="flex flex-col items-center justify-center py-8 gap-3">
            <p className="text-sm text-[var(--danger)] text-center font-medium">
              {getErrorMessage(error, 'Tarama sırasında hata oluştu.')}
            </p>
            <p className="text-xs text-[var(--text-secondary)] text-center max-w-md">
              Cihazın yerel ağda aktif olduğundan, IP adresinin, portunun ve kullanıcı adı/şifre bilgilerinin doğru olduğundan emin olun.
            </p>
            <Button variant="secondary" size="sm" onClick={() => scanChannels()}>Yeniden Dene</Button>
          </div>
        )}

        {!isPending && !error && (
          <>
            {diagnostics && (
              <div className={`rounded-lg border px-3 py-2 text-xs ${
                diagnostics.onvif_ok
                  ? 'border-[var(--success)]/30 bg-[var(--success)]/10 text-[var(--success)]'
                  : diagnostics.fallback_used && diagnostics.channels.length > 0
                  ? 'border-[var(--warning)]/30 bg-[var(--warning)]/10 text-[var(--warning)]'
                  : 'border-[var(--danger)]/30 bg-[var(--danger)]/10 text-[var(--danger)]'
              }`}>
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant={diagnostics.onvif_ok ? 'success' : diagnostics.channels.length > 0 ? 'warning' : 'danger'}>
                    {diagnostics.onvif_ok ? 'ONVIF Başarılı' : diagnostics.channels.length > 0 ? 'RTSP Fallback' : 'Kanal Bulunamadı'}
                  </Badge>
                  <span>
                    {diagnostics.onvif_ok
                      ? `${diagnostics.stream_uri_count} ONVIF stream URI alındı.`
                      : diagnostics.channels.length > 0
                      ? `ONVIF başarısız oldu, ${diagnostics.channels.length} kanal RTSP fallback ile bulundu.`
                      : 'ONVIF ve RTSP fallback kanal döndürmedi.'}
                  </span>
                </div>
                {!diagnostics.onvif_ok && diagnostics.onvif_error && (
                  <p className="mt-1 text-[11px] text-[var(--text-secondary)]">ONVIF hata: {diagnostics.onvif_error}</p>
                )}
                {diagnostics.fallback_error && (
                  <p className="mt-1 text-[11px] text-[var(--text-secondary)]">RTSP fallback hata: {diagnostics.fallback_error}</p>
                )}
              </div>
            )}

            {channels.length === 0 ? (
              <div className="text-center py-8 border border-dashed border-[var(--border)] rounded-lg text-[var(--text-secondary)] text-sm">
                Herhangi bir aktif kanal veya RTSP yayını tespit edilemedi.
              </div>
            ) : (
              <>
                <p className="text-xs text-[var(--text-secondary)]">
                  Sisteme eklemek istediğiniz kanalları seçin. Import sırasında bu listedeki gerçek RTSP URL,
                  host, port ve path bilgisi doğrulanır; ONVIF'in döndürdüğü kamera adresine ulaşılamazsa aynı path NVR host'u üzerinden denenir.
                </p>
                <div className="overflow-x-auto rounded-lg border border-[var(--border)] max-h-[300px] overflow-y-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="bg-[var(--bg-secondary)] border-b border-[var(--border)] sticky top-0 z-10">
                        <th className="px-3 py-2 text-left">
                          <input
                            type="checkbox"
                            checked={allSelected}
                            onChange={toggleAll}
                            className="rounded"
                            title="Tümünü seç / kaldır"
                          />
                        </th>
                        <th className="px-3 py-2 text-left text-xs text-[var(--text-secondary)]">Profil / Ad</th>
                        <th className="px-3 py-2 text-left text-xs text-[var(--text-secondary)]">Marka / Model</th>
                        <th className="px-3 py-2 text-left text-xs text-[var(--text-secondary)]">Kaynak</th>
                        <th className="px-3 py-2 text-left text-xs text-[var(--text-secondary)]">RTSP URL</th>
                      </tr>
                    </thead>
                    <tbody>
                      {channels.map((ch) => (
                        <tr
                          key={ch.profile_token}
                          className={`border-b border-[var(--border)] last:border-0 cursor-pointer transition-colors ${
                            selected.has(ch.profile_token) ? 'bg-[var(--accent)]/5' : ''
                          }`}
                          onClick={() => toggle(ch.profile_token)}
                        >
                          <td className="px-3 py-2" onClick={(e) => e.stopPropagation()}>
                            <input
                              type="checkbox"
                              checked={selected.has(ch.profile_token)}
                              onChange={() => toggle(ch.profile_token)}
                              className="rounded bg-[var(--bg-primary)] text-[var(--accent)] focus:ring-[var(--accent)]"
                            />
                          </td>
                          <td className="px-3 py-2 text-[var(--text-primary)] font-medium">{ch.profile_name}</td>
                          <td className="px-3 py-2 text-[var(--text-secondary)]">{ch.manufacturer ?? '—'} / {ch.model ?? '—'}</td>
                          <td className="px-3 py-2">
                            <Badge variant={ch.source === 'onvif' ? 'success' : 'warning'}>
                              {ch.source === 'onvif' ? 'ONVIF' : 'RTSP'}
                            </Badge>
                          </td>
                          <td className="px-3 py-2 text-[var(--text-secondary)] font-mono text-xs truncate max-w-[200px]" title={ch.rtsp_url}>{ch.rtsp_url}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            )}
            <div className="flex items-center justify-between mt-1">
              <div className="flex flex-col gap-1">
                <span className="text-xs text-[var(--text-secondary)]">
                  {selected.size} / {channels.length} kanal seçili
                </span>
                {importMessage && <span className="text-xs text-[var(--success)]">{importMessage}</span>}
                {importSelected.error && (
                  <span className="text-xs text-[var(--danger)]">
                    {getErrorMessage(importSelected.error, 'Kanallar eklenirken hata oluştu.')}
                  </span>
                )}
              </div>
              <div className="flex gap-3">
                <Button variant="secondary" onClick={onClose}>Kapat</Button>
                {channels.length > 0 && (
                  <Button
                    icon={<Download size={14} />}
                    loading={importSelected.isPending}
                    disabled={selected.size === 0}
                    onClick={() => {
                      const selectedList = channels.filter((ch) => selected.has(ch.profile_token))
                      importSelected.mutate(selectedList)
                    }}
                  >
                    {selected.size === channels.length ? 'Tümünü Ekle' : `${selected.size} Kanalı Ekle`}
                  </Button>
                )}
              </div>
            </div>
          </>
        )}
      </div>
    </Modal>
  )
}

interface DiscoveredNVRRow {
  host: string
  port: number
  brand: string
  model: string
  name: string
  onvif_port: number
  username?: string
  password?: string
  selected: boolean
}

/** Ağ cihazlarını keşfetme modal'ı */
function DiscoverModal({
  open,
  onClose,
}: {
  open: boolean
  onClose: () => void
}) {
  const qc = useQueryClient()
  const showToast = useToastStore((state) => state.showToast)
  const [activeTab, setActiveTab] = useState<'onvif' | 'range'>('range')
  const [results, setResults] = useState<DiscoveredNVRRow[]>([])

  // ONVIF Discovery
  const { isLoading: isOnvifLoading, refetch: refetchOnvif, isFetching: isOnvifFetching } = useQuery({
    queryKey: ['discovered_devices'],
    queryFn: async () => {
      const data = await nvrsApi.discover()
      setResults(
        data.map((item) => ({
          host: item.host,
          port: item.port,
          brand: 'ONVIF Cihazı',
          model: 'Network Video Recorder',
          name: `NVR_${item.host.replace(/\./g, '_')}`,
          onvif_port: item.port,
          username: 'admin',
          password: '',
          selected: true,
        }))
      )
      return data
    },
    enabled: open && activeTab === 'onvif',
    staleTime: 0,
  })

  // Range Scan
  const [ipRange, setIpRange] = useState('192.168.1.0/24')
  const [rtspPort, setRtspPort] = useState(554)
  const [username, setUsername] = useState('admin')
  const [password, setPassword] = useState('admin123')

  const rangeAbortRef = useRef<AbortController | null>(null)

  const { mutate: scanRange, isPending: isRangeScanning, error: rangeError, reset: resetRangeScan } = useMutation({
    mutationFn: () => {
      rangeAbortRef.current = new AbortController()
      return nvrsApi.scan({ ip_range: ipRange, rtsp_port: rtspPort, username, password }, rangeAbortRef.current.signal)
    },
    onSuccess: (data) => {
      setResults(
        data.map((item) => ({
          host: item.host,
          port: item.port,
          brand: item.brand,
          model: item.model,
          name: `${item.brand || 'NVR'} (${item.host})`,
          onvif_port: 80,
          username: username,
          password: password,
          selected: true,
        }))
      )
    },
    onError: () => {
      if (rangeAbortRef.current?.signal.aborted) resetRangeScan()
    },
  })

  const handleStopRangeScan = () => rangeAbortRef.current?.abort()

  const { mutate: saveNVRS, isPending: isSaving, error: saveError } = useMutation({
    mutationFn: (payload: NVRBulkAddPayload) => nvrsApi.bulkAdd(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['nvrs'] })
      showToast({ variant: 'success', title: 'NVR kayitlari eklendi', description: `${results.filter((r) => r.selected).length} kayit cihazi kaydedildi.` })
      onClose()
      setResults([])
    },
    onError: (err) => showToast({ variant: 'danger', title: 'NVR kayitlari eklenemedi', description: getErrorMessage(err, 'Toplu NVR ekleme sirasinda hata olustu.') }),
  })

  // Modal kapandığında state temizle
  useEffect(() => {
    if (!open) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setResults([])
    }
  }, [open])

  const toggleSelect = (index: number) => {
    setResults((prev) =>
      prev.map((item, idx) => (idx === index ? { ...item, selected: !item.selected } : item))
    )
  }

  const toggleSelectAll = () => {
    const allSelected = results.every((r) => r.selected)
    setResults((prev) => prev.map((item) => ({ ...item, selected: !allSelected })))
  }

  const handleFieldChange = (index: number, field: keyof DiscoveredNVRRow, value: string | number | boolean) => {
    setResults((prev) =>
      prev.map((item, idx) => (idx === index ? { ...item, [field]: value } : item))
    )
  }

  const handleSave = () => {
    const selectedList = results
      .filter((r) => r.selected)
      .map((r) => ({
        name: r.name,
        host: r.host,
        onvif_port: r.onvif_port,
        username: r.username,
        password: r.password,
        brand: r.brand,
        model: r.model,
      }))
    if (selectedList.length === 0) return
    saveNVRS(selectedList)
  }

  return (
    <Modal open={open} onClose={onClose} title="Ağdaki NVR Cihazlarını Keşfet" width="max-w-4xl">
      <div className="flex flex-col gap-4">
        {/* Sekmeler */}
        <div className="flex border-b border-[var(--border)] mb-2">
          <button
            type="button"
            className={`px-4 py-2 text-sm font-semibold border-b-2 transition-colors cursor-pointer ${
              activeTab === 'range'
                ? 'border-[var(--accent)] text-[var(--text-primary)]'
                : 'border-transparent text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
            }`}
            onClick={() => { setActiveTab('range'); setResults([]); }}
          >
            IP Aralığı ile NVR Tara (VideoEdge / Diğerleri)
          </button>
          <button
            type="button"
            className={`px-4 py-2 text-sm font-semibold border-b-2 transition-colors cursor-pointer ${
              activeTab === 'onvif'
                ? 'border-[var(--accent)] text-[var(--text-primary)]'
                : 'border-transparent text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
            }`}
            onClick={() => { setActiveTab('onvif'); setResults([]); refetchOnvif(); }}
          >
            Otomatik ONVIF Keşfi
          </button>
        </div>

        {/* ONVIF Tab Form */}
        {activeTab === 'onvif' && (
          <div className="flex justify-between items-center gap-4">
            <p className="text-xs text-[var(--text-secondary)]">
              WS-Discovery protokolü kullanılarak yerel ağdaki ONVIF destekli NVR ve kamera cihazları otomatik aranır.
            </p>
            <Button size="sm" variant="secondary" onClick={() => refetchOnvif()} loading={isOnvifLoading || isOnvifFetching}>
              Yeniden Tara
            </Button>
          </div>
        )}

        {/* Range Scan Tab Form */}
        {activeTab === 'range' && (
          <div className="flex flex-col gap-3">
            <div className="rounded-lg border border-[var(--border)] bg-[var(--bg-secondary)] px-3 py-2">
              <p className="text-xs text-[var(--text-secondary)] leading-5">
                IP aralığı taraması NVR'ın RTSP kanal yollarını test eder. ONVIF keşfi sonuç vermeyen VideoEdge,
                Hikvision veya Dahua benzeri cihazlarda bu yöntemi kullanın.
              </p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="flex flex-col gap-3">
                <Input
                  label="Ağ IP Aralığı"
                  value={ipRange}
                  onChange={(e) => setIpRange(e.target.value)}
                  placeholder="192.168.1.0/24 veya 192.168.1.50-100"
                  required
                />
                <Input
                  label="RTSP Port"
                  type="number"
                  value={rtspPort}
                  onChange={(e) => setRtspPort(Number(e.target.value))}
                />
              </div>
              <div className="flex flex-col gap-3">
                <Input
                  label="Tarama Kullanıcı Adı"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                />
                <PasswordInput
                  label="Tarama Şifresi"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </div>
            </div>
            <div className="flex justify-end border-b border-[var(--border)] pb-3">
              <Button onClick={() => scanRange()} loading={isRangeScanning} icon={<Search size={15} />}>
                NVR Ara
              </Button>
            </div>
          </div>
        )}

        {/* Sonuçların Listelenmesi (Checkbox, İsim, Port ve Şifre Özelleştirme) */}
        {(isRangeScanning || isOnvifLoading || isOnvifFetching) ? (
          <div className="flex flex-col items-center justify-center py-12 gap-3">
            <Spinner size="md" />
            <span className="text-xs text-[var(--text-secondary)]">Cihazlar taranıyor, lütfen bekleyin...</span>
            {isRangeScanning && (
              <Button variant="secondary" size="sm" onClick={handleStopRangeScan}>
                Durdur
              </Button>
            )}
          </div>
        ) : results.length > 0 ? (
          <div className="flex flex-col gap-3">
            <div className="flex items-center justify-between text-xs text-[var(--text-secondary)] font-medium border-b border-[var(--border)] pb-2 px-1">
              <label className="flex items-center gap-2 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={results.every((r) => r.selected)}
                  onChange={toggleSelectAll}
                  className="rounded border-[var(--border)] bg-[var(--bg-primary)] text-[var(--accent)] focus:ring-[var(--accent)] h-4 w-4"
                />
                <span>Hepsini Seç ({results.length} NVR bulundu)</span>
              </label>
              <span>Eklenecek NVR isimlerini ve kimlik bilgilerini değiştirebilirsiniz.</span>
            </div>

            <div className="flex flex-col gap-2 max-h-[300px] overflow-y-auto pr-1">
              {results.map((row, index) => (
                <div
                  key={index}
                  className="flex flex-col gap-2 p-3 rounded-lg border border-[var(--border)] bg-[var(--bg-card)] hover:bg-[var(--bg-hover)] transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <input
                        type="checkbox"
                        checked={row.selected}
                        onChange={() => toggleSelect(index)}
                        className="rounded border-[var(--border)] bg-[var(--bg-primary)] text-[var(--accent)] focus:ring-[var(--accent)] h-4 w-4 cursor-pointer"
                      />
                      <span className="text-sm font-semibold text-[var(--text-primary)]">{row.host}</span>
                      <Badge variant="neutral">{row.brand}</Badge>
                    </div>
                    <span className="text-[10px] text-[var(--text-secondary)]">{row.model}</span>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-4 gap-2 mt-1">
                    <Input
                      placeholder="Cihaz Adı"
                      value={row.name}
                      onChange={(e) => handleFieldChange(index, 'name', e.target.value)}
                    />
                    <Input
                      placeholder="ONVIF Port"
                      type="number"
                      value={row.onvif_port}
                      onChange={(e) => handleFieldChange(index, 'onvif_port', Number(e.target.value))}
                    />
                    <Input
                      placeholder="Kullanıcı Adı"
                      value={row.username ?? ''}
                      onChange={(e) => handleFieldChange(index, 'username', e.target.value)}
                    />
                    <PasswordInput
                      placeholder="Şifre"
                      value={row.password ?? ''}
                      onChange={(e) => handleFieldChange(index, 'password', e.target.value)}
                    />
                  </div>
                </div>
              ))}
            </div>

            {saveError && (
              <p className="text-xs text-[var(--danger)]">
                {getErrorMessage(saveError, "NVR'lar eklenirken hata oluştu.")}
              </p>
            )}

            <div className="flex justify-end gap-3 pt-3 border-t border-[var(--border)]">
              <Button variant="secondary" onClick={onClose} disabled={isSaving}>
                Kapat
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
        ) : (
          <div className="text-center py-12 border border-dashed border-[var(--border)] rounded-lg text-[var(--text-secondary)] text-sm">
            {activeTab === 'onvif'
              ? 'Ağda otomatik ONVIF cihazı bulunamadı. Cihazlarınız ONVIF desteklemiyorsa veya farklı ağdaysa yan sekmeyi kullanın.'
              : 'Ağda taranmış NVR bulunamadı. Lütfen ağ IP aralığını yazarak arama yapın.'}
          </div>
        )}

        {rangeError && (
          <div className="p-3 rounded bg-red-500/10 border border-red-500/20 text-xs text-[var(--danger)]">
            {getErrorMessage(rangeError, 'NVR tarama sırasında hata oluştu.')}
          </div>
        )}
      </div>
    </Modal>
  )
}

/** NVR yönetim sayfası */
export function NVRPage() {
  const [showAdd, setShowAdd] = useState(false)
  const [showDiscover, setShowDiscover] = useState(false)
  const [prefilledDevice, setPrefilledDevice] = useState<{ host: string; port: number; username?: string; password?: string; brand?: string } | null>(null)
  const [editNVR, setEditNVR] = useState<NVR | null>(null)
  const [activeNvrForScan, setActiveNvrForScan] = useState<NVR | null>(null)
  const [nvrSearch, setNvrSearch] = useState('')
  const [nvrStatusFilter, setNvrStatusFilter] = useState<'all' | 'active' | 'inactive'>('all')
  const [deleteTarget, setDeleteTarget] = useState<NVR | null>(null)
  const qc = useQueryClient()
  const { canManageNVRs } = usePermissions()
  const showToast = useToastStore((state) => state.showToast)

  const { data: nvrs = [], isLoading } = useQuery({
    queryKey: ['nvrs'],
    queryFn: nvrsApi.list,
  })

  const filteredNvrs = useMemo(() => {
    const needle = nvrSearch.trim().toLowerCase()
    return nvrs.filter((nvr) => {
      const matchesSearch = !needle || [
        nvr.name,
        nvr.host,
        nvr.brand ?? '',
        nvr.model ?? '',
        nvr.username ?? '',
      ].some((value) => value.toLowerCase().includes(needle))
      const matchesStatus =
        nvrStatusFilter === 'all' ||
        (nvrStatusFilter === 'active' && nvr.is_active) ||
        (nvrStatusFilter === 'inactive' && !nvr.is_active)
      return matchesSearch && matchesStatus
    })
  }, [nvrSearch, nvrStatusFilter, nvrs])

  const hasNvrFilter = nvrSearch.trim() !== '' || nvrStatusFilter !== 'all'

  const resetNvrFilters = () => {
    setNvrSearch('')
    setNvrStatusFilter('all')
  }

  /** NVR aktiflik durumunu değiştirir */
  const toggleStatus = useMutation({
    mutationFn: ({ id, isActive }: { id: number; isActive: boolean }) =>
      nvrsApi.toggleStatus(id, isActive),
    onSuccess: (nvr) => {
      qc.invalidateQueries({ queryKey: ['nvrs'] })
      showToast({ variant: 'success', title: 'NVR durumu guncellendi', description: nvr.name })
    },
    onError: (err) => showToast({ variant: 'danger', title: 'NVR durumu guncellenemedi', description: getErrorMessage(err, 'Kayit cihazi durumu degistirilemedi.') }),
  })

  /** NVR'ı sistemden siler */
  const deleteNvr = useMutation({
    mutationFn: nvrsApi.delete,
    onSuccess: () => {
      showToast({ variant: 'success', title: 'NVR silindi', description: deleteTarget?.name })
      setDeleteTarget(null)
      qc.invalidateQueries({ queryKey: ['nvrs'] })
    },
    onError: (err) => showToast({ variant: 'danger', title: 'NVR silinemedi', description: getErrorMessage(err, 'Silme islemi tamamlanamadi.') }),
  })

  const columns = [
    { key: 'name', header: 'Ad', render: (n: NVR) => <span className="font-medium">{n.name}</span> },
    { key: 'host', header: 'Host', render: (n: NVR) => (
      <span className="font-mono text-xs text-[var(--text-secondary)]">{n.host}:{n.onvif_port}</span>
    )},
    { key: 'brand', header: 'Marka', render: (n: NVR) => n.brand ?? '—' },
    {
      key: 'status',
      header: 'Durum',
      render: (n: NVR) => <Badge variant={n.is_active ? 'success' : 'neutral'}>{n.is_active ? 'Aktif' : 'Pasif'}</Badge>,
    },
    {
      key: 'actions',
      header: '',
      width: '220px',
      render: (n: NVR) => (
        <div className="flex items-center gap-1.5">
          {canManageNVRs && (
            <>
              <Button size="sm" variant="secondary" icon={<Pencil size={12} />} onClick={() => setEditNVR(n)}>
                Düzenle
              </Button>
              <Button
                size="sm"
                variant="secondary"
                icon={<Power size={12} />}
                loading={toggleStatus.isPending && toggleStatus.variables?.id === n.id}
                onClick={() => toggleStatus.mutate({ id: n.id, isActive: !n.is_active })}
              >
                {n.is_active ? 'Pasifleştir' : 'Aktifleştir'}
              </Button>
            </>
          )}
          <Button
            size="sm"
            variant="secondary"
            icon={<Search size={12} />}
            onClick={() => setActiveNvrForScan(n)}
          >
            Tara
          </Button>
          {canManageNVRs && (
            <Button
              size="sm"
              variant="danger"
              icon={<Trash2 size={12} />}
              loading={deleteNvr.isPending && deleteNvr.variables === n.id}
              onClick={() => setDeleteTarget(n)}
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
          <h1 className="text-xl font-bold text-[var(--text-primary)]">Kayit Cihazlari</h1>
          <p className="text-sm text-[var(--text-secondary)] mt-0.5">
            {filteredNvrs.length} / {nvrs.length} kayıt cihazı
          </p>
        </div>
        <div className="flex gap-2">
          {canManageNVRs && (
            <>
              <Button variant="secondary" icon={<Search size={15} />} onClick={() => setShowDiscover(true)}>
                Ağdaki Cihazları Tara
              </Button>
              <Button icon={<Plus size={15} />} onClick={() => { setPrefilledDevice(null); setShowAdd(true); }}>
                Kayit Cihazi Ekle
              </Button>
            </>
          )}
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <Input
          value={nvrSearch}
          onChange={(e) => setNvrSearch(e.target.value)}
          placeholder="Kayit cihazi adi, IP, marka veya model ara"
          className="w-full sm:w-80"
        />
        <select
          value={nvrStatusFilter}
          onChange={(e) => setNvrStatusFilter(e.target.value as 'all' | 'active' | 'inactive')}
          className="rounded-lg border border-[var(--border)] bg-[var(--bg-card)] px-3 py-2 text-sm text-[var(--text-primary)] outline-none transition-colors focus:border-[var(--accent)]"
        >
          <option value="all">Tum Durumlar</option>
          <option value="active">Aktif</option>
          <option value="inactive">Pasif</option>
        </select>
        {hasNvrFilter && (
          <Button size="sm" variant="secondary" onClick={resetNvrFilters}>
            Filtreleri Sifirla
          </Button>
        )}
      </div>

      {isLoading ? (
        <div className="flex justify-center py-16"><Spinner size="lg" /></div>
      ) : (
        <Table columns={columns} data={filteredNvrs} keyFn={(n) => n.id} emptyText={hasNvrFilter ? 'Filtrelerle eslesen NVR bulunamadi.' : 'Henüz NVR eklenmedi.'} />
      )}

      <AddNVRModal open={showAdd} onClose={() => { setShowAdd(false); setPrefilledDevice(null); }} initialValues={prefilledDevice} />
      <EditNVRModal nvr={editNVR} onClose={() => setEditNVR(null)} />
      <ConfirmDialog
        open={deleteTarget !== null}
        title="NVR Sil"
        description={deleteTarget ? `"${deleteTarget.name}" kayit cihazi silinecek. Bagli kameralar NVR baglantisini kaybedebilir.` : ''}
        confirmLabel="Sil"
        loading={deleteNvr.isPending}
        onClose={() => !deleteNvr.isPending && setDeleteTarget(null)}
        onConfirm={() => deleteTarget && deleteNvr.mutate(deleteTarget.id)}
      />
      <DiscoverModal
        open={showDiscover}
        onClose={() => setShowDiscover(false)}
      />
      <ChannelModal
        nvr={activeNvrForScan}
        open={activeNvrForScan !== null}
        onClose={() => setActiveNvrForScan(null)}
      />
    </div>
  )
}
