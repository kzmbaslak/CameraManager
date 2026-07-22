// Uygulama ana yerleşimi; sidebar ve içerik alanını düzenler.
import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import { Camera, Menu } from 'lucide-react'
import { Sidebar } from './Sidebar'
import { AlarmNotificationPanel } from '../alarm/AlarmNotificationPanel'
import { CameraFullscreenModal } from '../camera/CameraFullscreenModal'
import { ToastViewport } from '../ui/ToastViewport'

export function AppLayout() {
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false)

  return (
    <div className="flex h-screen bg-[var(--bg-primary)] overflow-hidden">
      <Sidebar className="hidden md:flex" />

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
