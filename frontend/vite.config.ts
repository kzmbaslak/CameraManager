import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

const rootDir = dirname(fileURLToPath(import.meta.url))

export default defineConfig({
  root: rootDir,
  plugins: [
    react(),
    tailwindcss(),
  ],
  build: {
    rollupOptions: {
      input: resolve(rootDir, 'index.html'),
      output: {
        manualChunks(id) {
          if (!id.includes('node_modules')) return undefined
          if (/[\\/]node_modules[\\/](react|react-dom|react-router-dom)[\\/]/.test(id)) return 'vendor-react'
          if (/[\\/]node_modules[\\/]@tanstack[\\/]react-query[\\/]/.test(id)) return 'vendor-data'
          if (/[\\/]node_modules[\\/](axios|zustand)[\\/]/.test(id)) return 'vendor-data'
          if (/[\\/]node_modules[\\/](framer-motion|lucide-react)[\\/]/.test(id)) return 'vendor-ui'
          if (/[\\/]node_modules[\\/]dayjs[\\/]/.test(id)) return 'vendor-time'
          return 'vendor'
        },
      },
    },
  },
  server: {
    // Geliştirme modunda backend'e proxy
    proxy: {
      '/api': {
        target: 'http://localhost:8090',
        changeOrigin: true,
        timeout: 120000,
        proxyTimeout: 120000,
      },
      '/api/streams': {
        target: 'ws://localhost:8090',
        ws: true,
        changeOrigin: true,
      },
    },
  },
})
