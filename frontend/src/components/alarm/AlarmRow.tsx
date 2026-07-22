// Alarm table row with status, confidence, timestamp and quick acknowledgement.
import dayjs from 'dayjs'
import 'dayjs/locale/tr'
import { Activity, CheckCircle, Eye, User, Wifi } from 'lucide-react'
import { Badge } from '../ui/Badge'
import { Button } from '../ui/Button'
import type { Alarm } from '../../types/api'

dayjs.locale('tr')

interface AlarmRowProps {
  alarm: Alarm
  cameraName?: string
  onAcknowledge?: (id: number) => void
  onInspect?: (alarm: Alarm) => void
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
const severityLabel = { low: 'Dusuk', medium: 'Orta', high: 'Yuksek', critical: 'Kritik' }
const severityVariant = { low: 'neutral', medium: 'warning', high: 'danger', critical: 'danger' } as const

export function AlarmRow({ alarm, cameraName, onAcknowledge, onInspect, acknowledging }: AlarmRowProps) {
  const cfg = typeConfig[alarm.alarm_type] ?? {
    label: alarm.alarm_type,
    icon: null,
    badgeVariant: 'neutral' as const,
  }

  return (
    <tr className="border-b border-border transition-colors last:border-0 hover:bg-bg-secondary/60">
      <td className="px-4 py-3">
        <span className="text-sm font-medium text-text-primary">
          {cameraName ?? `#${alarm.camera_id}`}
        </span>
      </td>
      <td className="max-w-[280px] px-4 py-3">
        <div className="flex items-start gap-2">
          <span className={`mt-0.5 shrink-0 ${
            alarm.alarm_type === 'human_detected' ? 'text-danger' :
            alarm.alarm_type === 'motion_detected' ? 'text-warning' :
            'text-text-secondary'
          }`}>
            {cfg.icon}
          </span>
          <div className="min-w-0">
            <p className="text-sm font-medium leading-tight text-text-primary">{cfg.label}</p>
            {alarm.message && (
              <p className="mt-0.5 text-xs leading-snug text-text-secondary">{alarm.message}</p>
            )}
          </div>
        </div>
      </td>
      <td className="px-4 py-3">
        <div className="flex flex-col items-start gap-1">
          <Badge variant={statusVariant[alarm.status]} dot>
            {alarm.false_positive ? 'Yanlis Alarm' : statusLabel[alarm.status]}
          </Badge>
          <Badge variant={severityVariant[alarm.severity]}>
            {severityLabel[alarm.severity]}
          </Badge>
        </div>
      </td>
      <td className="px-4 py-3 text-sm tabular-nums text-text-secondary">
        {alarm.alarm_type !== 'camera_offline' && alarm.confidence != null
          ? `%${Math.round(alarm.confidence * 100)}`
          : '-'}
      </td>
      <td className="whitespace-nowrap px-4 py-3 text-sm text-text-secondary">
        {alarm.created_at ? dayjs(alarm.created_at).format('DD.MM.YYYY HH:mm:ss') : '-'}
      </td>
      <td className="px-4 py-3">
        <div className="flex justify-end gap-2">
          {onInspect && (
            <Button
              size="sm"
              variant="secondary"
              icon={<Eye size={13} />}
              onClick={() => onInspect(alarm)}
              aria-label={`${cameraName ?? `Kamera ${alarm.camera_id}`} alarmÄ±nÄ± incele`}
            >
              Incele
            </Button>
          )}
          {alarm.status === 'new' && onAcknowledge && (
          <Button
            size="sm"
            variant="secondary"
            icon={<CheckCircle size={13} />}
            loading={acknowledging}
            onClick={() => onAcknowledge(alarm.id)}
            aria-label={`${cameraName ?? `Kamera ${alarm.camera_id}`} alarmını onayla`}
          >
            Onayla
          </Button>
          )}
        </div>
      </td>
    </tr>
  )
}
