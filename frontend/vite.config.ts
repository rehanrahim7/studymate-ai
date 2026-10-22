import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const dirname = path.dirname(fileURLToPath(import.meta.url))

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(dirname, './src'),
    },
  },
  server: {
    port: 5173,
    strictPort: false,
    proxy: {
      // Lets the browser call "/api/..." during development without CORS.
      '/api': {
        target: process.env.VITE_API_PROXY_TARGET ?? 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    rollupOptions: {
      output: {
        // Split the heavy vendor libraries so they cache independently.
        manualChunks(id) {
          if (!id.includes('node_modules')) return undefined
          if (id.includes('@radix-ui')) return 'radix'
          if (id.includes('react')) return 'react'
          return undefined
        },
      },
    },
  },
})
