// Sifre alanlari icin gorunurluk degistirme destekli standart input.
import { forwardRef, type InputHTMLAttributes, useId, useState } from 'react'
import { Eye, EyeOff } from 'lucide-react'

interface PasswordInputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> {
  label?: string
  error?: string
}

export const PasswordInput = forwardRef<HTMLInputElement, PasswordInputProps>(
  ({ label, error, className = '', id, ...props }, ref) => {
    const generatedId = useId()
    const inputId = id ?? label?.toLowerCase().replace(/\s+/g, '-') ?? generatedId
    const errorId = error ? `${inputId}-error` : undefined
    const [visible, setVisible] = useState(false)

    return (
      <div className="flex flex-col gap-1.5">
        {label && (
          <label htmlFor={inputId} className="text-sm font-medium text-[var(--text-secondary)]">
            {label}
          </label>
        )}
        <div className="relative">
          <input
            ref={ref}
            id={inputId}
            type={visible ? 'text' : 'password'}
            aria-invalid={error ? true : undefined}
            aria-describedby={errorId}
            className={`
              w-full rounded-lg px-3 py-2 pr-10 text-sm
              bg-[var(--bg-primary)] border text-[var(--text-primary)]
              placeholder:text-[var(--text-secondary)]
              outline-none transition-colors duration-150
              ${error ? 'border-[var(--danger)] focus:border-[var(--danger)]' : 'border-[var(--border)] focus:border-[var(--accent)]'}
              ${className}
            `}
            {...props}
          />
          <button
            type="button"
            aria-label={visible ? 'Sifreyi gizle' : 'Sifreyi goster'}
            title={visible ? 'Sifreyi gizle' : 'Sifreyi goster'}
            onClick={() => setVisible((value) => !value)}
            className="absolute right-2 top-1/2 -translate-y-1/2 rounded-md p-1 text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-secondary)] hover:text-[var(--text-primary)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
          >
            {visible ? <EyeOff size={16} /> : <Eye size={16} />}
          </button>
        </div>
        {error && <p id={errorId} className="text-xs text-[var(--danger)]">{error}</p>}
      </div>
    )
  }
)

PasswordInput.displayName = 'PasswordInput'
