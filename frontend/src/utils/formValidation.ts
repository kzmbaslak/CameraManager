// Shared lightweight validation helpers for management forms.
export type FieldErrors = Record<string, string>

export const hasErrors = (errors: FieldErrors) => Object.keys(errors).length > 0

export function requiredText(value: unknown, message: string): string | undefined {
  return typeof value === 'string' && value.trim() ? undefined : message
}

export function validateHost(value: unknown, message = 'Gecerli bir IP veya host girin.'): string | undefined {
  if (typeof value !== 'string' || !value.trim()) return message
  if (/^https?:\/\//i.test(value.trim()) || /^rtsp:\/\//i.test(value.trim())) {
    return 'Host alanina protokol yazmayin; sadece IP veya DNS adi girin.'
  }
  return /^[a-zA-Z0-9.-]+$/.test(value.trim()) ? undefined : message
}

export function validatePort(value: unknown, label: string): string | undefined {
  const port = Number(value)
  if (!Number.isInteger(port) || port < 1 || port > 65535) {
    return `${label} 1-65535 arasinda olmalidir.`
  }
  return undefined
}

export function validateNumberRange(value: unknown, label: string, min: number, max: number): string | undefined {
  const number = Number(value)
  if (!Number.isFinite(number) || number < min || number > max) {
    return `${label} ${min}-${max} arasinda olmalidir.`
  }
  return undefined
}

export function validateNewPassword(value: unknown, required: boolean): string | undefined {
  if (typeof value !== 'string' || !value) {
    return required ? 'Sifre zorunludur.' : undefined
  }
  return value.length >= 8 ? undefined : 'Sifre en az 8 karakter olmalidir.'
}
