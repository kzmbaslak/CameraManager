// Etiketli standart form input bileşeni.
import { type InputHTMLAttributes, forwardRef } from 'react'

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, className = '', id, ...props }, ref) => {
    const inputId = id ?? label?.toLowerCase().replace(/\s+/g, '-')
    const errorId = error && inputId ? `${inputId}-error` : undefined

    return (
      <div className="flex flex-col gap-1.5">
        {label && (
          <label htmlFor={inputId} className="text-sm font-medium text-[var(--text-secondary)]">
            {label}
          </label>
        )}
        <input
          ref={ref}
          id={inputId}
          aria-invalid={error ? true : undefined}
          aria-describedby={errorId}
          className={`
            w-full rounded-lg px-3 py-2 text-sm
            bg-[var(--bg-primary)] border text-[var(--text-primary)]
            placeholder:text-[var(--text-secondary)]
            outline-none transition-colors duration-150
            ${error ? 'border-[var(--danger)] focus:border-[var(--danger)]' : 'border-[var(--border)] focus:border-[var(--accent)]'}
            ${className}
          `}
          {...props}
        />
        {error && <p id={errorId} className="text-xs text-[var(--danger)]">{error}</p>}
      </div>
    )
  }
)

Input.displayName = 'Input'
