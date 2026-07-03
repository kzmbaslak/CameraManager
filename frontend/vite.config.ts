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
