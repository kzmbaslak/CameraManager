// Durum ve kategori bilgisini küçük rozet olarak gösterir.
import { type ReactNode } from 'react'

type BadgeVariant = 'success' | 'danger' | 'warning' | 'info' | 'neutral'

interface BadgeProps {
  variant?: BadgeVariant
  children: ReactNode
  dot?: boolean
  icon?: ReactNode
  className?: string
}

const variantClasses: Record<BadgeVariant, string> = {
  success: 'bg-success/15 text-success border border-success/20',
  danger: 'bg-danger/15 text-danger border border-danger/25',
  warning: 'bg-warning/15 text-warning border border-warning/25',
  info: 'bg-info/15 text-info border border-info/25',
  neutral: 'bg-bg-elevated text-text-secondary border border-border',
}

const dotColors: Record<BadgeVariant, string> = {
  success: 'bg-success',
  danger: 'bg-danger',
  warning: 'bg-warning',
  info: 'bg-accent',
  neutral: 'bg-text-secondary',
}

export function Badge({ variant = 'neutral', children, dot = false, icon, className = '' }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded px-2 py-0.5 text-xs font-medium ${variantClasses[variant]} ${className}`}
    >
      {dot && <span className={`w-1.5 h-1.5 rounded-full ${dotColors[variant]}`} />}
      {icon}
      {children}
    </span>
  )
}
