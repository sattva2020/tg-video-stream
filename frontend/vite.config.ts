import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import { visualizer } from 'rollup-plugin-visualizer'
import fs from 'fs'

/**
 * Case-sensitivity plugin for Vite
 * Detects import path casing mismatches that cause issues on case-sensitive filesystems (Linux)
 * while developing on case-insensitive filesystems (Windows/macOS)
 */
function caseSensitivityCheck() {
  const issues: Array<{ file: string; import: string; expected: string }> = []
  const checkedFiles = new Set<string>()

  return {
    name: 'case-sensitivity-check',

    resolveId(id: string, importer?: string) {
      if (!importer) return null

      // Only check source files, skip node_modules
      if (id.includes('node_modules') || importer.includes('node_modules')) {
        return null
      }

      // Skip virtual modules and special paths
      if (id.startsWith('\0') || id.startsWith('/@/') || id.startsWith('/@vite/')) {
        return null
      }

      try {
        // Get the directory of the importing file
        const importerDir = path.dirname(importer)

        // Resolve the import path relative to the importer
        const resolved = path.resolve(importerDir, id)

        // Skip if already checked
        if (checkedFiles.has(resolved)) {
          return null
        }
        checkedFiles.add(resolved)

        // Check if the file exists
        if (!fs.existsSync(resolved)) {
          return null // Let Vite handle missing files
        }

        // Get the actual filename from filesystem (with correct casing)
        const actualPath = getActualPath(resolved)

        // Compare resolved path with actual path
        if (resolved !== actualPath) {
          issues.push({
            file: importer,
            import: id,
            expected: actualPath
          })
        }
      } catch (error) {
        // Ignore errors (file not found, permission issues, etc.)
      }

      return null
    },

    buildEnd() {
      if (issues.length > 0) {
        this.error(
          `Case-sensitivity issues detected:\n\n` +
          issues.map(issue =>
            `  ❌ In ${issue.file}:\n` +
            `     Import: "${issue.import}"\n` +
            `     Expected: "${issue.expected}"\n`
          ).join('\n') +
          `\n${issues.length} case-sensitivity issue(s) found.\n` +
          `These imports will fail on case-sensitive filesystems (Linux).\n` +
          `Please fix the import casing to match the actual file paths.`
        )
      }
    }
  }
}

/**
 * Get the actual path with correct casing from the filesystem
 */
function getActualPath(targetPath: string): string {
  try {
    // Split path into parts
    const parts = targetPath.split(path.sep)
    let currentPath = parts[0] // Drive letter or root

    // Build path incrementally, checking each part
    for (let i = 1; i < parts.length; i++) {
      const part = parts[i]
      const testPath = path.join(currentPath, part)

      if (fs.existsSync(testPath)) {
        // Check if the casing matches by listing directory
        const parentPath = currentPath
        const actualFiles = fs.readdirSync(parentPath)

        // Find the actual filename (case-sensitive)
        const actualName = actualFiles.find(
          f => f.toLowerCase() === part.toLowerCase()
        )

        if (actualName) {
          currentPath = path.join(currentPath, actualName)
        } else {
          // File not found (shouldn't happen as we checked exists)
          currentPath = testPath
        }
      } else {
        // Path doesn't exist, return as-is
        currentPath = testPath
      }
    }

    return currentPath
  } catch {
    // On error, return original path
    return targetPath
  }
}

/**
 * Bundle size monitoring plugin for Vite
 * Reports bundle sizes and warnings for chunks exceeding size limits
 */
function bundleSizeMonitor() {
  const sizeLimits = {
    // Critical vendor chunks that should be kept small
    'react-vendor': 200,
    'router-vendor': 100,
    'query-vendor': 150,
    'ui-vendor': 300,
    // Feature chunks
    'pages-admin': 200,
    'pages-notifications': 150,
    'components-auth': 100,
    // Default limit for other chunks
    'default': 250,
  }

  return {
    name: 'bundle-size-monitor',

    generateBundle(options: any, bundle: any) {
      const chunkSizes: Array<{ name: string; size: number; limit: number }> = []
      let totalSize = 0
      const warnings: string[] = []

      // Calculate sizes for all chunks
      for (const [fileName, chunk] of Object.entries(bundle)) {
        if (chunk.type === 'chunk') {
          const size = chunk.code.length / 1024 // Convert to KB
          totalSize += size

          // Determine limit based on chunk name
          let limit = sizeLimits.default
          for (const [chunkName, chunkLimit] of Object.entries(sizeLimits)) {
            if (chunkName !== 'default' && fileName.includes(chunkName)) {
              limit = chunkLimit
              break
            }
          }

          chunkSizes.push({ name: fileName, size, limit })

          // Check if chunk exceeds limit
          if (size > limit) {
            warnings.push(
              `  ⚠️  ${fileName}: ${size.toFixed(2)} KB (limit: ${limit} KB)`
            )
          }
        }
      }

      // Sort chunks by size (descending)
      chunkSizes.sort((a, b) => b.size - a.size)

      // Report bundle sizes
      console.log('\n' + '='.repeat(80))
      console.log('📦 Bundle Size Report')
      console.log('='.repeat(80))

      // Report largest chunks
      console.log('\n📊 Largest chunks:')
      chunkSizes.slice(0, 10).forEach(({ name, size, limit }) => {
        const status = size > limit ? '❌' : '✅'
        const percentage = ((size / limit) * 100).toFixed(0)
        console.log(
          `  ${status} ${name}\n` +
          `     Size: ${size.toFixed(2)} KB / ${limit} KB (${percentage}%)\n`
        )
      })

      // Report total size
      console.log(`\n💾 Total bundle size: ${totalSize.toFixed(2)} KB`)
      console.log(`📦 Total chunks: ${chunkSizes.length}`)

      // Report warnings
      if (warnings.length > 0) {
        console.log('\n⚠️  Size Warnings:')
        warnings.forEach(warning => console.log(warning))
        console.log(`\n${warnings.length} chunk(s) exceed size limits.`)
        console.log('Consider code splitting or lazy loading to reduce bundle sizes.\n')
      } else {
        console.log('\n✅ All chunks within size limits!\n')
      }

      console.log('='.repeat(80) + '\n')
    },
  }
}

export default defineConfig({
  plugins: [
    react(),
    caseSensitivityCheck(),
    bundleSizeMonitor(),
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
