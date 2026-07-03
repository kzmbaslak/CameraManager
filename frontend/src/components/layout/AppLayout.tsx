import { Outlet } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { AlarmNotificationPanel } from '../alarm/AlarmNotificationPanel'
import { CameraFullscreenModal } from '../camera/CameraFullscreenModal'

export function AppLayout() {
  return (
    <div className="flex h-screen bg-[var(--bg-primary)] overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-y-auto">
        <Outlet />
      </main>
      {/* Global: hangi sayfada olursa olsun alarm bildirimleri */}
      <AlarmNotificationPanel />
      {/* Global: tam ekran kamera modal */}
      <CameraFullscreenModal />
    </div>
  )
}
