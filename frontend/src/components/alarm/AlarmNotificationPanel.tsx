import { AnimatePresence, motion } from 'framer-motion'
import { X, AlertTriangle, ChevronRight, BellOff } from 'lucide-react'
import dayjs from 'dayjs'
import 'dayjs/locale/tr'
import { useAlarmStore } from '../../stores/alarmStore'
import { useCameraStream } from '../../hooks/useCameraStream'
import { useAlarmNotifications } from '../../hooks/useAlarmNotifications'

dayjs.locale('tr')

const typeLabel: Record<string, string> = {
  human_detected: 'İnsan Tespit',
  motion_detected: 'Hareket',
  camera_offline: 'Kamera Çevrimdışı',
}

// Tek bir bildirim kartı — küçük canlı kamera önizlemesi içerir
function NotificationCard({
  alarmId,
  cameraId,
  alarmType,
  receivedAt,
}: {
  alarmId: number
  cameraId: number
  alarmType: string
  receivedAt: number
}) {
  const { dismiss, setExpandedCamera } = useAlarmStore()
  // Kamera çevrimdışı alarmında stream açmaya çalışmak anlamsız — kamera zaten erişilemiyor
  const streamEnabled = alarmType !== 'camera_offline'
  const { frame, connected } = useCameraStream(cameraId, streamEnabled, 'alarm')

  return (
    <motion.div
      layout
      initial={{ opacity: 0, x: 80, scale: 0.95 }}
      animate={{ opacity: 1, x: 0, scale: 1 }}
      exit={{ opacity: 0, x: 80, scale: 0.95 }}
      transition={{ duration: 0.25, ease: 'easeOut' }}
      className="bg-[var(--bg-card)] border border-[var(--danger)]/40 rounded-xl overflow-hidden shadow-xl w-72"
    >
      {/* Üst şerit */}
      <div className="flex items-center justify-between px-3 py-2 bg-[var(--danger)]/10 border-b border-[var(--danger)]/20">
        <div className="flex items-center gap-2">
          <motion.div
            animate={{ opacity: [1, 0.3, 1] }}
            transition={{ repeat: Infinity, duration: 1 }}
          >
            <AlertTriangle size={13} className="text-[var(--danger)]" />
          </motion.div>
          <span className="text-xs font-semibold text-[var(--danger)]">
            {typeLabel[alarmType] ?? alarmType}
          </span>
        </div>
        <div className="flex items-center gap-1">
          <span className="text-xs text-[var(--text-secondary)]">
            {dayjs(receivedAt).format('HH:mm:ss')}
          </span>
          <button
            onClick={() => dismiss(alarmId)}
            className="p-0.5 rounded hover:bg-[var(--border)] text-[var(--text-secondary)] transition-colors"
          >
            <X size={12} />
          </button>
        </div>
      </div>

      {/* Küçük kamera önizleme — tıklayınca tam ekran */}
      <button
        onClick={() => setExpandedCamera(cameraId)}
        className="relative w-full aspect-video bg-[var(--bg-primary)] flex items-center justify-center group overflow-hidden"
      >
        {frame ? (
          <img src={frame} alt="alarm" className="w-full h-full object-cover" />
        ) : (
          <div className="text-xs text-[var(--text-secondary)]">
            {connected ? 'Bağlanıyor...' : 'Bağlantı yok'}
          </div>
        )}
        {/* hover overlay */}
        <div className="absolute inset-0 bg-black/0 group-hover:bg-black/30 transition-colors flex items-center justify-center">
          <div className="opacity-0 group-hover:opacity-100 flex items-center gap-1.5 bg-white/20 backdrop-blur-sm px-3 py-1.5 rounded-full text-white text-xs font-medium transition-opacity">
            <ChevronRight size={13} />
            Tam Ekran
          </div>
        </div>
      </button>
    </motion.div>
  )
}

// Tüm bildirimleri yöneten kapsayıcı — her sayfanın üzerinde durur
export function AlarmNotificationPanel() {
  // Hook burada çağrılır — AppLayout içinde mount edildiğinde polling başlar
  useAlarmNotifications()

  const { notifications, dismissAll } = useAlarmStore()

  return (
    <div className="fixed bottom-4 right-4 z-[100] flex flex-col gap-2 items-end">
      {/* Tümünü kapat butonu — birden fazla bildirim varsa göster */}
      <AnimatePresence>
        {notifications.length > 1 && (
          <motion.button
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 8 }}
            onClick={dismissAll}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-[var(--bg-card)] border border-[var(--border)] rounded-full text-xs text-[var(--text-secondary)] hover:text-[var(--text-primary)] shadow transition-colors"
          >
            <BellOff size={12} />
            Tümünü kapat ({notifications.length})
          </motion.button>
        )}
      </AnimatePresence>

      <AnimatePresence mode="popLayout">
        {notifications.map(({ alarm, receivedAt }) => (
          <NotificationCard
            key={alarm.id}
            alarmId={alarm.id}
            cameraId={alarm.camera_id}
            alarmType={alarm.alarm_type}
            receivedAt={receivedAt}
          />
        ))}
      </AnimatePresence>
    </div>
  )
}
