import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './tests/vitest/setup.ts',
    reporters: process.env.CI ? ['junit', 'default'] : 'default',
    coverage: {
      reporter: ['text', 'html'],
      reportsDirectory: './tests/vitest/coverage',
    },
    exclude: ['**/node_modules/**', '**/dist/**', '**/tests/e2e/**', '**/tests/playwright/**'],
  },
});
