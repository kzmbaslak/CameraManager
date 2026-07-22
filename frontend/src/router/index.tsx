// Uygulama route tanımları ve korumalı sayfa yönlendirmeleri.
import { type ReactNode, Suspense, lazy } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'
import { LoginPage } from '../pages/LoginPage'

const AppLayout = lazy(() => import('../components/layout/AppLayout').then((m) => ({ default: m.AppLayout })))
const DashboardPage = lazy(() => import('../pages/DashboardPage').then((m) => ({ default: m.DashboardPage })))
const CamerasPage = lazy(() => import('../pages/CamerasPage').then((m) => ({ default: m.CamerasPage })))
const NVRPage = lazy(() => import('../pages/NVRPage').then((m) => ({ default: m.NVRPage })))
const AlarmsPage = lazy(() => import('../pages/AlarmsPage').then((m) => ({ default: m.AlarmsPage })))
const SettingsPage = lazy(() => import('../pages/SettingsPage').then((m) => ({ default: m.SettingsPage })))

function RouteLoader() {
  return (
    <div className="min-h-[50vh] flex items-center justify-center text-sm text-[var(--text-secondary)]">
      Yükleniyor...
    </div>
  )
}

function ProtectedRoute({ children }: { children: ReactNode }) {
  const token = useAuthStore((s) => s.token)
  if (!token) return <Navigate to="/login" replace />
  return <>{children}</>
}

export function AppRouter() {
  return (
    <BrowserRouter>
      <Suspense fallback={<RouteLoader />}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <AppLayout />
              </ProtectedRoute>
            }
          >
            <Route index element={<DashboardPage />} />
            <Route path="cameras" element={<CamerasPage />} />
            <Route path="recorders" element={<NVRPage />} />
            <Route path="nvr" element={<Navigate to="/recorders" replace />} />
            <Route path="alarms" element={<AlarmsPage />} />
            <Route path="users" element={<SettingsPage />} />
            <Route path="settings" element={<Navigate to="/users" replace />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  )
}
