// Kullanıcı yönetimi sayfası — listeleme, ekleme, düzenleme (rol/aktiflik/şifre), silme
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Pencil, Trash2, Volume2 } from 'lucide-react'
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
import type { User, UserCreate } from '../types/api'

/** Yeni kullanıcı ekleme modal'ı */
function AddUserModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const qc = useQueryClient()
  const [form, setForm] = useState<UserCreate>({ username: '', password: '', role: 'viewer' })

  const { mutate, isPending, error } = useMutation({
    mutationFn: usersApi.add,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['users'] })
      onClose()
      setForm({ username: '', password: '', role: 'viewer' })
    },
  })

  return (
    <Modal open={open} onClose={onClose} title="Kullanıcı Ekle">
      <form onSubmit={(e) => { e.preventDefault(); mutate(form) }} className="flex flex-col gap-4">
        <Input label="Kullanıcı Adı" value={form.username} onChange={(e) => setForm((f) => ({ ...f, username: e.target.value }))} required />
        <Input label="Şifre" type="password" value={form.password} onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))} required />
        <RoleSelect value={form.role} onChange={(role) => setForm((f) => ({ ...f, role }))} />
        {error && <p className="text-xs text-[var(--danger)]">Hata oluştu, tekrar deneyin.</p>}
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
  const [form, setForm] = useState<UserUpdate>({})
  const [lastId, setLastId] = useState<number | null>(null)
  const currentUsername = useAuthStore((s) => s.username)

  if (user && user.id !== lastId) {
    setLastId(user.id)
    setForm({ role: user.role, is_active: user.is_active })
  }

  const { mutate, isPending, error } = useMutation({
    mutationFn: (payload: UserUpdate) => usersApi.update(user!.id, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['users'] })
      onClose()
    },
  })

  if (!user) return null

  // Kendi hesabını devre dışı bırakmasını engelle
  const isSelf = user.username === currentUsername

  return (
    <Modal open onClose={onClose} title={`Düzenle — ${user.username}`}>
      <form onSubmit={(e) => { e.preventDefault(); mutate(form) }} className="flex flex-col gap-4">
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

        <Input
          label="Yeni Şifre"
          type="password"
          placeholder="Değiştirmek için doldurun"
          onChange={(e) => setForm((f) => ({ ...f, password: e.target.value || undefined }))}
        />

        {isSelf && (
          <p className="text-xs text-[var(--warning)]">Kendi hesabınızı devre dışı bırakamazsınız.</p>
        )}
        {error && <p className="text-xs text-[var(--danger)]">Hata oluştu, tekrar deneyin.</p>}
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
        <option value="viewer">İzleyici — Yalnızca görüntüleme ve alarm onaylama</option>
      </select>
    </div>
  )
}

const roleVariant = (role: string) => {
  if (role === 'admin') return 'danger'
  if (role === 'operator') return 'warning'
  return 'neutral'
}

const roleLabel = { admin: 'Admin', operator: 'Operatör', viewer: 'İzleyici' } as Record<string, string>

/** İnsan tespiti sesli uyarı ayarlarını düzenler. */
function GeneralSettingsPanel() {
  const soundEnabled = useSystemSettingsStore((s) => s.humanDetectionSoundEnabled)
  const soundDuration = useSystemSettingsStore((s) => s.humanDetectionSoundDurationSeconds)
  const setSoundEnabled = useSystemSettingsStore((s) => s.setHumanDetectionSoundEnabled)
  const setSoundDuration = useSystemSettingsStore((s) => s.setHumanDetectionSoundDurationSeconds)

  return (
    <section className="bg-[var(--bg-card)] border border-[var(--border)] rounded-xl p-4">
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
export function SettingsPage() {
  const [showAdd, setShowAdd] = useState(false)
  const [editUser, setEditUser] = useState<User | null>(null)
  const qc = useQueryClient()
  const { canManageUsers } = usePermissions()
  const currentUsername = useAuthStore((s) => s.username)

  const { data: users = [], isLoading } = useQuery({
    queryKey: ['users'],
    queryFn: usersApi.list,
  })

  /** Kullanıcıyı sistemden siler */
  const deleteUser = useMutation({
    mutationFn: usersApi.delete,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['users'] }),
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
              onClick={() => confirm(`"${u.username}" silinsin mi?`) && deleteUser.mutate(u.id)}
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
          <h1 className="text-xl font-bold text-[var(--text-primary)]">Genel Ayarlar</h1>
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

      <div>
        <h2 className="text-sm font-semibold text-[var(--text-secondary)] uppercase tracking-wide mb-3">Kullanıcılar</h2>
        {isLoading ? (
          <div className="flex justify-center py-16"><Spinner size="lg" /></div>
        ) : (
          <Table columns={columns} data={users} keyFn={(u) => u.id} emptyText="Kullanıcı bulunamadı." />
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
    </div>
  )
}
