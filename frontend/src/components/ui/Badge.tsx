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
  success: 'bg-green-500/15 text-success',
  danger: 'bg-red-500/15 text-danger',
  warning: 'bg-yellow-500/15 text-warning',
  info: 'bg-blue-500/15 text-accent',
  neutral: 'bg-border text-text-secondary',
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
      className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium ${variantClasses[variant]} ${className}`}
    >
      {dot && <span className={`w-1.5 h-1.5 rounded-full ${dotColors[variant]}`} />}
      {icon}
      {children}
    </span>
  )
}
