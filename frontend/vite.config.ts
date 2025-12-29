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
    host: '127.0.0.1', // Force IPv4 to avoid ngrok connection issues
    port: 3000,
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
        target: process.env.VITE_API_TARGET || 'http://localhost:8000',
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
      // Проксируем /health, чтобы e2e health-checks ходили в backend
      '/health': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
    },
  },
  build: {
    sourcemap: true,
    minify: 'esbuild',
    chunkSizeWarningLimit: 500,
    
    // Performance budget: оптимизация bundle splitting
    rollupOptions: {
      output: {
        // Manual chunks для оптимального code splitting
        manualChunks: (id) => {
          // Vendor chunks - разделяем крупные библиотеки
          if (id.includes('node_modules')) {
            // React ecosystem
            if (id.includes('react') || id.includes('react-dom') || id.includes('react-router')) {
              return 'vendor-react';
            }
            
            // 3D библиотеки - отдельный большой chunk (lazy loaded)
            if (id.includes('@react-three') || id.includes('three') || id.includes('postprocessing')) {
              return 'vendor-three';
            }
            
            // UI библиотеки
            if (id.includes('@radix-ui') || id.includes('@heroui') || id.includes('framer-motion')) {
              return 'vendor-ui';
            }
            
            // Утилиты
            if (id.includes('lodash') || id.includes('date-fns') || id.includes('zod')) {
              return 'vendor-utils';
            }
            
            // i18n
            if (id.includes('i18next') || id.includes('react-i18next')) {
              return 'vendor-i18n';
            }
            
            // Query/State management
            if (id.includes('@tanstack') || id.includes('zustand') || id.includes('axios')) {
              return 'vendor-data';
            }
            
            // Остальные мелкие библиотеки
            return 'vendor-misc';
          }
          
          // Application chunks
          if (id.includes('/pages/admin/')) {
            return 'pages-admin';
          }
          
          if (id.includes('/pages/notifications/')) {
            return 'pages-notifications';
          }
          
          if (id.includes('/components/auth/')) {
            return 'components-auth';
          }
        },
        
        // Оптимизация имён файлов для кэширования
        chunkFileNames: (chunkInfo) => {
          const facadeModuleId = chunkInfo.facadeModuleId
            ? chunkInfo.facadeModuleId.split('/').pop()?.replace('.tsx', '').replace('.ts', '')
            : 'chunk';
          return `assets/${chunkInfo.name || facadeModuleId}-[hash].js`;
        },
        
        assetFileNames: (assetInfo) => {
          const info = assetInfo.name?.split('.') || [];
          const ext = info[info.length - 1];
          
          if (/png|jpe?g|svg|gif|tiff|bmp|ico/i.test(ext)) {
            return 'assets/images/[name]-[hash][extname]';
          }
          
          if (/woff2?|eot|ttf|otf/i.test(ext)) {
            return 'assets/fonts/[name]-[hash][extname]';
          }
          
          return 'assets/[name]-[hash][extname]';
        },
      },
    },
  }
})
