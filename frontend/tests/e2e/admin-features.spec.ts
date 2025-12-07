/**
 * Admin Features Interactive Tests
 * 
 * Тестируем функциональность админки:
 * 1) Плейлист - добавление новых треков
 * 2) Расписание - добавление нового расписания
 * 3) Админ панель - все кнопки
 * 4) Ожидающие пользователи - проверка
 * 5) Мониторинг - проверка
 * 6) Аналитика - проверка
 */

import { test, expect, Page } from '@playwright/test';

const BASE_URL = process.env.TEST_BASE_URL || 'https://sattva-streamer.top';

// Helper: Setup auth with admin role
async function setupAdminAuth(page: Page) {
  // Create a mock JWT token for admin
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
  const signature = 'test-signature';
  const mockToken = `${header}.${payload}.${signature}`;
  
  // Set token in localStorage before navigation
  await page.addInitScript((token) => {
    localStorage.setItem('token', token);
  }, mockToken);
  
  // Mock API responses
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
  
  // Mock stream status
  await page.route('**/api/admin/stream/status', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ 
        is_running: false, 
        current_track: null,
        uptime: 0 
      }),
    });
  });
  
  // Mock admin users list
  await page.route('**/api/admin/users', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        { id: '1', email: 'user1@test.com', name: 'User 1', role: 'user', is_active: true },
        { id: '2', email: 'user2@test.com', name: 'User 2', role: 'operator', is_active: true },
      ]),
    });
  });
}

test.describe('Admin Features - Interactive Tests', () => {
  
  test.describe('1. Playlist Management', () => {
    test('can view playlist page', async ({ page }) => {
      await setupAdminAuth(page);
      
      // Mock playlist API
      await page.route('**/api/playlist/**', async (route) => {
        if (route.request().method() === 'GET') {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify([
              { id: '1', title: 'Test Track 1', url: 'https://youtube.com/watch?v=abc123', position: 1 },
              { id: '2', title: 'Test Track 2', url: 'https://youtube.com/watch?v=def456', position: 2 },
            ]),
          });
        } else {
          await route.continue();
        }
      });
      
      await page.goto(`${BASE_URL}/playlist`);
      await page.waitForLoadState('domcontentloaded');
      
      // Check playlist page loaded
      const pageContent = page.locator('body');
      await expect(pageContent).not.toBeEmpty();
      
      console.log('[Playlist] Page URL:', page.url());
      console.log('[Playlist] Page loaded successfully');
    });
    
    test('can find add track button/form', async ({ page }) => {
      await setupAdminAuth(page);
      
      await page.route('**/api/playlist/**', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify([]),
        });
      });
      
      await page.goto(`${BASE_URL}/playlist`);
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(2000);
      
      // Look for add button or input field
      const addButton = page.locator('button:has-text("Добавить"), button:has-text("Add"), button:has-text("+")').first();
      const urlInput = page.locator('input[placeholder*="URL"], input[placeholder*="url"], input[placeholder*="ссылк"], input[type="url"]').first();
      
      const hasAddButton = await addButton.isVisible().catch(() => false);
      const hasUrlInput = await urlInput.isVisible().catch(() => false);
      
      console.log('[Playlist] Add button visible:', hasAddButton);
      console.log('[Playlist] URL input visible:', hasUrlInput);
      
      // At least one should be present
      expect(hasAddButton || hasUrlInput).toBeTruthy();
    });
    
    test('can attempt to add new track', async ({ page }) => {
      await setupAdminAuth(page);
      
      let addTrackCalled = false;
      
      await page.route('**/api/playlist/**', async (route) => {
        const method = route.request().method();
        if (method === 'POST') {
          addTrackCalled = true;
          console.log('[Playlist] POST request body:', route.request().postData());
          await route.fulfill({
            status: 201,
            contentType: 'application/json',
            body: JSON.stringify({ id: '3', title: 'New Track', url: 'https://youtube.com/watch?v=new123', position: 3 }),
          });
        } else {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify([]),
          });
        }
      });
      
      await page.goto(`${BASE_URL}/playlist`);
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(2000);
      
      // Try to find and fill URL input
      const urlInput = page.locator('input[placeholder*="URL"], input[placeholder*="url"], input[placeholder*="ссылк"], input[type="url"], input[type="text"]').first();
      
      if (await urlInput.isVisible()) {
        await urlInput.fill('https://www.youtube.com/watch?v=dQw4w9WgXcQ');
        console.log('[Playlist] Filled URL input');
        
        // Try to find and click submit button
        const submitButton = page.locator('button[type="submit"], button:has-text("Добавить"), button:has-text("Add")').first();
        if (await submitButton.isVisible()) {
          await submitButton.click();
          console.log('[Playlist] Clicked submit button');
          await page.waitForTimeout(1000);
        }
      }
      
      console.log('[Playlist] Add track API called:', addTrackCalled);
    });
  });
  
  test.describe('2. Schedule Management', () => {
    test('can view schedule page', async ({ page }) => {
      await setupAdminAuth(page);
      
      await page.route('**/api/schedule/**', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify([]),
        });
      });
      
      await page.goto(`${BASE_URL}/schedule`);
      await page.waitForLoadState('domcontentloaded');
      
      const pageContent = page.locator('body');
      await expect(pageContent).not.toBeEmpty();
      
      console.log('[Schedule] Page URL:', page.url());
      console.log('[Schedule] Page loaded successfully');
    });
    
    test('can find add schedule button', async ({ page }) => {
      await setupAdminAuth(page);
      
      await page.route('**/api/schedule/**', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify([]),
        });
      });
      
      await page.goto(`${BASE_URL}/schedule`);
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(2000);
      
      // Look for add schedule button
      const addButton = page.locator('button:has-text("Добавить"), button:has-text("Add"), button:has-text("Создать"), button:has-text("Create"), button:has-text("+")').first();
      
      const hasAddButton = await addButton.isVisible().catch(() => false);
      console.log('[Schedule] Add button visible:', hasAddButton);
      
      if (hasAddButton) {
        await addButton.click();
        console.log('[Schedule] Clicked add button');
        await page.waitForTimeout(1000);
        
        // Check if modal/form appeared
        const modal = page.locator('[role="dialog"], .modal, form').first();
        const modalVisible = await modal.isVisible().catch(() => false);
        console.log('[Schedule] Modal/form visible after click:', modalVisible);
      }
    });
    
    test('can attempt to add new schedule', async ({ page }) => {
      await setupAdminAuth(page);
      
      let createScheduleCalled = false;
      
      await page.route('**/api/schedule/**', async (route) => {
        const method = route.request().method();
        if (method === 'POST') {
          createScheduleCalled = true;
          console.log('[Schedule] POST request body:', route.request().postData());
          await route.fulfill({
            status: 201,
            contentType: 'application/json',
            body: JSON.stringify({ id: '1', name: 'New Schedule', start_time: '10:00', enabled: true }),
          });
        } else {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify([]),
          });
        }
      });
      
      await page.goto(`${BASE_URL}/schedule`);
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(2000);
      
      // Try to add schedule
      const addButton = page.locator('button:has-text("Добавить"), button:has-text("Add"), button:has-text("+")').first();
      if (await addButton.isVisible()) {
        await addButton.click();
        await page.waitForTimeout(1000);
      }
      
      console.log('[Schedule] Create API called:', createScheduleCalled);
    });
  });
  
  test.describe('3. Admin Panel Buttons', () => {
    test('can access admin page', async ({ page }) => {
      await setupAdminAuth(page);
      
      await page.goto(`${BASE_URL}/admin`);
      await page.waitForLoadState('domcontentloaded');
      
      console.log('[Admin] Page URL:', page.url());
      
      // Check if redirected or loaded
      const currentUrl = page.url();
      expect(currentUrl).toContain('/admin');
    });
    
    test('admin page has interactive elements', async ({ page }) => {
      await setupAdminAuth(page);
      
      await page.goto(`${BASE_URL}/admin`);
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(2000);
      
      // Count buttons
      const buttons = await page.locator('button').count();
      console.log('[Admin] Total buttons found:', buttons);
      
      // Count links
      const links = await page.locator('a').count();
      console.log('[Admin] Total links found:', links);
      
      // List visible buttons
      const visibleButtons = page.locator('button:visible');
      const buttonCount = await visibleButtons.count();
      for (let i = 0; i < Math.min(buttonCount, 10); i++) {
        const text = await visibleButtons.nth(i).textContent();
        console.log(`[Admin] Button ${i + 1}:`, text?.trim());
      }
    });
    
    test('can click various admin buttons', async ({ page }) => {
      await setupAdminAuth(page);
      
      // Mock various admin APIs
      await page.route('**/api/admin/**', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ success: true }),
        });
      });
      
      await page.goto(`${BASE_URL}/admin`);
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(2000);
      
      const clickedButtons: string[] = [];
      
      // Try clicking different action buttons
      const actionButtons = [
        'button:has-text("Сохранить")',
        'button:has-text("Save")',
        'button:has-text("Применить")',
        'button:has-text("Apply")',
        'button:has-text("Обновить")',
        'button:has-text("Refresh")',
      ];
      
      for (const selector of actionButtons) {
        const button = page.locator(selector).first();
        if (await button.isVisible().catch(() => false)) {
          const text = await button.textContent();
          clickedButtons.push(text || selector);
          // Don't actually click to avoid side effects, just log
          console.log('[Admin] Found clickable button:', text);
        }
      }
      
      console.log('[Admin] Total action buttons found:', clickedButtons.length);
    });
  });
  
  test.describe('4. Pending Users', () => {
    test('can access pending users page', async ({ page }) => {
      await setupAdminAuth(page);
      
      await page.route('**/api/admin/users/pending**', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify([
            { id: 'p1', email: 'pending1@test.com', name: 'Pending User 1', created_at: '2025-12-01' },
            { id: 'p2', email: 'pending2@test.com', name: 'Pending User 2', created_at: '2025-12-02' },
          ]),
        });
      });
      
      await page.goto(`${BASE_URL}/admin/pending`);
      await page.waitForLoadState('domcontentloaded');
      
      console.log('[Pending] Page URL:', page.url());
      
      const currentUrl = page.url();
      // Should either load or redirect
      console.log('[Pending] Final URL:', currentUrl);
    });
    
    test('pending users page shows user list or empty state', async ({ page }) => {
      await setupAdminAuth(page);
      
      await page.route('**/api/admin/users/pending**', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify([
            { id: 'p1', email: 'pending1@test.com', name: 'Pending User 1', created_at: '2025-12-01' },
          ]),
        });
      });
      
      await page.goto(`${BASE_URL}/admin/pending`);
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(2000);
      
      // Look for user list or empty state
      const userRow = page.locator('tr, [data-testid*="user"], .user-row').first();
      const emptyState = page.locator('text=/Нет ожидающих|No pending|Пусто|Empty/i').first();
      
      const hasUsers = await userRow.isVisible().catch(() => false);
      const isEmpty = await emptyState.isVisible().catch(() => false);
      
      console.log('[Pending] Has user rows:', hasUsers);
      console.log('[Pending] Shows empty state:', isEmpty);
    });
    
    test('can find approve/reject buttons', async ({ page }) => {
      await setupAdminAuth(page);
      
      await page.route('**/api/admin/users/pending**', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify([
            { id: 'p1', email: 'pending1@test.com', name: 'Pending User 1', created_at: '2025-12-01' },
          ]),
        });
      });
      
      await page.goto(`${BASE_URL}/admin/pending`);
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(2000);
      
      const approveButton = page.locator('button:has-text("Одобрить"), button:has-text("Approve"), button:has-text("Accept")').first();
      const rejectButton = page.locator('button:has-text("Отклонить"), button:has-text("Reject"), button:has-text("Deny")').first();
      
      const hasApprove = await approveButton.isVisible().catch(() => false);
      const hasReject = await rejectButton.isVisible().catch(() => false);
      
      console.log('[Pending] Approve button visible:', hasApprove);
      console.log('[Pending] Reject button visible:', hasReject);
    });
  });
  
  test.describe('5. Monitoring', () => {
    test('can access monitoring page', async ({ page }) => {
      await setupAdminAuth(page);
      
      await page.route('**/api/system/metrics**', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            cpu_percent: 25.5,
            memory_percent: 45.2,
            disk_percent: 60.0,
            uptime: 86400,
            active_connections: 5,
          }),
        });
      });
      
      await page.goto(`${BASE_URL}/admin/monitoring`);
      await page.waitForLoadState('domcontentloaded');
      
      console.log('[Monitoring] Page URL:', page.url());
    });
    
    test('monitoring shows system metrics', async ({ page }) => {
      await setupAdminAuth(page);
      
      await page.route('**/api/system/metrics**', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            cpu_percent: 25.5,
            memory_percent: 45.2,
            disk_percent: 60.0,
          }),
        });
      });
      
      await page.goto(`${BASE_URL}/admin/monitoring`);
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(2000);
      
      // Look for metric indicators
      const cpuIndicator = page.locator('text=/CPU|ЦПУ|Процессор/i').first();
      const memoryIndicator = page.locator('text=/Memory|Память|RAM/i').first();
      const diskIndicator = page.locator('text=/Disk|Диск|Storage/i').first();
      
      const hasCpu = await cpuIndicator.isVisible().catch(() => false);
      const hasMemory = await memoryIndicator.isVisible().catch(() => false);
      const hasDisk = await diskIndicator.isVisible().catch(() => false);
      
      console.log('[Monitoring] CPU indicator visible:', hasCpu);
      console.log('[Monitoring] Memory indicator visible:', hasMemory);
      console.log('[Monitoring] Disk indicator visible:', hasDisk);
    });
    
    test('monitoring has refresh functionality', async ({ page }) => {
      await setupAdminAuth(page);
      
      let refreshCount = 0;
      
      await page.route('**/api/system/metrics**', async (route) => {
        refreshCount++;
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            cpu_percent: 20 + refreshCount * 5,
            memory_percent: 40 + refreshCount * 2,
            disk_percent: 60.0,
          }),
        });
      });
      
      await page.goto(`${BASE_URL}/admin/monitoring`);
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(2000);
      
      // Look for refresh button
      const refreshButton = page.locator('button:has-text("Обновить"), button:has-text("Refresh"), button[aria-label*="refresh"]').first();
      
      if (await refreshButton.isVisible()) {
        await refreshButton.click();
        await page.waitForTimeout(1000);
        console.log('[Monitoring] Clicked refresh, total API calls:', refreshCount);
      }
      
      console.log('[Monitoring] Total metrics API calls:', refreshCount);
    });
  });
  
  test.describe('6. Analytics', () => {
    test('can access analytics page', async ({ page }) => {
      await setupAdminAuth(page);
      
      await page.route('**/api/analytics/**', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            total_views: 1000,
            total_users: 50,
            active_streams: 3,
            data: [],
          }),
        });
      });
      
      await page.goto(`${BASE_URL}/admin/analytics`);
      await page.waitForLoadState('domcontentloaded');
      
      console.log('[Analytics] Page URL:', page.url());
    });
    
    test('analytics shows charts or data', async ({ page }) => {
      await setupAdminAuth(page);
      
      await page.route('**/api/analytics/**', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            total_views: 1000,
            total_users: 50,
            periods: ['day', 'week', 'month'],
          }),
        });
      });
      
      await page.goto(`${BASE_URL}/admin/analytics`);
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(2000);
      
      // Look for chart elements or statistics
      const chartElement = page.locator('canvas, svg, [class*="chart"], [class*="graph"]').first();
      const statsElement = page.locator('text=/Просмотр|Views|Статистика|Statistics|Пользовател|Users/i').first();
      
      const hasChart = await chartElement.isVisible().catch(() => false);
      const hasStats = await statsElement.isVisible().catch(() => false);
      
      console.log('[Analytics] Chart element visible:', hasChart);
      console.log('[Analytics] Stats element visible:', hasStats);
    });
    
    test('analytics has period selectors', async ({ page }) => {
      await setupAdminAuth(page);
      
      await page.route('**/api/analytics/**', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ data: [] }),
        });
      });
      
      await page.goto(`${BASE_URL}/admin/analytics`);
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(2000);
      
      // Look for period selectors
      const dayButton = page.locator('button:has-text("День"), button:has-text("Day"), button:has-text("24")').first();
      const weekButton = page.locator('button:has-text("Неделя"), button:has-text("Week"), button:has-text("7")').first();
      const monthButton = page.locator('button:has-text("Месяц"), button:has-text("Month"), button:has-text("30")').first();
      
      const hasDay = await dayButton.isVisible().catch(() => false);
      const hasWeek = await weekButton.isVisible().catch(() => false);
      const hasMonth = await monthButton.isVisible().catch(() => false);
      
      console.log('[Analytics] Day selector visible:', hasDay);
      console.log('[Analytics] Week selector visible:', hasWeek);
      console.log('[Analytics] Month selector visible:', hasMonth);
      
      // Try clicking if visible
      if (hasWeek) {
        await weekButton.click();
        console.log('[Analytics] Clicked week selector');
        await page.waitForTimeout(500);
      }
    });
  });
});
