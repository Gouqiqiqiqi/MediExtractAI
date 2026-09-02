import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        // Split the dependencies that never change away from the app code.
        // Asset filenames are content-hashed, so without this every deploy
        // invalidates React along with the one component that actually
        // changed, and every returning visitor re-downloads the lot.
        manualChunks: {
          react: ['react', 'react-dom', 'react-router-dom'],
        },
      },
    },
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        // Overridable so the dev server can be pointed at a backend that is not
        // on this host — a container on the same network, typically.
        target: process.env.VITE_API_PROXY || 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});
