// Kullanıcı yönetimi sayfası — listeleme, ekleme, düzenleme (rol/aktiflik/şifre), silme
import { useMemo, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Activity, Download, Moon, Plus, Pencil, Sun, Trash2, Volume2 } from 'lucide-react'
import dayjs from 'dayjs'
import { systemApi } from '../api/system'
import { usersApi, type UserUpdate } from '../api/users'
import { usePermissions } from '../hooks/usePermissions'
import { useAuthStore } from '../stores/authStore'
import { useSystemSettingsStore } from '../stores/systemSettingsStore'
import { Table } from '../components/ui/Table'
import { Button } from '../components/ui/Button'
import { Badge } from '../components/ui/Badge'
import { Modal } from '../components/ui/Modal'
import { Input } from '../components/ui/Input'
import { Toggle } from '../components/ui/Toggle'
import { Spinner } from '../components/ui/Spinner'
import { ConfirmDialog } from '../components/ui/ConfirmDialog'
import { PaginationControls } from '../components/ui/PaginationControls'
import { PasswordInput } from '../components/ui/PasswordInput'
import { useToastStore } from '../stores/toastStore'
import { getApiErrorMessage } from '../utils/apiError'
import { hasErrors, requiredText, validateNewPassword, type FieldErrors } from '../utils/formValidation'
import type { AuditEvent, User, UserCreate } from '../types/api'

/** Yeni kullanıcı ekleme modal'ı */
function AddUserModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const qc = useQueryClient()
  const showToast = useToastStore((state) => state.showToast)
  const [form, setForm] = useState<UserCreate>({ username: '', password: '', role: 'viewer' })
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({})

  const { mutate, isPending, error } = useMutation({
    mutationFn: usersApi.add,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['users'] })
      showToast({ variant: 'success', title: 'Kullanici eklendi', description: form.username })
      onClose()
      setForm({ username: '', password: '', role: 'viewer' })
      setFieldErrors({})
    },
    onError: (err) => showToast({ variant: 'danger', title: 'Kullanici eklenemedi', description: getApiErrorMessage(err, 'Kullanici adi, sifre ve rol bilgisini kontrol edin.') }),
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const errors: FieldErrors = {}
    const usernameError = requiredText(form.username, 'Kullanici adi zorunludur.')
    const passwordError = validateNewPassword(form.password, true)
    if (usernameError) errors.username = usernameError
    if (passwordError) errors.password = passwordError
    setFieldErrors(errors)
    if (!hasErrors(errors)) mutate(form)
  }

  return (
    <Modal open={open} onClose={onClose} title="Kullanıcı Ekle">
      <form onSubmit={handleSubmit} noValidate className="flex flex-col gap-4">
        <Input label="Kullanıcı Adı" value={form.username} onChange={(e) => setForm((f) => ({ ...f, username: e.target.value }))} required error={fieldErrors.username} />
        <PasswordInput label="Şifre" value={form.password} onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))} required error={fieldErrors.password} />
        <RoleSelect value={form.role} onChange={(role) => setForm((f) => ({ ...f, role }))} />
        {error && <p className="text-xs text-[var(--danger)]">{getApiErrorMessage(error, 'Kullanici adi, sifre ve rol bilgisini kontrol edin.')}</p>}
        <div className="flex gap-3 justify-end mt-1">
          <Button variant="secondary" type="button" onClick={onClose}>İptal</Button>
          <Button type="submit" loading={isPending}>Ekle</Button>
        </div>
      </form>
    </Modal>
  )
}

/** Kullanıcı düzenleme modal'ı — rol, aktiflik durumu ve şifre güncellenebilir */
function EditUserModal({ user, onClose }: { user: User | null; onClose: () => void }) {
  const qc = useQueryClient()
  const showToast = useToastStore((state) => state.showToast)
  const [form, setForm] = useState<UserUpdate>({})
  const [lastId, setLastId] = useState<number | null>(null)
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({})
  const currentUsername = useAuthStore((s) => s.username)

  if (user && user.id !== lastId) {
    setLastId(user.id)
    setForm({ role: user.role, is_active: user.is_active })
    setFieldErrors({})
  }

  const { mutate, isPending, error } = useMutation({
    mutationFn: (payload: UserUpdate) => usersApi.update(user!.id, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['users'] })
      showToast({ variant: 'success', title: 'Kullanici guncellendi', description: user?.username })
      onClose()
    },
    onError: (err) => showToast({ variant: 'danger', title: 'Kullanici guncellenemedi', description: getApiErrorMessage(err, 'Rol, aktiflik veya sifre degisikligi kaydedilemedi.') }),
  })

  if (!user) return null

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const errors: FieldErrors = {}
    const passwordError = validateNewPassword(form.password, false)
    if (passwordError) errors.password = passwordError
    setFieldErrors(errors)
    if (!hasErrors(errors)) mutate(form)
  }

  // Kendi hesabını devre dışı bırakmasını engelle
  const isSelf = user.username === currentUsername

  return (
    <Modal open onClose={onClose} title={`Düzenle — ${user.username}`}>
      <form onSubmit={handleSubmit} noValidate className="flex flex-col gap-4">
        <RoleSelect value={form.role ?? user.role} onChange={(role) => setForm((f) => ({ ...f, role }))} />

        <div className="flex items-center justify-between py-1">
          <div>
            <p className="text-sm font-medium text-[var(--text-primary)]">Aktif</p>
            <p className="text-xs text-[var(--text-secondary)]">Pasif kullanıcı giriş yapamaz</p>
          </div>
          <Toggle
            checked={form.is_active ?? user.is_active}
            disabled={isSelf}  // kendi hesabını kapatamaz
            onChange={(v) => setForm((f) => ({ ...f, is_active: v }))}
          />
        </div>

        <PasswordInput
          label="Yeni Şifre"
          placeholder="Değiştirmek için doldurun"
          onChange={(e) => setForm((f) => ({ ...f, password: e.target.value || undefined }))}
          error={fieldErrors.password}
        />

        {isSelf && (
          <p className="text-xs text-[var(--warning)]">Kendi hesabınızı devre dışı bırakamazsınız.</p>
        )}
        {error && <p className="text-xs text-[var(--danger)]">{getApiErrorMessage(error, 'Rol, aktiflik veya sifre degisikligi kaydedilemedi.')}</p>}
        <div className="flex gap-3 justify-end mt-1">
          <Button variant="secondary" type="button" onClick={onClose}>İptal</Button>
          <Button type="submit" loading={isPending}>Kaydet</Button>
        </div>
      </form>
    </Modal>
  )
}

/** Rol seçimi için ortak select bileşeni */
function RoleSelect({ value, onChange }: { value: string; onChange: (role: string) => void }) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-sm font-medium text-[var(--text-secondary)]">Rol</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-lg px-3 py-2 text-sm bg-[var(--bg-primary)] border border-[var(--border)] text-[var(--text-primary)] outline-none focus:border-[var(--accent)] transition-colors"
      >
        <option value="admin">Admin — Tam yetki</option>
        <option value="operator">Operatör — Kamera/NVR yönetimi, alarm onaylama</option>
        <option value="viewer">İzleyici — Yalnızca görüntüleme ve inceleme</option>
      </select>
    </div>
  )
}

const roleVariant = (role: string) => {
  if (role === 'admin') return 'danger'
  if (role === 'operator') return 'warning'
  return 'neutral'
}

const EMPTY_USERS: User[] = []

const roleLabel = { admin: 'Admin', operator: 'Operatör', viewer: 'İzleyici' } as Record<string, string>

const auditEventMetadataText = (event: AuditEvent) => {
  const metadata = JSON.stringify(event.metadata ?? {})
  return metadata === '{}' ? '-' : metadata
}

const auditEventHashLabel = (event: AuditEvent) => event.event_hash?.slice(0, 12) ?? '-'

/** İnsan tespiti sesli uyarı ayarlarını düzenler. */
function GeneralSettingsPanel() {
  const themeMode = useSystemSettingsStore((s) => s.themeMode)
  const setThemeMode = useSystemSettingsStore((s) => s.setThemeMode)
  const soundEnabled = useSystemSettingsStore((s) => s.humanDetectionSoundEnabled)
  const soundDuration = useSystemSettingsStore((s) => s.humanDetectionSoundDurationSeconds)
  const setSoundEnabled = useSystemSettingsStore((s) => s.setHumanDetectionSoundEnabled)
  const setSoundDuration = useSystemSettingsStore((s) => s.setHumanDetectionSoundDurationSeconds)

  return (
    <section className="bg-[var(--bg-card)] border border-[var(--border)] rounded-xl p-4">
      <div className="mb-5 flex items-start justify-between gap-4 border-b border-[var(--border)] pb-4">
        <div className="flex items-start gap-3">
          <div className="mt-0.5 rounded-lg bg-[var(--accent)]/10 p-2 text-[var(--accent)]">
            {themeMode === 'dark' ? <Moon size={18} /> : <Sun size={18} />}
          </div>
          <div>
            <h2 className="text-sm font-semibold text-[var(--text-primary)]">Arayuz Temasi</h2>
            <p className="text-xs text-[var(--text-secondary)] mt-1">
              Operator konsolu icin karanlik veya aydinlik yuksek kontrast gorunumunu secin.
            </p>
          </div>
        </div>
        <div className="flex rounded-md border border-[var(--border)] bg-[var(--bg-secondary)] p-1">
          <button
            type="button"
            aria-pressed={themeMode === 'dark'}
            onClick={() => setThemeMode('dark')}
            className={`inline-flex h-8 items-center gap-1.5 rounded px-3 text-xs font-medium transition-colors ${
              themeMode === 'dark' ? 'bg-[var(--accent)] text-white' : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
            }`}
          >
            <Moon size={13} />
            Koyu
          </button>
          <button
            type="button"
            aria-pressed={themeMode === 'light'}
            onClick={() => setThemeMode('light')}
            className={`inline-flex h-8 items-center gap-1.5 rounded px-3 text-xs font-medium transition-colors ${
              themeMode === 'light' ? 'bg-[var(--accent)] text-white' : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
            }`}
          >
            <Sun size={13} />
            Acik
          </button>
        </div>
      </div>

      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="mt-0.5 rounded-lg bg-[var(--accent)]/10 p-2 text-[var(--accent)]">
            <Volume2 size={18} />
          </div>
          <div>
            <h2 className="text-sm font-semibold text-[var(--text-primary)]">İnsan Tespiti Sesli Uyarı</h2>
            <p className="text-xs text-[var(--text-secondary)] mt-1">
              Yeni insan tespiti alarmı geldiğinde bu tarayıcıda kısa bir uyarı sesi çalar.
            </p>
          </div>
        </div>
        <Toggle checked={soundEnabled} onChange={setSoundEnabled} />
      </div>

      <div className="mt-4 max-w-xs">
        <Input
          label="Ses Süresi (saniye)"
          type="number"
          min={1}
          max={15}
          value={soundDuration}
          disabled={!soundEnabled}
          title="İnsan tespiti alarmında sesin kaç saniye çalacağını belirler."
          onChange={(e) => setSoundDuration(Number(e.target.value))}
        />
        <p className="text-xs text-[var(--text-secondary)] mt-1">1-15 saniye arası ayarlanabilir.</p>
      </div>
    </section>
  )
}

/** Kullanıcı yönetimi sayfası */
function AuditEventsPanel({ enabled }: { enabled: boolean }) {
  const [auditSearch, setAuditSearch] = useState('')
  const [auditStatus, setAuditStatus] = useState<'all' | 'success' | 'failure'>('all')
  const { data: events = [], isLoading } = useQuery({
    queryKey: ['audit-events'],
    queryFn: () => systemApi.auditEvents(50),
    enabled,
    refetchInterval: 30_000,
  })

  const filteredEvents = useMemo(() => {
    const needle = auditSearch.trim().toLowerCase()
    return events.filter((event) => {
      const matchesStatus =
        auditStatus === 'all' ||
        (auditStatus === 'success' && event.success) ||
        (auditStatus === 'failure' && !event.success)
      const haystack = [
        event.timestamp,
        event.action,
        event.actor ?? '',
        event.source_ip ?? '',
        event.event_hash ?? '',
        event.previous_hash ?? '',
        auditEventMetadataText(event),
      ].join(' ').toLowerCase()
      const matchesSearch = !needle || haystack.includes(needle)
      return matchesStatus && matchesSearch
    })
  }, [auditSearch, auditStatus, events])

  const hasAuditFilter = auditSearch.trim() !== '' || auditStatus !== 'all'

  const exportAuditCsv = () => {
    const escapeCsv = (value: string) => `"${value.replace(/"/g, '""')}"`
    const headers = ['Zaman', 'Durum', 'Aksiyon', 'Kullanici', 'IP', 'Hash Algoritmasi', 'Onceki Hash', 'Olay Hash', 'Detay']
    const rows = filteredEvents.map((event) => [
      dayjs(event.timestamp).format('YYYY-MM-DD HH:mm:ss'),
      event.success ? 'Basarili' : 'Basarisiz',
      event.action,
      event.actor ?? '-',
      event.source_ip ?? '-',
      event.hash_algorithm ?? '-',
      event.previous_hash ?? '-',
      event.event_hash ?? '-',
      auditEventMetadataText(event),
    ])
    const csv = [headers, ...rows].map((row) => row.map(escapeCsv).join(',')).join('\r\n')
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `audit-events-${dayjs().format('YYYYMMDD-HHmmss')}.csv`
    document.body.appendChild(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(url)
  }

  if (!enabled) return null

  return (
    <section className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-4">
      <div className="mb-3 flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="mt-0.5 rounded-lg bg-[var(--accent)]/10 p-2 text-[var(--accent)]">
            <Activity size={18} />
          </div>
          <div>
            <h2 className="text-sm font-semibold text-[var(--text-primary)]">Audit Kayitlari</h2>
            <p className="mt-1 text-xs text-[var(--text-secondary)]">
              Son 50 guvenlik ve operasyon olayi. Liste 30 saniyede bir yenilenir.
            </p>
          </div>
        </div>
        <Badge variant="info">{filteredEvents.length} / {events.length} olay</Badge>
      </div>

      <div className="mb-3 flex flex-wrap items-center gap-2">
        <Input
          value={auditSearch}
          onChange={(e) => setAuditSearch(e.target.value)}
          placeholder="Aksiyon, kullanici, IP veya detay ara"
          className="w-full sm:w-80"
        />
        <select
          value={auditStatus}
          onChange={(e) => setAuditStatus(e.target.value as 'all' | 'success' | 'failure')}
          className="rounded-lg border border-[var(--border)] bg-[var(--bg-card)] px-3 py-2 text-sm text-[var(--text-primary)] outline-none transition-colors focus:border-[var(--accent)]"
        >
          <option value="all">Tum Durumlar</option>
          <option value="success">Basarili</option>
          <option value="failure">Basarisiz</option>
        </select>
        <Button
          size="sm"
          variant="secondary"
          icon={<Download size={14} />}
          disabled={filteredEvents.length === 0}
          onClick={exportAuditCsv}
        >
          CSV Indir
        </Button>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-8"><Spinner size="sm" /></div>
      ) : filteredEvents.length === 0 ? (
        <p className="rounded-md border border-dashed border-[var(--border)] px-3 py-6 text-center text-sm text-[var(--text-secondary)]">
          {hasAuditFilter ? 'Filtrelerle eslesen audit kaydi yok.' : 'Audit kaydi bulunamadi.'}
        </p>
      ) : (
        <div className="max-h-80 overflow-y-auto rounded-md border border-[var(--border)]">
          <table className="w-full text-xs">
            <thead className="sticky top-0 bg-[var(--bg-secondary)]">
              <tr className="border-b border-[var(--border)] text-left text-[var(--text-secondary)]">
                <th className="px-3 py-2 font-medium">Zaman</th>
                <th className="px-3 py-2 font-medium">Aksiyon</th>
                <th className="px-3 py-2 font-medium">Kullanici</th>
                <th className="px-3 py-2 font-medium">IP</th>
                <th className="px-3 py-2 font-medium">Zincir</th>
                <th className="px-3 py-2 font-medium">Detay</th>
              </tr>
            </thead>
            <tbody>
              {filteredEvents.map((event, index) => (
                <tr key={`${event.timestamp}-${event.action}-${index}`} className="border-b border-[var(--border)] last:border-b-0">
                  <td className="whitespace-nowrap px-3 py-2 text-[var(--text-secondary)]">
                    {dayjs(event.timestamp).format('DD.MM.YYYY HH:mm:ss')}
                  </td>
                  <td className="px-3 py-2">
                    <Badge variant={event.success ? 'success' : 'danger'}>{event.action}</Badge>
                  </td>
                  <td className="px-3 py-2 text-[var(--text-primary)]">{event.actor ?? '-'}</td>
                  <td className="px-3 py-2 font-mono text-[var(--text-secondary)]">{event.source_ip ?? '-'}</td>
                  <td className="px-3 py-2 font-mono text-[var(--text-secondary)]" title={event.event_hash ?? 'Hash yok'}>
                    {auditEventHashLabel(event)}
                  </td>
                  <td className="max-w-xs truncate px-3 py-2 font-mono text-[var(--text-secondary)]" title={auditEventMetadataText(event)}>
                    {auditEventMetadataText(event)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}

export function SettingsPage() {
  const [showAdd, setShowAdd] = useState(false)
  const [editUser, setEditUser] = useState<User | null>(null)
  const [userSearch, setUserSearch] = useState('')
  const [roleFilter, setRoleFilter] = useState<'all' | 'admin' | 'operator' | 'viewer'>('all')
  const [activeFilter, setActiveFilter] = useState<'all' | 'active' | 'inactive'>('all')
  const [userSort, setUserSort] = useState<'username_asc' | 'username_desc' | 'role' | 'status' | 'id_desc'>('username_asc')
  const [userPage, setUserPage] = useState(1)
  const [userPageSize, setUserPageSize] = useState(25)
  const [deleteTarget, setDeleteTarget] = useState<User | null>(null)
  const qc = useQueryClient()
  const { canManageUsers } = usePermissions()
  const currentUsername = useAuthStore((s) => s.username)
  const showToast = useToastStore((state) => state.showToast)

  const { data: userPageData, isLoading } = useQuery({
    queryKey: ['users', 'paginated', userPage, userPageSize, userSearch, roleFilter, activeFilter, userSort],
    queryFn: () => usersApi.listPaginated({
      page: userPage,
      page_size: userPageSize,
      search: userSearch,
      role: roleFilter,
      active: activeFilter,
      sort: userSort,
    }),
  })

  const users = userPageData?.items ?? EMPTY_USERS
  const userTotal = userPageData?.total ?? 0

  const filteredUsers = useMemo(() => {
    const needle = userSearch.trim().toLowerCase()
    const filtered = users.filter((user) => {
      const matchesSearch = !needle || user.username.toLowerCase().includes(needle)
      const matchesRole = roleFilter === 'all' || user.role === roleFilter
      const matchesActive =
        activeFilter === 'all' ||
        (activeFilter === 'active' && user.is_active) ||
        (activeFilter === 'inactive' && !user.is_active)
      return matchesSearch && matchesRole && matchesActive
    })
    return [...filtered].sort((left, right) => {
      if (userSort === 'username_desc') return right.username.localeCompare(left.username, 'tr')
      if (userSort === 'role') return left.role.localeCompare(right.role, 'tr') || left.username.localeCompare(right.username, 'tr')
      if (userSort === 'status') return Number(right.is_active) - Number(left.is_active) || left.username.localeCompare(right.username, 'tr')
      if (userSort === 'id_desc') return right.id - left.id
      return left.username.localeCompare(right.username, 'tr')
    })
  }, [activeFilter, roleFilter, userSearch, userSort, users])

  const hasUserFilter = userSearch.trim() !== '' || roleFilter !== 'all' || activeFilter !== 'all' || userSort !== 'username_asc'

  const resetUserFilters = () => {
    setUserSearch('')
    setRoleFilter('all')
    setActiveFilter('all')
    setUserSort('username_asc')
    setUserPage(1)
  }

  /** Kullanıcıyı sistemden siler */
  const deleteUser = useMutation({
    mutationFn: usersApi.delete,
    onSuccess: () => {
      showToast({ variant: 'success', title: 'Kullanici silindi', description: deleteTarget?.username })
      setDeleteTarget(null)
      qc.invalidateQueries({ queryKey: ['users'] })
    },
    onError: (err) => showToast({ variant: 'danger', title: 'Kullanici silinemedi', description: getApiErrorMessage(err, 'Silme islemi tamamlanamadi.') }),
  })

  const columns = [
    { key: 'username', header: 'Kullanıcı Adı', render: (u: User) => (
      <div className="flex items-center gap-2">
        <span className="font-medium">{u.username}</span>
        {u.username === currentUsername && (
          <Badge variant="info">Siz</Badge>
        )}
      </div>
    )},
    {
      key: 'role',
      header: 'Rol',
      render: (u: User) => <Badge variant={roleVariant(u.role)}>{roleLabel[u.role] ?? u.role}</Badge>,
    },
    {
      key: 'active',
      header: 'Durum',
      render: (u: User) => <Badge variant={u.is_active ? 'success' : 'neutral'} dot>{u.is_active ? 'Aktif' : 'Pasif'}</Badge>,
    },
    {
      key: 'actions',
      header: '',
      width: '140px',
      render: (u: User) => canManageUsers ? (
        <div className="flex items-center gap-1.5">
          <Button size="sm" variant="secondary" icon={<Pencil size={12} />} onClick={() => setEditUser(u)}>
            Düzenle
          </Button>
          {/* Kendi hesabını silememeli */}
          {u.username !== currentUsername && (
            <Button
              size="sm"
              variant="danger"
              icon={<Trash2 size={12} />}
              loading={deleteUser.isPending && deleteUser.variables === u.id}
              onClick={() => setDeleteTarget(u)}
            >
              Sil
            </Button>
          )}
        </div>
      ) : null,
    },
  ]

  return (
    <div className="p-6 flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-[var(--text-primary)]">Sistem ve Kullanicilar</h1>
          {!canManageUsers && (
            <p className="text-sm text-[var(--text-secondary)] mt-0.5">
              Kullanıcı yönetimi için admin yetkisi gerekli.
            </p>
          )}
        </div>
        {canManageUsers && (
          <Button icon={<Plus size={15} />} onClick={() => setShowAdd(true)}>
            Kullanıcı Ekle
          </Button>
        )}
      </div>

      <GeneralSettingsPanel />

      <AuditEventsPanel enabled={canManageUsers} />

      <div>
        <div className="mb-3 flex flex-col gap-3">
          <div>
            <h2 className="text-sm font-semibold text-[var(--text-secondary)] uppercase tracking-wide">Kullanıcılar</h2>
            <p className="mt-1 text-sm text-[var(--text-secondary)]">
              {userTotal} kullanici sonucu
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Input
              value={userSearch}
              onChange={(e) => { setUserSearch(e.target.value); setUserPage(1) }}
              placeholder="Kullanici adi ara"
              className="w-full sm:w-72"
            />
            <select
              value={roleFilter}
              onChange={(e) => { setRoleFilter(e.target.value as 'all' | 'admin' | 'operator' | 'viewer'); setUserPage(1) }}
              className="rounded-lg border border-[var(--border)] bg-[var(--bg-card)] px-3 py-2 text-sm text-[var(--text-primary)] outline-none transition-colors focus:border-[var(--accent)]"
            >
              <option value="all">Tum Roller</option>
              <option value="admin">Admin</option>
              <option value="operator">Operator</option>
              <option value="viewer">Izleyici</option>
            </select>
            <select
              value={activeFilter}
              onChange={(e) => { setActiveFilter(e.target.value as 'all' | 'active' | 'inactive'); setUserPage(1) }}
              className="rounded-lg border border-[var(--border)] bg-[var(--bg-card)] px-3 py-2 text-sm text-[var(--text-primary)] outline-none transition-colors focus:border-[var(--accent)]"
            >
              <option value="all">Tum Durumlar</option>
              <option value="active">Aktif</option>
              <option value="inactive">Pasif</option>
            </select>
            <select
              value={userSort}
              onChange={(e) => { setUserSort(e.target.value as 'username_asc' | 'username_desc' | 'role' | 'status' | 'id_desc'); setUserPage(1) }}
              aria-label="Kullanici listesini sirala"
              className="rounded-lg border border-[var(--border)] bg-[var(--bg-card)] px-3 py-2 text-sm text-[var(--text-primary)] outline-none transition-colors focus:border-[var(--accent)]"
            >
              <option value="username_asc">Ad A-Z</option>
              <option value="username_desc">Ad Z-A</option>
              <option value="role">Rol</option>
              <option value="status">Aktiflik</option>
              <option value="id_desc">En Yeni</option>
            </select>
            {hasUserFilter && (
              <Button size="sm" variant="secondary" onClick={resetUserFilters}>
                Filtreleri Sifirla
              </Button>
            )}
          </div>
        </div>
        {isLoading ? (
          <div className="flex justify-center py-16"><Spinner size="lg" /></div>
        ) : (
          <>
            <Table columns={columns} data={filteredUsers} keyFn={(u) => u.id} emptyText={hasUserFilter ? 'Filtrelerle eslesen kullanici bulunamadi.' : 'Kullanıcı bulunamadı.'} caption="Kullanici listesi" />
            <PaginationControls
              page={userPage}
              pageSize={userPageSize}
              total={userTotal}
              onPageChange={setUserPage}
              onPageSizeChange={(pageSize) => { setUserPageSize(pageSize); setUserPage(1) }}
            />
          </>
        )}
      </div>

      {/* Yetki açıklama kartı */}
      <div className="bg-[var(--bg-card)] border border-[var(--border)] rounded-xl p-4">
        <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-3">Rol Yetkileri</h3>
        <div className="grid grid-cols-3 gap-4 text-xs text-[var(--text-secondary)]">
          <div>
            <Badge variant="danger" className="mb-2">Admin</Badge>
            <ul className="space-y-1 mt-2">
              <li>✓ Tüm kamera işlemleri</li>
              <li>✓ Tüm NVR işlemleri</li>
              <li>✓ Kullanıcı yönetimi</li>
              <li>✓ Alarm onaylama</li>
            </ul>
          </div>
          <div>
            <Badge variant="warning" className="mb-2">Operatör</Badge>
            <ul className="space-y-1 mt-2">
              <li>✓ Kamera yönetimi</li>
              <li>✓ NVR yönetimi</li>
              <li>✗ Kullanıcı yönetimi</li>
              <li>✓ Alarm onaylama</li>
            </ul>
          </div>
          <div>
            <Badge variant="neutral" className="mb-2">İzleyici</Badge>
            <ul className="space-y-1 mt-2">
              <li>✗ Kamera yönetimi</li>
              <li>✗ NVR yönetimi</li>
              <li>✗ Kullanıcı yönetimi</li>
              <li>✓ Alarm onaylama</li>
            </ul>
          </div>
        </div>
      </div>

      <AddUserModal open={showAdd} onClose={() => setShowAdd(false)} />
      <EditUserModal user={editUser} onClose={() => setEditUser(null)} />
      <ConfirmDialog
        open={deleteTarget !== null}
        title="Kullanici Sil"
        description={deleteTarget ? `"${deleteTarget.username}" kullanicisi silinecek. Bu kullanici artik sisteme erisemeyecek.` : ''}
        confirmLabel="Sil"
        loading={deleteUser.isPending}
        onClose={() => !deleteUser.isPending && setDeleteTarget(null)}
        onConfirm={() => deleteTarget && deleteUser.mutate(deleteTarget.id)}
      />
    </div>
  )
}
