import { defineConfig, devices } from '@playwright/test';

const port = process.env.PLAYWRIGHT_PORT || '4173';
const baseURL = process.env.BASE_URL || `http://localhost:${port}`;
const webServerCommand = process.env.PLAYWRIGHT_WEB_COMMAND || `npm run dev -- --host 0.0.0.0 --port ${port}`;

export default defineConfig({
  // Изолируем e2e от vitest-спеков, чтобы не подмешивались jest-matchers
  testDir: './tests',
  testMatch: ['**/e2e/**/*.spec.ts', '**/playwright/**/*.spec.ts'],
  testIgnore: '**/vitest/**',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    baseURL,
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: {
    command: webServerCommand,
    url: baseURL,
    reuseExistingServer: false,
    env: {
      VITE_ENABLE_BASIC_LOGIN: 'true',
    },
    timeout: 120 * 1000,
  },
});
