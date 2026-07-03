// Kenar çubuğu (Sidebar) navigasyon bileşeni — sol panel, sayfa bağlantıları, kullanıcı bilgisi
import { NavLink } from 'react-router-dom'
import { LayoutDashboard, Camera, Server, Bell, Users, LogOut } from 'lucide-react'
import { useAuthStore } from '../../stores/authStore'

const navItems = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, exact: true },
  { to: '/cameras', label: 'Kameralar', icon: Camera, exact: false },
  { to: '/nvr', label: 'NVR', icon: Server, exact: false },
  { to: '/alarms', label: 'Alarmlar', icon: Bell, exact: false },
  { to: '/settings', label: 'Kullanıcılar', icon: Users, exact: false },
]

export function Sidebar() {
  const { username, logout } = useAuthStore()

  return (
    <aside className="flex flex-col w-60 h-screen bg-bg-secondary border-r border-border shrink-0">
      {/* Logo */}
      <div className="flex items-center gap-3 px-5 h-16 border-b border-border">
        <div className="w-7 h-7 rounded-lg bg-accent flex items-center justify-center">
          <Camera size={15} className="text-white" />
        </div>
        <span className="font-semibold text-text-primary text-sm">Kamera Yönetimi</span>
      </div>

      {/* Navigasyon */}
      <nav className="flex-1 px-3 py-4 space-y-0.5">
        {navItems.map(({ to, label, icon: Icon, exact }) => (
          <NavLink
            key={to}
            to={to}
            end={exact}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors duration-150 ${
                isActive
                  ? 'bg-accent/15 text-accent font-semibold'
                  : 'text-text-secondary hover:text-text-primary hover:bg-bg-card'
              }`
            }
          >
            <Icon size={17} />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Alt: kullanıcı + çıkış */}
      <div className="px-3 py-4 border-t border-border">
        <div className="flex items-center justify-between px-3 py-2 rounded-lg">
          <div className="flex flex-col">
            <span className="text-sm font-medium text-text-primary">{username}</span>
          </div>
          <button
            onClick={logout}
            title="Çıkış yap"
            className="p-1.5 rounded-lg hover:bg-bg-card text-text-secondary hover:text-danger transition-colors"
          >
            <LogOut size={16} />
          </button>
        </div>
      </div>
    </aside>
  )
}
