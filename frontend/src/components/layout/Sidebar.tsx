// Left navigation shell for the operator console.
import { NavLink } from 'react-router-dom'
import { Bell, Camera, LayoutDashboard, LogOut, Server, Users } from 'lucide-react'
import { useAuthStore } from '../../stores/authStore'

const navItems = [
  { to: '/', label: 'Canli Izleme', icon: LayoutDashboard, exact: true },
  { to: '/cameras', label: 'Kameralar', icon: Camera, exact: false },
  { to: '/recorders', label: 'Kayit Cihazlari', icon: Server, exact: false },
  { to: '/alarms', label: 'Alarmlar', icon: Bell, exact: false },
  { to: '/users', label: 'Sistem ve Kullanicilar', icon: Users, exact: false },
]

interface SidebarProps {
  className?: string
  onNavigate?: () => void
}

export function Sidebar({ className = '', onNavigate }: SidebarProps) {
  const { username, logout } = useAuthStore()

  return (
    <aside className={`flex h-screen w-56 shrink-0 flex-col border-r border-border bg-bg-secondary ${className}`}>
      <div className="flex h-14 items-center gap-3 border-b border-border px-4">
        <div className="flex h-7 w-7 items-center justify-center rounded bg-accent">
          <Camera size={15} className="text-white" />
        </div>
        <span className="text-sm font-semibold tracking-wide text-text-primary">Kamera Yönetimi</span>
      </div>

      <nav className="flex-1 space-y-0.5 px-2 py-3">
        {navItems.map(({ to, label, icon: Icon, exact }) => (
          <NavLink
            key={to}
            to={to}
            end={exact}
            onClick={onNavigate}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-md border px-3 py-2 text-sm font-medium transition-colors duration-150 ${
                isActive
                  ? 'border-accent/20 bg-accent/15 text-accent'
                  : 'border-transparent text-text-secondary hover:bg-bg-card hover:text-text-primary'
              }`
            }
          >
            <Icon size={17} />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-border px-3 py-3">
        <div className="flex items-center justify-between rounded-md px-2 py-2">
          <span className="truncate text-sm font-medium text-text-primary">{username}</span>
          <button
            onClick={logout}
            title="Çıkış yap"
            aria-label="Çıkış yap"
            className="rounded-md p-1.5 text-text-secondary transition-colors hover:bg-bg-card hover:text-danger"
          >
            <LogOut size={16} />
          </button>
        </div>
      </div>
    </aside>
  )
}
