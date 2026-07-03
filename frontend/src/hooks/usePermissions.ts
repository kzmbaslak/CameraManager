// Rol tabanlı yetki kontrolü — useAuthStore'dan rolü okuyarak izin flagleri döner
import { useAuthStore } from '../stores/authStore'

interface Permissions {
  /** Kamera ekleme ve silme */
  canManageCameras: boolean
  /** Kamera AI/durum toggle ve düzenleme */
  canEditCameras: boolean
  /** NVR ekleme, düzenleme ve silme */
  canManageNVRs: boolean
  /** Kullanıcı ekleme, düzenleme ve silme */
  canManageUsers: boolean
  /** Alarm onaylama */
  canAcknowledgeAlarms: boolean
  /** Mevcut rol */
  role: string | null
  isAdmin: boolean
  isOperator: boolean
  isViewer: boolean
}

/**
 * Giriş yapan kullanıcının rolüne göre izin flaglerini hesaplar.
 *
 * - admin: tam yetki
 * - operator: kamera/NVR yönetimi + alarm onaylama; kullanıcı yönetimi yok
 * - viewer: yalnızca okuma + alarm onaylama
 */
export function usePermissions(): Permissions {
  const role = useAuthStore((s) => s.role)

  const isAdmin = role === 'admin'
  const isOperator = role === 'operator'
  const isViewer = role === 'viewer'

  return {
    canManageCameras: isAdmin || isOperator,
    canEditCameras: isAdmin || isOperator,
    canManageNVRs: isAdmin || isOperator,
    canManageUsers: isAdmin,
    canAcknowledgeAlarms: isAdmin || isOperator || isViewer,
    role,
    isAdmin,
    isOperator,
    isViewer,
  }
}
