import { test, expect } from '@playwright/test';

test.describe('Admin Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    // Mock login or assume setup state
    // For now, we just navigate to the dashboard
    await page.goto('/admin/dashboard');
  });

  test('should display stream controls', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'Stream Control' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Start Stream' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Stop Stream' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Restart Stream' })).toBeVisible();
  });

  test('should display metrics', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'System Metrics' })).toBeVisible();
    await expect(page.getByText('CPU Usage')).toBeVisible();
    await expect(page.getByText('Memory Usage')).toBeVisible();
  });

  test('should display logs', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'System Logs' })).toBeVisible();
    await expect(page.locator('.logs-container')).toBeVisible();
  });

  test('should display playlist editor', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'Playlist Management' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Add Item' })).toBeVisible();
    await expect(page.locator('.playlist-item')).toBeVisible();
  });
});
