// Uygulama geneli kisa islem bildirimlerini yoneten store.
import { create } from 'zustand'

export type ToastVariant = 'success' | 'danger' | 'warning' | 'info'

export interface ToastMessage {
  id: string
  title: string
  description?: string
  variant: ToastVariant
}

interface ToastState {
  toasts: ToastMessage[]
  showToast: (toast: Omit<ToastMessage, 'id'>) => void
  removeToast: (id: string) => void
}

export const useToastStore = create<ToastState>((set) => ({
  toasts: [],
  showToast: (toast) => {
    const id = `${Date.now()}-${Math.random().toString(16).slice(2)}`
    set((state) => ({ toasts: [...state.toasts.slice(-3), { ...toast, id }] }))
  },
  removeToast: (id) => {
    set((state) => ({ toasts: state.toasts.filter((toast) => toast.id !== id) }))
  },
}))
