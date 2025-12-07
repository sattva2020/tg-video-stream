/**
 * Schedule Calendar Performance Tests
 * Тестирование производительности загрузки календаря
 */
import { test, expect, Page } from '@playwright/test';

const BASE_URL = process.env.TEST_BASE_URL || 'https://sattva-streamer.top';

// Helper: Setup auth with admin role
async function setupAdminAuth(page: Page) {
  const mockPayload = {
    sub: 'test-admin-id',
    email: 'admin@test.com',
    name: 'Test Admin',
    role: 'superadmin',
    exp: Math.floor(Date.now() / 1000) + 3600,
    iat: Math.floor(Date.now() / 1000),
  };
  
  const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
  const payload = btoa(JSON.stringify(mockPayload));
  const signature = 'test-signature';
  const mockToken = `${header}.${payload}.${signature}`;
  
  await page.addInitScript((token) => {
    localStorage.setItem('token', token);
  }, mockToken);
  
  // Mock user API
  await page.route('**/api/users/me', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 'test-admin-id',
        email: 'admin@test.com',
        name: 'Test Admin',
        role: 'superadmin',
        is_active: true,
        status: 'approved',
      }),
    });
  });

  // Mock channels
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
}

// Generate mock calendar data for 31 days
function generateMockCalendarData() {
  const data = [];
  const year = 2025;
  const month = 12;
  
  for (let day = 1; day <= 31; day++) {
    const dateStr = `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
    data.push({
      date: dateStr,
      slots_count: Math.floor(Math.random() * 3),
      has_conflicts: false,
      slots: day % 5 === 0 ? [{
        id: `slot-${day}`,
        title: `Test Slot ${day}`,
        start_time: '10:00',
        end_time: '12:00',
        color: '#8b5cf6',
        playlist_name: 'Test Playlist',
      }] : [],
    });
  }
  return data;
}

test.describe('Schedule Calendar Performance', () => {
  
  test('measure calendar loading with FAST mock data', async ({ page }) => {
    await setupAdminAuth(page);
    
    // Mock calendar API with INSTANT response
    await page.route('**/api/schedule/calendar**', async (route) => {
      const data = generateMockCalendarData();
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(data),
      });
    });
    
    // Mock templates
    await page.route('**/api/schedule/templates**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
      });
    });
    
    // Mock playlists
    await page.route('**/api/playlists**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
      });
    });
    
    const metrics: Record<string, number> = {};
    const startTime = Date.now();
    
    // Navigate to schedule page
    await page.goto(`${BASE_URL}/schedule`, { waitUntil: 'domcontentloaded' });
    metrics['dom_loaded'] = Date.now() - startTime;
    console.log(`[PERF] DOM loaded: ${metrics['dom_loaded']}ms`);
    
    // Wait for calendar grid
    const gridStart = Date.now();
    const calendarGrid = page.locator('[class*="grid-cols-7"]').first();
    await calendarGrid.waitFor({ state: 'visible', timeout: 30000 });
    metrics['grid_visible'] = Date.now() - gridStart;
    console.log(`[PERF] Grid visible: ${metrics['grid_visible']}ms`);
    
    // Wait for day numbers
    const cellStart = Date.now();
    await page.locator('text="15"').first().waitFor({ state: 'visible', timeout: 30000 });
    metrics['cells_visible'] = Date.now() - cellStart;
    console.log(`[PERF] Day cells visible: ${metrics['cells_visible']}ms`);
    
    // Take screenshot
    await page.screenshot({ path: 'test-results/schedule-fast-mock.png', fullPage: true });
    
    // Count elements
    const dayDivs = await page.locator('[class*="min-h-"][class*="p-2"]').count();
    console.log(`[PERF] Day divs rendered: ${dayDivs}`);
    
    console.log('\n=== FAST MOCK PERFORMANCE ===');
    console.log(`Total time: ${Date.now() - startTime}ms`);
    console.log('===========================\n');
    
    expect(metrics['cells_visible']).toBeLessThan(5000);
  });
  
  test('measure calendar loading with SLOW mock data (2 sec delay)', async ({ page }) => {
    await setupAdminAuth(page);
    
    // Mock calendar API with 2 SECOND delay
    await page.route('**/api/schedule/calendar**', async (route) => {
      await new Promise(resolve => setTimeout(resolve, 2000)); // 2 sec delay
      const data = generateMockCalendarData();
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(data),
      });
    });
    
    await page.route('**/api/schedule/templates**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
      });
    });
    
    await page.route('**/api/playlists**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
      });
    });
    
    const metrics: Record<string, number> = {};
    const startTime = Date.now();
    
    await page.goto(`${BASE_URL}/schedule`, { waitUntil: 'domcontentloaded' });
    metrics['dom_loaded'] = Date.now() - startTime;
    console.log(`[PERF] DOM loaded: ${metrics['dom_loaded']}ms`);
    
    // Check skeletons appear during loading
    await page.waitForTimeout(500);
    await page.screenshot({ path: 'test-results/schedule-loading-state.png', fullPage: true });
    const skeletonsWhileLoading = await page.locator('[class*="animate-pulse"]').count();
    console.log(`[PERF] Skeletons during load: ${skeletonsWhileLoading}`);
    
    // Wait for data to load
    const cellStart = Date.now();
    await page.locator('text="15"').first().waitFor({ state: 'visible', timeout: 30000 });
    metrics['cells_visible'] = Date.now() - cellStart;
    console.log(`[PERF] Day cells visible after API delay: ${metrics['cells_visible']}ms`);
    
    await page.screenshot({ path: 'test-results/schedule-slow-mock.png', fullPage: true });
    
    console.log('\n=== SLOW MOCK PERFORMANCE (2s API delay) ===');
    console.log(`Total time: ${Date.now() - startTime}ms`);
    console.log('Expected: ~2000ms + render time');
    console.log('============================================\n');
    
    // Should be around 2000ms (API delay) + some render time
    expect(metrics['cells_visible']).toBeGreaterThan(1500);
    expect(metrics['cells_visible']).toBeLessThan(5000);
  });

  test('compare with REAL API (no mocks)', async ({ page }) => {
    await setupAdminAuth(page);
    
    // Don't mock calendar API - let it hit real server
    await page.route('**/api/schedule/templates**', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
    });
    await page.route('**/api/playlists**', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
    });
    
    const metrics: Record<string, number> = {};
    const startTime = Date.now();
    
    // Track API response time
    let apiResponseTime = 0;
    page.on('response', async (response) => {
      if (response.url().includes('/api/schedule/calendar')) {
        console.log(`[API] Calendar API status: ${response.status()}`);
        apiResponseTime = Date.now() - startTime;
        console.log(`[API] Calendar API responded at: ${apiResponseTime}ms`);
      }
    });
    
    await page.goto(`${BASE_URL}/schedule`, { waitUntil: 'domcontentloaded' });
    metrics['dom_loaded'] = Date.now() - startTime;
    console.log(`[PERF] DOM loaded: ${metrics['dom_loaded']}ms`);
    
    // Wait for any content or loading state
    await page.waitForTimeout(3000);
    await page.screenshot({ path: 'test-results/schedule-real-api-3sec.png', fullPage: true });
    
    // Check what's on the page
    const pageContent = await page.content();
    const hasCalendarUI = pageContent.includes('Расписание') || pageContent.includes('Schedule');
    const hasSkeletons = pageContent.includes('animate-pulse');
    const hasDayNumbers = />[0-9]{1,2}</.test(pageContent);
    
    console.log(`\n=== REAL API ANALYSIS ===`);
    console.log(`Has calendar UI: ${hasCalendarUI}`);
    console.log(`Has skeletons: ${hasSkeletons}`);
    console.log(`Has day numbers: ${hasDayNumbers}`);
    console.log(`API response time: ${apiResponseTime}ms`);
    console.log(`Total time at 3s mark: ${Date.now() - startTime}ms`);
    console.log(`=========================\n`);
    
    // Wait longer and take another screenshot
    await page.waitForTimeout(7000);
    await page.screenshot({ path: 'test-results/schedule-real-api-10sec.png', fullPage: true });
    
    console.log(`Total time at 10s mark: ${Date.now() - startTime}ms`);
  });
});
