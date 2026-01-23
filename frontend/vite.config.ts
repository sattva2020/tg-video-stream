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
    host: '0.0.0.0', // Listen on all interfaces for Docker/domain access
    port: 3000,
    allowedHosts: [
      'localhost',
      '127.0.0.1',
      'flowbooster.xyz',  // Продакшн домен
      '.flowbooster.xyz', // Поддомены flowbooster.xyz
      '.ngrok-free.dev',  // Разрешаем все ngrok домены
      'sattva-streamer.top', // Production domain
      '.sattva-streamer.top', // All subdomains
      'api.sattva-streamer.top',
      'grafana.sattva-streamer.top',
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
        // Manual chunks для оптимального code splitting и предотвращения циклических зависимостей
        manualChunks: (id) => {
          // Vendor chunks - стратегическое разделение для оптимизации кэширования
          if (id.includes('node_modules')) {
            // React core framework (редко меняется)
            if (id.includes('react') || id.includes('react-dom') || id.includes('scheduler')) {
              return 'react-vendor';
            }

            // Routing (меняется независимо от React)
            if (id.includes('react-router')) {
              return 'router-vendor';
            }

            // Data fetching and state management
            if (id.includes('@tanstack/react-query') || id.includes('axios') || id.includes('zustand')) {
              return 'query-vendor';
            }

            // UI libraries (@heroui, @radix-ui, framer-motion, etc.)
            if (id.includes('@heroui') ||
                id.includes('@radix-ui') ||
                id.includes('framer-motion') ||
                id.includes('lucide-react') ||
                id.includes('sonner') ||
                id.includes('aceternity-ui') ||
                id.includes('magic-ui')) {
              return 'ui-vendor';
            }

            // Drag and drop libraries
            if (id.includes('@dnd-kit') || id.includes('@hello-pangea/dnd')) {
              return 'dnd-vendor';
            }

            // Form handling and validation
            if (id.includes('react-hook-form') ||
                id.includes('@hookform/resolvers') ||
                id.includes('zod')) {
              return 'form-vendor';
            }

            // Internationalization
            if (id.includes('i18next') || id.includes('react-i18next')) {
              return 'i18n-vendor';
            }

            // Three.js and 3D rendering
            if (id.includes('three') ||
                id.includes('@react-three')) {
              return 'three-vendor';
            }

            // Charts and visualization
            if (id.includes('recharts')) {
              return 'charts-vendor';
            }

            // Utility libraries
            if (id.includes('date-fns') ||
                id.includes('clsx') ||
                id.includes('class-variance-authority') ||
                id.includes('tailwind-merge') ||
                id.includes('jwt-decode') ||
                id.includes('@sentry/react')) {
              return 'utils-vendor';
            }

            // Catch-all for other vendor dependencies
            return 'vendor';
          }

          // Application chunks - feature-based splitting
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
