// Uygulama kökü; React Query sağlayıcısını ve router'ı bağlar.
import { useEffect } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AppRouter } from './router'
import { useSystemSettingsStore } from './stores/systemSettingsStore'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 30_000,
    },
  },
})

function ThemeController() {
  const themeMode = useSystemSettingsStore((s) => s.themeMode)

  useEffect(() => {
    document.documentElement.dataset.theme = themeMode
  }, [themeMode])

  return null
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeController />
      <AppRouter />
    </QueryClientProvider>
  )
}
