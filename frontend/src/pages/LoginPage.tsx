// Kullanıcı giriş sayfası; JWT oturumunu başlatır.
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { isAxiosError } from 'axios'
import { Camera, Lock } from 'lucide-react'
import { authApi } from '../api/auth'
import { useAuthStore } from '../stores/authStore'
import { Input } from '../components/ui/Input'
import { PasswordInput } from '../components/ui/PasswordInput'
import { Button } from '../components/ui/Button'

export function LoginPage() {
  const navigate = useNavigate()
  const login = useAuthStore((s) => s.login)
  const sessionExpired = new URLSearchParams(window.location.search).get('expired') === '1'

  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const data = await authApi.login(username, password)
      login(data.access_token, data.username, data.role)
      navigate('/', { replace: true })
    } catch (err) {
      if (isAxiosError(err)) {
        if (!err.response) {
          setError('Sunucuya bağlanılamadı. Bağlantınızı kontrol edin.')
        } else if (err.response.status === 401) {
          setError('Kullanıcı adı veya şifre hatalı.')
        } else {
          setError('Giriş yapılamadı. Lütfen daha sonra tekrar deneyin.')
        }
      } else {
        setError('Giriş yapılamadı. Lütfen daha sonra tekrar deneyin.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-[var(--bg-primary)] flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, ease: 'easeOut' }}
        className="w-full max-w-sm"
      >
        {/* Logo */}
        <div className="flex flex-col items-center mb-8">
          <div className="w-14 h-14 rounded-2xl bg-[var(--accent)] flex items-center justify-center mb-4">
            <Camera size={28} className="text-white" />
          </div>
          <h1 className="text-xl font-bold text-[var(--text-primary)]">Kamera Yönetimi</h1>
          <p className="text-sm text-[var(--text-secondary)] mt-1">Sisteme giriş yapın</p>
        </div>

        {/* Form */}
        <div className="bg-[var(--bg-card)] border border-[var(--border)] rounded-xl p-6">
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <Input
              label="Kullanıcı Adı"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="kullanıcı adı"
              autoComplete="username"
              autoFocus
            />
            <PasswordInput
              label="Şifre"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              autoComplete="current-password"
            />

            {error && (
              <motion.p
                initial={{ opacity: 0, y: -4 }}
                animate={{ opacity: 1, y: 0 }}
                className="text-sm text-[var(--danger)] text-center"
              >
                {error}
              </motion.p>
            )}

            {!error && sessionExpired && (
              <p className="rounded-md border border-[var(--warning)]/30 bg-[var(--warning)]/10 px-3 py-2 text-center text-xs text-[var(--warning)]">
                Oturum suresi doldu. Devam etmek icin tekrar giris yapin.
              </p>
            )}

            <Button type="submit" loading={loading} icon={<Lock size={15} />} className="mt-1">
              Giriş Yap
            </Button>
          </form>
        </div>
      </motion.div>
    </div>
  )
}
