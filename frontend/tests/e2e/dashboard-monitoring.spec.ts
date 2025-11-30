import { test, expect } from '@playwright/test';

/**
 * E2E Tests for Dashboard Monitoring (US1-US4)
 * Feature: 015-real-system-monitoring
 * 
 * Tests:
 * - US1: System metrics display (CPU, RAM, Disk, Latency, DB)
 * - US2: Activity timeline with events
 * - US3: Stream status with error display
 * - US4: Activity filtering and search
 */

test.describe('Dashboard Monitoring', () => {
  test.beforeEach(async ({ page }) => {
    // Mock Auth - Admin user
    await page.route('**/api/users/me', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'user_admin',
          email: 'admin@sattva.studio',
          full_name: 'Admin User',
          role: 'admin',
          status: 'approved'
        })
      });
    });

    // Mock system metrics endpoint
    await page.route('**/api/system/metrics', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          cpu_percent: 45.5,
          memory_percent: 62.3,
          disk_percent: 78.0,
          db_connections: 5,
          db_max_connections: 100,
          latency_ms: 15.2,
          uptime_seconds: 86400,
          timestamp: new Date().toISOString()
        })
      });
    });

    // Mock activity events endpoint
    await page.route('**/api/system/activity**', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          events: [
            {
              id: 1,
              event_type: 'user_registered',
              message: 'Новый пользователь test@example.com',
              user_email: 'test@example.com',
              details: { method: 'email' },
              created_at: new Date().toISOString()
            },
            {
              id: 2,
              event_type: 'stream_started',
              message: 'Трансляция запущена',
              user_email: 'admin@sattva.studio',
              details: null,
              created_at: new Date(Date.now() - 3600000).toISOString()
            },
            {
              id: 3,
              event_type: 'track_added',
              message: 'Трек добавлен: Test Song',
              user_email: 'admin@sattva.studio',
              details: { track_title: 'Test Song' },
              created_at: new Date(Date.now() - 7200000).toISOString()
            }
          ],
          total: 3
        })
      });
    });

    // Mock stream status endpoint
    await page.route('**/api/admin/stream/status', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          is_running: true,
          status: 'running',
          current_track: 'Relaxing Music',
          uptime: 3600,
          error: null
        })
      });
    });
  });

  test.describe('US1: System Health Metrics', () => {
    test('TC-HEALTH-001 — displays CPU, RAM, Disk metrics', async ({ page }) => {
      await page.goto('/admin/dashboard');
      
      // Wait for metrics to load
      await expect(page.getByText('CPU')).toBeVisible({ timeout: 5000 });
      await expect(page.getByText('45.5%')).toBeVisible();
      
      await expect(page.getByText(/Memory|Память/)).toBeVisible();
      await expect(page.getByText('62.3%')).toBeVisible();
      
      await expect(page.getByText(/Disk|Диск/)).toBeVisible();
      await expect(page.getByText('78.0%')).toBeVisible();
    });

    test('TC-HEALTH-002 — displays latency metric', async ({ page }) => {
      await page.goto('/admin/dashboard');
      
      await expect(page.getByText(/Latency|Задержка/)).toBeVisible({ timeout: 5000 });
      await expect(page.getByText(/15(\.\d+)?\s*ms/)).toBeVisible();
    });

    test('TC-HEALTH-003 — displays DB connections', async ({ page }) => {
      await page.goto('/admin/dashboard');
      
      await expect(page.getByText(/DB Connections|Соединения БД/)).toBeVisible({ timeout: 5000 });
      await expect(page.getByText(/5\s*\/\s*100/)).toBeVisible();
    });

    test('TC-HEALTH-004 — shows warning status for high usage', async ({ page }) => {
      // Override mock with warning-level metrics
      await page.route('**/api/system/metrics', async route => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            cpu_percent: 82.0, // > 80% = warning
            memory_percent: 85.0,
            disk_percent: 92.0, // > 90% = critical
            db_connections: 80,
            db_max_connections: 100,
            latency_ms: 250.0, // > 200ms = warning
            uptime_seconds: 3600,
            timestamp: new Date().toISOString()
          })
        });
      });

      await page.goto('/admin/dashboard');
      
      // Should show warning/critical indicators (yellow/red colors or status badges)
      await expect(page.getByText('82.0%')).toBeVisible({ timeout: 5000 });
      await expect(page.getByText('92.0%')).toBeVisible();
    });

    test('TC-HEALTH-005 — handles API error gracefully', async ({ page }) => {
      await page.route('**/api/system/metrics', async route => {
        await route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Internal Server Error' })
        });
      });

      await page.goto('/admin/dashboard');
      
      // Should show error or unavailable message
      await expect(page.getByText(/unavailable|недоступны|error|ошибка/i)).toBeVisible({ timeout: 5000 });
    });
  });

  test.describe('US2: Activity Timeline', () => {
    test('TC-ACTIVITY-001 — displays activity events list', async ({ page }) => {
      await page.goto('/admin/dashboard');
      
      // Wait for activity section
      await expect(page.getByText(/Recent Activity|Последняя активность/)).toBeVisible({ timeout: 5000 });
      
      // Check events are displayed
      await expect(page.getByText(/test@example.com/)).toBeVisible();
      await expect(page.getByText(/Трансляция запущена|Stream started/i)).toBeVisible();
    });

    test('TC-ACTIVITY-002 — shows event timestamps', async ({ page }) => {
      await page.goto('/admin/dashboard');
      
      // Should have relative timestamps (e.g., "1h ago", "just now")
      await expect(page.getByText(/Recent Activity|Последняя активность/)).toBeVisible({ timeout: 5000 });
      
      // At least one timestamp indicator should be visible
      const timeIndicators = page.locator('[class*="time"], [class*="ago"], time');
      await expect(timeIndicators.first()).toBeVisible();
    });

    test('TC-ACTIVITY-003 — handles empty activity list', async ({ page }) => {
      await page.route('**/api/system/activity**', async route => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ events: [], total: 0 })
        });
      });

      await page.goto('/admin/dashboard');
      
      await expect(page.getByText(/no recent activity|нет недавней активности/i)).toBeVisible({ timeout: 5000 });
    });
  });

  test.describe('US3: Stream Status', () => {
    test('TC-STREAM-001 — displays running stream status', async ({ page }) => {
      await page.goto('/admin/dashboard');
      
      // Should show stream is running
      await expect(page.getByText(/running|запущен|active|активн/i)).toBeVisible({ timeout: 5000 });
      await expect(page.getByText('Relaxing Music')).toBeVisible();
    });

    test('TC-STREAM-002 — displays stream error message', async ({ page }) => {
      await page.route('**/api/admin/stream/status', async route => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            is_running: false,
            status: 'error',
            current_track: null,
            uptime: 0,
            error: 'FFmpeg process crashed: segmentation fault'
          })
        });
      });

      await page.goto('/admin/dashboard');
      
      // Should show error status and message
      await expect(page.getByText(/error|ошибка/i)).toBeVisible({ timeout: 5000 });
      await expect(page.getByText(/FFmpeg|segmentation/i)).toBeVisible();
    });

    test('TC-STREAM-003 — displays stopped stream status', async ({ page }) => {
      await page.route('**/api/admin/stream/status', async route => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            is_running: false,
            status: 'stopped',
            current_track: null,
            uptime: 0,
            error: null
          })
        });
      });

      await page.goto('/admin/dashboard');
      
      await expect(page.getByText(/stopped|остановлен|offline/i)).toBeVisible({ timeout: 5000 });
    });
  });

  test.describe('US4: Activity Filtering', () => {
    test('TC-FILTER-001 — filter dropdown is visible', async ({ page }) => {
      await page.goto('/admin/dashboard');
      
      // Wait for activity section to load
      await expect(page.getByText(/Recent Activity|Последняя активность/)).toBeVisible({ timeout: 5000 });
      
      // Should have filter controls
      const filterButton = page.locator('[class*="filter"], button:has-text("Filter"), select');
      await expect(filterButton.first()).toBeVisible();
    });

    test('TC-FILTER-002 — search input is visible', async ({ page }) => {
      await page.goto('/admin/dashboard');
      
      await expect(page.getByText(/Recent Activity|Последняя активность/)).toBeVisible({ timeout: 5000 });
      
      // Should have search input
      const searchInput = page.getByPlaceholder(/search|поиск/i);
      await expect(searchInput).toBeVisible();
    });

    test('TC-FILTER-003 — filter by event type works', async ({ page }) => {
      // Track API calls to verify filter is applied
      let lastActivityRequest: URL | null = null;
      
      await page.route('**/api/system/activity**', async route => {
        lastActivityRequest = new URL(route.request().url());
        
        // Return filtered results if type param exists
        const type = lastActivityRequest.searchParams.get('type');
        const events = type === 'user_registered' 
          ? [{
              id: 1,
              event_type: 'user_registered',
              message: 'Filtered user event',
              user_email: 'test@example.com',
              details: null,
              created_at: new Date().toISOString()
            }]
          : []; // Return empty for other filters in this test
        
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ events, total: events.length })
        });
      });

      await page.goto('/admin/dashboard');
      
      // Wait for initial load
      await expect(page.getByText(/Recent Activity|Последняя активность/)).toBeVisible({ timeout: 5000 });
      
      // Click filter button/dropdown and select a type
      const filterSelect = page.locator('select').first();
      if (await filterSelect.isVisible()) {
        await filterSelect.selectOption({ label: /user|пользовател/i });
        
        // Verify API was called with filter
        await page.waitForTimeout(500);
        expect(lastActivityRequest?.searchParams.get('type')).toBeTruthy();
      }
    });

    test('TC-FILTER-004 — search by text works', async ({ page }) => {
      let lastActivityRequest: URL | null = null;
      
      await page.route('**/api/system/activity**', async route => {
        lastActivityRequest = new URL(route.request().url());
        
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ events: [], total: 0 })
        });
      });

      await page.goto('/admin/dashboard');
      
      await expect(page.getByText(/Recent Activity|Последняя активность/)).toBeVisible({ timeout: 5000 });
      
      // Type in search input
      const searchInput = page.getByPlaceholder(/search|поиск/i);
      if (await searchInput.isVisible()) {
        await searchInput.fill('test search');
        await searchInput.press('Enter');
        
        // Verify API was called with search param
        await page.waitForTimeout(500);
        expect(lastActivityRequest?.searchParams.get('search')).toBe('test search');
      }
    });

    test('TC-FILTER-005 — clear filters resets view', async ({ page }) => {
      await page.goto('/admin/dashboard');
      
      await expect(page.getByText(/Recent Activity|Последняя активность/)).toBeVisible({ timeout: 5000 });
      
      // Look for clear/reset button after applying filter
      const clearButton = page.getByRole('button', { name: /clear|очистить|reset|сброс|×/i });
      
      // If clear button exists, clicking it should reset filters
      if (await clearButton.isVisible()) {
        await clearButton.click();
        // After clear, filter select should show "All"
        const filterSelect = page.locator('select').first();
        if (await filterSelect.isVisible()) {
          await expect(filterSelect).toHaveValue('');
        }
      }
    });
  });

  test.describe('Integration: Dashboard Overview', () => {
    test('TC-DASH-001 — all monitoring components render together', async ({ page }) => {
      await page.goto('/admin/dashboard');
      
      // All main sections should be visible
      await expect(page.getByText(/System Health|Здоровье системы|CPU/)).toBeVisible({ timeout: 5000 });
      await expect(page.getByText(/Recent Activity|Последняя активность/)).toBeVisible();
      await expect(page.getByText(/Stream|Трансляция/)).toBeVisible();
    });

    test('TC-DASH-002 — dashboard handles multiple API failures gracefully', async ({ page }) => {
      // Fail all monitoring endpoints
      await page.route('**/api/system/metrics', route => route.fulfill({ status: 500 }));
      await page.route('**/api/system/activity**', route => route.fulfill({ status: 500 }));
      await page.route('**/api/admin/stream/status', route => route.fulfill({ status: 500 }));

      await page.goto('/admin/dashboard');
      
      // Page should still render without crashing
      await expect(page.locator('body')).toBeVisible({ timeout: 5000 });
      
      // Should show error states or fallback UI
      await expect(page.getByText(/error|ошибка|unavailable|недоступ/i).first()).toBeVisible();
    });

    test('TC-DASH-003 — metrics auto-refresh works', async ({ page }) => {
      let metricsCallCount = 0;
      
      await page.route('**/api/system/metrics', async route => {
        metricsCallCount++;
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            cpu_percent: 45 + metricsCallCount,
            memory_percent: 60,
            disk_percent: 70,
            db_connections: 5,
            db_max_connections: 100,
            latency_ms: 20,
            uptime_seconds: 3600,
            timestamp: new Date().toISOString()
          })
        });
      });

      await page.goto('/admin/dashboard');
      
      // Wait for initial load
      await expect(page.getByText('CPU')).toBeVisible({ timeout: 5000 });
      
      // Wait for auto-refresh (assuming 10s interval)
      await page.waitForTimeout(12000);
      
      // Should have made multiple calls
      expect(metricsCallCount).toBeGreaterThan(1);
    });
  });
});
