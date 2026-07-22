// Axios HTTP istemcisi — JWT interceptor ile
import axios from 'axios'
import { useAuthStore } from '../stores/authStore'

const client = axios.create({
  baseURL: '/api',
  timeout: 300000,
  headers: { 'Content-Type': 'application/json' },
})

// Her istekte Authorization header'ına JWT token ekle
client.interceptors.request.use((config) => {
  const { token, isExpired, logout } = useAuthStore.getState()
  if (token && isExpired()) {
    logout()
    if (window.location.pathname !== '/login') {
      window.location.href = '/login?expired=1'
    }
    return Promise.reject(new Error('Oturum suresi doldu.'))
  }
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 401 yanıtında token temizle ve login sayfasına yönlendir.
// Login isteğinin kendisi 401 dönerse (hatalı kullanıcı adı/şifre) burası
// devreye girmez — aksi halde sayfa anında reload olur ve LoginPage'in
// gösterdiği hata mesajı kullanıcıya görünmeden kaybolur.
client.interceptors.response.use(
  (response) => response,
  (error) => {
    const isLoginRequest = error.config?.url?.includes('/auth/login')
    if (error.response?.status === 401 && !isLoginRequest) {
      useAuthStore.getState().logout()
      window.location.href = '/login?expired=1'
    }
    return Promise.reject(error)
  }
)

export default client
