import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// The FastAPI backend (app/main.py) has no CORS middleware, and we don't
// touch app/ to add one. Proxying /api -> the backend makes every request
// same-origin from the browser's point of view, which sidesteps CORS
// entirely instead of fighting it.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
