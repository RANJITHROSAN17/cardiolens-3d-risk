import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  // GitHub Pages serves this repository below /cardiolens-3d-risk/; local dev uses /.
  base: process.env.VITE_BASE_PATH || '/',
  plugins: [react()],
  build: {
    // Three.js is a single vendor dependency; its 189 kB gzip bundle is within the demo budget.
    chunkSizeWarningLimit: 800,
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    strictPort: true,
    allowedHosts: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
});
