// Uygulama ana yerleşimi; sidebar ve içerik alanını düzenler.
import { useEffect, useMemo, useState } from 'react'
import { Outlet } from 'react-router-dom'
import { Camera, Clock3, LogOut, Menu } from 'lucide-react'
import { Sidebar } from './Sidebar'
import { AlarmNotificationPanel } from '../alarm/AlarmNotificationPanel'
import { CameraFullscreenModal } from '../camera/CameraFullscreenModal'
import { ToastViewport } from '../ui/ToastViewport'
import { Button } from '../ui/Button'
import { useAuthStore } from '../../stores/authStore'

const SESSION_WARNING_MS = 5 * 60 * 1000
const INITIAL_NOW = Date.now()
const SIDEBAR_COLLAPSED_KEY = 'kamera-sidebar-collapsed'

function readSidebarCollapsedPreference() {
  try {
    return localStorage.getItem(SIDEBAR_COLLAPSED_KEY) === 'true'
  } catch {
    return false
  }
}

export function AppLayout() {
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(readSidebarCollapsedPreference)
  const [now, setNow] = useState(INITIAL_NOW)
  const expiresAt = useAuthStore((s) => s.expiresAt)
  const logout = useAuthStore((s) => s.logout)

  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 30_000)
    return () => window.clearInterval(timer)
  }, [])

  useEffect(() => {
    if (expiresAt && now >= expiresAt) {
      logout()
      window.location.href = '/login?expired=1'
    }
  }, [expiresAt, logout, now])

  const remainingMinutes = useMemo(() => {
    if (!expiresAt) return null
    return Math.max(0, Math.ceil((expiresAt - now) / 60_000))
  }, [expiresAt, now])

  const showSessionWarning =
    remainingMinutes !== null && expiresAt !== null && expiresAt - now <= SESSION_WARNING_MS && expiresAt > now

  const handleLogout = () => {
    logout()
    window.location.href = '/login'
  }

  const toggleSidebarCollapsed = () => {
    setSidebarCollapsed((current) => {
      const next = !current
      try {
        localStorage.setItem(SIDEBAR_COLLAPSED_KEY, String(next))
      } catch {
        // Keep the in-memory preference when storage is unavailable.
      }
      return next
    })
  }

  return (
    <div className="flex h-screen bg-[var(--bg-primary)] overflow-hidden">
      <Sidebar
        className="hidden md:flex"
        collapsed={sidebarCollapsed}
        onToggleCollapsed={toggleSidebarCollapsed}
      />

      <header className="fixed left-0 right-0 top-0 z-[120] flex h-12 items-center justify-between border-b border-border bg-bg-secondary px-3 md:hidden">
        <button
          type="button"
          aria-label="Navigasyonu ac"
          onClick={() => setMobileSidebarOpen(true)}
          className="rounded-md border border-border bg-bg-card p-2 text-text-secondary transition-colors hover:text-text-primary"
        >
          <Menu size={18} />
        </button>
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded bg-accent">
            <Camera size={15} className="text-white" />
          </div>
          <span className="text-sm font-semibold text-text-primary">Kamera Yonetimi</span>
        </div>
        <div className="h-9 w-9" />
      </header>

      {mobileSidebarOpen && (
        <div className="fixed inset-0 z-[170] md:hidden">
          <button
            type="button"
            aria-label="Navigasyonu kapat"
            className="absolute inset-0 bg-black/55"
            onClick={() => setMobileSidebarOpen(false)}
          />
          <Sidebar className="relative z-[180] shadow-2xl" onNavigate={() => setMobileSidebarOpen(false)} />
        </div>
      )}

      <main className="flex-1 overflow-y-auto pt-12 md:pt-0">
        {showSessionWarning && (
          <div
            role="status"
            className="sticky top-0 z-[90] flex flex-col gap-2 border-b border-[var(--warning)]/25 bg-[var(--warning)]/10 px-4 py-2 text-[var(--warning)] shadow-sm sm:flex-row sm:items-center sm:justify-between"
          >
            <div className="flex items-center gap-2 text-sm font-medium">
              <Clock3 size={16} />
              <span>Oturum {remainingMinutes} dakika icinde sona erecek.</span>
            </div>
            <Button variant="secondary" size="sm" icon={<LogOut size={14} />} onClick={handleLogout}>
              Cikis yap
            </Button>
          </div>
        )}
        <Outlet />
      </main>
      {/* Global: hangi sayfada olursa olsun alarm bildirimleri */}
      <AlarmNotificationPanel />
      {/* Global: tam ekran kamera modal */}
      <CameraFullscreenModal />
      <ToastViewport />
    </div>
  )
}
