// Left navigation shell for the operator console.
import { NavLink } from 'react-router-dom'
import { Bell, Camera, LayoutDashboard, LogOut, PanelLeftClose, PanelLeftOpen, Server, Users } from 'lucide-react'
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
  collapsed?: boolean
  onToggleCollapsed?: () => void
}

export function Sidebar({ className = '', onNavigate, collapsed = false, onToggleCollapsed }: SidebarProps) {
  const { username, logout } = useAuthStore()

  return (
    <aside className={`flex h-screen shrink-0 flex-col border-r border-border bg-bg-secondary transition-[width] duration-150 ${collapsed ? 'w-16' : 'w-56'} ${className}`}>
      <div className={`flex h-14 items-center border-b border-border ${collapsed ? 'justify-center px-2' : 'gap-3 px-4'}`}>
        <div className="flex h-7 w-7 items-center justify-center rounded bg-accent">
          <Camera size={15} className="text-white" />
        </div>
        {!collapsed && <span className="text-sm font-semibold tracking-wide text-text-primary">Kamera Yonetimi</span>}
      </div>

      <nav className="flex-1 space-y-0.5 px-2 py-3">
        {navItems.map(({ to, label, icon: Icon, exact }) => (
          <NavLink
            key={to}
            to={to}
            end={exact}
            onClick={onNavigate}
            title={collapsed ? label : undefined}
            className={({ isActive }) =>
              `flex items-center rounded-md border py-2 text-sm font-medium transition-colors duration-150 ${collapsed ? 'justify-center px-2' : 'gap-3 px-3'} ${
                isActive
                  ? 'border-accent/20 bg-accent/15 text-accent'
                  : 'border-transparent text-text-secondary hover:bg-bg-card hover:text-text-primary'
              }`
            }
          >
            <Icon size={17} />
            {!collapsed && label}
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-border px-3 py-3">
        {onToggleCollapsed && (
          <button
            type="button"
            title={collapsed ? 'Menuyu genislet' : 'Menuyu daralt'}
            aria-label={collapsed ? 'Menuyu genislet' : 'Menuyu daralt'}
            onClick={onToggleCollapsed}
            className="mb-2 flex w-full items-center justify-center rounded-md p-1.5 text-text-secondary transition-colors hover:bg-bg-card hover:text-text-primary"
          >
            {collapsed ? <PanelLeftOpen size={16} /> : <PanelLeftClose size={16} />}
          </button>
        )}
        <div className={`flex items-center rounded-md py-2 ${collapsed ? 'justify-center px-0' : 'justify-between px-2'}`}>
          {!collapsed && <span className="truncate text-sm font-medium text-text-primary">{username}</span>}
          <button
            onClick={logout}
            title="Cikis yap"
            aria-label="Cikis yap"
            className="rounded-md p-1.5 text-text-secondary transition-colors hover:bg-bg-card hover:text-danger"
          >
            <LogOut size={16} />
          </button>
        </div>
      </div>
    </aside>
  )
}
