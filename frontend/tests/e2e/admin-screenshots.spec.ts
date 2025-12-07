/**
 * Admin Screenshots - Visual inspection of all admin pages
 */

import { test, Page } from '@playwright/test';

const BASE_URL = process.env.TEST_BASE_URL || 'https://sattva-streamer.top';

async function setupAdminAuth(page: Page) {
  const mockPayload = {
    sub: 'test-admin-id',
    email: 'admin@test.com',
    name: 'Test Admin',
    role: 'admin',
    exp: Math.floor(Date.now() / 1000) + 3600,
    iat: Math.floor(Date.now() / 1000),
  };
  
  const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
  const payload = btoa(JSON.stringify(mockPayload));
  const mockToken = `${header}.${payload}.test-signature`;
  
  await page.addInitScript((token) => {
    localStorage.setItem('token', token);
  }, mockToken);
  
  // Mock all API calls to prevent redirect loops
  await page.route('**/api/users/me', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 'test-admin-id',
        email: 'admin@test.com',
        name: 'Test Admin',
        role: 'admin',
        is_active: true,
      }),
    });
  });
  
  await page.route('**/api/admin/**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([]),
    });
  });
  
  await page.route('**/api/playlist/**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([]),
    });
  });
  
  await page.route('**/api/schedule/**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([]),
    });
  });
  
  await page.route('**/api/system/**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ cpu_percent: 25, memory_percent: 40, disk_percent: 60 }),
    });
  });
  
  await page.route('**/api/analytics/**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ data: [], total: 0 }),
    });
  });
}

test.describe('Admin Pages Screenshots', () => {
  
  test('1. Playlist page screenshot', async ({ page }) => {
    await setupAdminAuth(page);
    await page.goto(`${BASE_URL}/playlist`);
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(3000);
    await page.screenshot({ path: 'test-results/screenshot-1-playlist.png', fullPage: true });
    console.log('Screenshot saved: screenshot-1-playlist.png');
  });
  
  test('2. Schedule page screenshot', async ({ page }) => {
    await setupAdminAuth(page);
    await page.goto(`${BASE_URL}/schedule`);
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(3000);
    await page.screenshot({ path: 'test-results/screenshot-2-schedule.png', fullPage: true });
    console.log('Screenshot saved: screenshot-2-schedule.png');
  });
  
  test('3. Admin page screenshot', async ({ page }) => {
    await setupAdminAuth(page);
    await page.goto(`${BASE_URL}/admin`);
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(3000);
    await page.screenshot({ path: 'test-results/screenshot-3-admin.png', fullPage: true });
    console.log('Screenshot saved: screenshot-3-admin.png');
  });
  
  test('4. Pending users page screenshot', async ({ page }) => {
    await setupAdminAuth(page);
    await page.goto(`${BASE_URL}/admin/pending`);
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(3000);
    await page.screenshot({ path: 'test-results/screenshot-4-pending.png', fullPage: true });
    console.log('Screenshot saved: screenshot-4-pending.png');
  });
  
  test('5. Monitoring page screenshot', async ({ page }) => {
    await setupAdminAuth(page);
    await page.goto(`${BASE_URL}/admin/monitoring`);
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(3000);
    await page.screenshot({ path: 'test-results/screenshot-5-monitoring.png', fullPage: true });
    console.log('Screenshot saved: screenshot-5-monitoring.png');
  });
  
  test('6. Analytics page screenshot', async ({ page }) => {
    await setupAdminAuth(page);
    await page.goto(`${BASE_URL}/admin/analytics`);
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(3000);
    await page.screenshot({ path: 'test-results/screenshot-6-analytics.png', fullPage: true });
    console.log('Screenshot saved: screenshot-6-analytics.png');
  });
  
  test('7. Dashboard page screenshot', async ({ page }) => {
    await setupAdminAuth(page);
    await page.goto(`${BASE_URL}/dashboard`);
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(3000);
    await page.screenshot({ path: 'test-results/screenshot-7-dashboard.png', fullPage: true });
    console.log('Screenshot saved: screenshot-7-dashboard.png');
  });
});
