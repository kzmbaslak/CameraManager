// Uygulama geneli toast bildirimlerini gosterir.
import { useEffect } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { AlertCircle, CheckCircle2, Info, X, AlertTriangle } from 'lucide-react'
import { type ToastMessage, useToastStore } from '../../stores/toastStore'

const variantClasses = {
  success: 'border-[var(--success)]/30 bg-[var(--success)]/10 text-[var(--success)]',
  danger: 'border-[var(--danger)]/30 bg-[var(--danger)]/10 text-[var(--danger)]',
  warning: 'border-[var(--warning)]/30 bg-[var(--warning)]/10 text-[var(--warning)]',
  info: 'border-[var(--accent)]/30 bg-[var(--accent)]/10 text-[var(--accent)]',
}

const icons = {
  success: <CheckCircle2 size={18} />,
  danger: <AlertCircle size={18} />,
  warning: <AlertTriangle size={18} />,
  info: <Info size={18} />,
}

function ToastItem({ toast }: { toast: ToastMessage }) {
  const removeToast = useToastStore((state) => state.removeToast)

  useEffect(() => {
    const timer = window.setTimeout(() => removeToast(toast.id), 4500)
    return () => window.clearTimeout(timer)
  }, [removeToast, toast.id])

  return (
    <motion.div
      layout
      initial={{ opacity: 0, x: 24, scale: 0.98 }}
      animate={{ opacity: 1, x: 0, scale: 1 }}
      exit={{ opacity: 0, x: 24, scale: 0.98 }}
      transition={{ duration: 0.16 }}
      className={`w-full rounded-lg border p-3 shadow-xl backdrop-blur ${variantClasses[toast.variant]}`}
      role="status"
      aria-live="polite"
    >
      <div className="flex items-start gap-3">
        <span className="mt-0.5 shrink-0">{icons[toast.variant]}</span>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold text-[var(--text-primary)]">{toast.title}</p>
          {toast.description && (
            <p className="mt-1 text-xs leading-5 text-[var(--text-secondary)]">{toast.description}</p>
          )}
        </div>
        <button
          type="button"
          aria-label="Bildirimi kapat"
          onClick={() => removeToast(toast.id)}
          className="rounded-md p-1 text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-secondary)] hover:text-[var(--text-primary)]"
        >
          <X size={14} />
        </button>
      </div>
    </motion.div>
  )
}

export function ToastViewport() {
  const toasts = useToastStore((state) => state.toasts)

  return (
    <div className="pointer-events-none fixed right-4 top-4 z-[220] flex w-[min(380px,calc(100vw-32px))] flex-col gap-2">
      <AnimatePresence initial={false}>
        {toasts.map((toast) => (
          <div key={toast.id} className="pointer-events-auto">
            <ToastItem toast={toast} />
          </div>
        ))}
      </AnimatePresence>
    </div>
  )
}
