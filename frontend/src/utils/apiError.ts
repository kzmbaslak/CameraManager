// API hatalarini kullaniciya okunabilir tek cumleye cevirir.
interface ApiErrorLike {
  response?: {
    data?: {
      detail?: string
    }
  }
  message?: string
}

export function getApiErrorMessage(error: unknown, fallback: string): string {
  const err = error as ApiErrorLike
  if (!err.response && err.message === 'Network Error') {
    return 'Backend yanit vermedi veya islem zaman asimina ugradi. Servisin calistigini ve ag baglantisini kontrol edin.'
  }
  return err.response?.data?.detail || err.message || fallback
}
