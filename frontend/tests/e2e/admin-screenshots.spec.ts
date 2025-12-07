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
  
  await page.route('**/api/channels**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([{
        id: '00000000-0000-0000-0000-000000000001',
        name: 'Test Channel',
        telegram_id: '-1001234567890',
        is_active: true,
      }]),
    });
  });
  
  await page.route('**/api/playlist/**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([]),
    });
  });
  
  await page.route('**/api/schedule/calendar**', async (route) => {
    // Generate calendar data for current month
    const now = new Date();
    const year = now.getFullYear();
    const month = now.getMonth() + 1;
    const daysInMonth = new Date(year, month, 0).getDate();
    
    const data = [];
    for (let day = 1; day <= daysInMonth; day++) {
      const dateStr = `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
      data.push({
        date: dateStr,
        slots_count: 0,
        has_conflicts: false,
        slots: [],
      });
    }
    
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(data),
    });
  });
  
  await page.route('**/api/schedule/playlists**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([]),
    });
  });
  
  await page.route('**/api/schedule/templates**', async (route) => {
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
    
    const startTime = Date.now();
    await page.goto(`${BASE_URL}/schedule`);
    const navigationTime = Date.now() - startTime;
    
    await page.waitForLoadState('domcontentloaded');
    const domLoadTime = Date.now() - startTime;
    
    // Wait for calendar grid to appear - use more specific selector
    const gridStart = Date.now();
    try {
      // Try multiple selectors
      const gridSelector = page.locator('.grid.grid-cols-7').first();
      await gridSelector.waitFor({ state: 'visible', timeout: 10000 });
      const gridTime = Date.now() - gridStart;
      console.log(`[PERF] Calendar grid visible: ${gridTime}ms`);
      
      // Count how many day cells are visible
      const dayCells = await page.locator('.grid.grid-cols-7 > div').count();
      console.log(`[PERF] Day cells rendered: ${dayCells}`);
    } catch {
      console.log('[PERF] Calendar grid not found in 10s, checking page content...');
      
      // Debug: check what's on the page
      const hasCalendar = await page.locator('text="Расписание"').count();
      const hasLoading = await page.locator('[class*="animate-pulse"], [class*="skeleton"]').count();
      const hasError = await page.locator('text="Ошибка"').count();
      console.log(`[DEBUG] Has "Расписание": ${hasCalendar}, Loading elements: ${hasLoading}, Errors: ${hasError}`);
    }
    
    await page.waitForTimeout(2000); // Extra wait for animations
    const totalTime = Date.now() - startTime;
    
    console.log(`[PERF] Navigation: ${navigationTime}ms, DOM: ${domLoadTime}ms, Total: ${totalTime}ms`);
    
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
