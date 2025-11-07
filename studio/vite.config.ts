import path from "path"
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { getSentryPlugin } from './sentry.config'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    react(),
    getSentryPlugin(),
  ].filter(Boolean),
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      }
    }
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    assetsDir: 'assets',
    sourcemap: true, // Enable sourcemaps for Sentry error tracking
    minify: 'esbuild',
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
          monaco: ['@monaco-editor/react']
        }
      }
    }
  }
})