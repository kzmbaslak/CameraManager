// Alarm tablosu satırı — tip, açıklama, durum, güven skoru, zaman, onaylama
import dayjs from 'dayjs'
import 'dayjs/locale/tr'
import { CheckCircle, Wifi, User, Activity } from 'lucide-react'
import { Badge } from '../ui/Badge'
import { Button } from '../ui/Button'
import type { Alarm } from '../../types/api'

dayjs.locale('tr')

interface AlarmRowProps {
  alarm: Alarm
  cameraName?: string
  onAcknowledge?: (id: number) => void
  acknowledging?: boolean
}

const typeConfig: Record<string, {
  label: string
  icon: React.ReactNode
  badgeVariant: 'danger' | 'warning' | 'neutral'
}> = {
  human_detected: {
    label: 'İnsan Tespiti',
    icon: <User size={13} />,
    badgeVariant: 'danger',
  },
  motion_detected: {
    label: 'Hareket Tespiti',
    icon: <Activity size={13} />,
    badgeVariant: 'warning',
  },
  camera_offline: {
    label: 'Kamera Çevrimdışı',
    icon: <Wifi size={13} className="opacity-50" />,
    badgeVariant: 'neutral',
  },
}

const statusVariant = {
  new: 'danger',
  acknowledged: 'warning',
  resolved: 'success',
} as const

const statusLabel = { new: 'Yeni', acknowledged: 'Onaylandı', resolved: 'Çözüldü' }

/** Alarm tablosunda tek bir alarm satırını gösterir */
export function AlarmRow({ alarm, cameraName, onAcknowledge, acknowledging }: AlarmRowProps) {
  const cfg = typeConfig[alarm.alarm_type] ?? {
    label: alarm.alarm_type,
    icon: null,
    badgeVariant: 'neutral' as const,
  }

  return (
    <tr className="border-b border-border last:border-0 hover:bg-bg-secondary/60 transition-colors">
      {/* Kamera */}
      <td className="px-4 py-3">
        <span className="text-sm font-medium text-text-primary">
          {cameraName ?? `#${alarm.camera_id}`}
        </span>
      </td>

      {/* Tip + açıklama */}
      <td className="px-4 py-3 max-w-[280px]">
        <div className="flex items-start gap-2">
          <span className={`mt-0.5 shrink-0 ${
            alarm.alarm_type === 'human_detected' ? 'text-danger' :
            alarm.alarm_type === 'motion_detected' ? 'text-warning' :
            'text-text-secondary'
          }`}>
            {cfg.icon}
          </span>
          <div className="min-w-0">
            <p className="text-sm font-medium text-text-primary leading-tight">
              {cfg.label}
            </p>
            {alarm.message && (
              <p className="text-xs text-text-secondary mt-0.5 leading-snug">
                {alarm.message}
              </p>
            )}
          </div>
        </div>
      </td>

      {/* Durum */}
      <td className="px-4 py-3">
        <Badge variant={statusVariant[alarm.status]} dot>
          {statusLabel[alarm.status]}
        </Badge>
      </td>

      {/* Güven — yalnızca insan/hareket için anlamlı */}
      <td className="px-4 py-3 text-sm text-text-secondary tabular-nums">
        {alarm.alarm_type !== 'camera_offline' && alarm.confidence != null
          ? `%${Math.round(alarm.confidence * 100)}`
          : '—'}
      </td>

      {/* Zaman */}
      <td className="px-4 py-3 text-sm text-text-secondary whitespace-nowrap">
        {alarm.created_at
          ? dayjs(alarm.created_at).format('DD.MM.YYYY HH:mm:ss')
          : '—'}
      </td>

      {/* Onayla */}
      <td className="px-4 py-3">
        {alarm.status === 'new' && onAcknowledge && (
          <Button
            size="sm"
            variant="secondary"
            icon={<CheckCircle size={13} />}
            loading={acknowledging}
            onClick={() => onAcknowledge(alarm.id)}
          >
            Onayla
          </Button>
        )}
      </td>
    </tr>
  )
}
