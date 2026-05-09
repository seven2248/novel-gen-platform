import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    port: 5173,
    // Proxy API calls to FastAPI backend
    proxy: {
      '/projects': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      '/events': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      '/agent-runs': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
})
