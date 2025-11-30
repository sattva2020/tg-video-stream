import { defineConfig, devices } from '@playwright/test';

const baseURL = process.env.BASE_URL || 'http://localhost:3000';
const webServerCommand = process.env.PLAYWRIGHT_WEB_COMMAND || 'npm run dev';

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
    reuseExistingServer: !process.env.CI,
    timeout: 120 * 1000,
  },
});
