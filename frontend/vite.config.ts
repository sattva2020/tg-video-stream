import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import { visualizer } from 'rollup-plugin-visualizer'

export default defineConfig({
  plugins: [
    react(),
    process.env.ANALYZE === 'true' && visualizer({
      filename: '../.internal/frontend-logs/perf/profiling/bundle-report.html',
      open: false,
      gzipSize: true,
      brotliSize: true,
    })
  ],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    allowedHosts: [
      'localhost',
      '127.0.0.1',
      'flowbooster.xyz',  // Продакшн домен
      '.flowbooster.xyz', // Поддомены flowbooster.xyz
      '.ngrok-free.dev',  // Разрешаем все ngrok домены
    ],
    proxy: {
      // Проксируем API запросы на локальный бэкенд
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
        // Важно: передаём cookies между доменами
        cookieDomainRewrite: '',
        configure: (proxy) => {
          proxy.on('proxyReq', (proxyReq, req) => {
            // Логируем cookies для отладки OAuth
            if (req.url?.includes('/auth/google')) {
              console.log('[Proxy] OAuth request:', req.url);
              console.log('[Proxy] Cookies:', req.headers.cookie);
            }
          });
          proxy.on('proxyRes', (proxyRes, req) => {
            if (req.url?.includes('/auth/google')) {
              console.log('[Proxy] OAuth response status:', proxyRes.statusCode);
              console.log('[Proxy] Set-Cookie:', proxyRes.headers['set-cookie']);
            }
          });
        },
      },
    },
  },
  build: {
    sourcemap: true,
    minify: 'esbuild',
    // Отключаем manualChunks - пусть Vite сам разбивает
    chunkSizeWarningLimit: 1000,
  }
})
