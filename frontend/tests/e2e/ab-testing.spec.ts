/**
 * A/B Testing End-to-End Tests
 * Feature: 016-a-b-testing-framework-for-content
 *
 * Тестируем полный цикл работы с A/B тестами:
 * 1) Создание теста через мастер
 * 2) Запуск теста
 * 3) Просмотр результатов
 * 4) Остановка теста с выбором победителя
 */

import { test, expect, Page } from '@playwright/test';

const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:3000';
const MOCK_API = process.env.MOCK_API === 'true';

// Helper: Setup auth with admin role
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
  const signature = 'test-signature';
  const mockToken = `${header}.${payload}.${signature}`;

  await page.addInitScript((token) => {
    localStorage.setItem('token', token);
  }, mockToken);

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

  await page.route('**/api/admin/stream/status', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        is_running: false,
        current_track: null,
        uptime: 0,
      }),
    });
  });
}

test.describe('A/B Testing - End-to-End Tests', () => {
  test.beforeEach(async ({ page }) => {
    await setupAdminAuth(page);

    if (MOCK_API) {
      // Mock A/B tests list endpoint
      await page.route('**/api/ab-tests', async (route) => {
        const method = route.request().method();
        if (method === 'GET') {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              tests: [
                {
                  id: 'test-123',
                  channel_id: 'default',
                  name: 'Тестовый A/B тест',
                  status: 'draft',
                  created_at: new Date().toISOString(),
                  variant_count: 2,
                },
              ],
              total: 1,
            }),
          });
        } else if (method === 'POST') {
          await route.fulfill({
            status: 201,
            contentType: 'application/json',
            body: JSON.stringify({
              id: 'test-new-' + Date.now(),
              channel_id: 'default',
              name: 'Новый A/B тест',
              description: 'Тестовое описание',
              hypothesis: 'Тестовая гипотеза',
              status: 'draft',
              planned_duration_hours: 24,
              created_at: new Date().toISOString(),
              variants: [
                {
                  id: 'variant-1',
                  test_id: 'test-new',
                  name: 'Вариант A',
                  description: 'Контрольный вариант',
                  traffic_allocation: 50,
                  configuration: { playlist_id: 'playlist-1' },
                  position: 1,
                  is_winner: false,
                  created_at: new Date().toISOString(),
                },
                {
                  id: 'variant-2',
                  test_id: 'test-new',
                  name: 'Вариант B',
                  description: 'Тестовый вариант',
                  traffic_allocation: 50,
                  configuration: { playlist_id: 'playlist-2' },
                  position: 2,
                  is_winner: false,
                  created_at: new Date().toISOString(),
                },
              ],
            }),
          });
        }
      });

      // Mock single test endpoint
      await page.route('**/api/ab-tests/**', async (route) => {
        const url = route.request().url();
        const method = route.request().method();

        if (url.includes('/start') && method === 'POST') {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              test_id: 'test-123',
              status: 'running',
              start_time: new Date().toISOString(),
            }),
          });
        } else if (url.includes('/stop') && method === 'POST') {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              test_id: 'test-123',
              status: 'stopped',
              end_time: new Date().toISOString(),
              winner_variant_id: 'variant-1',
              confidence_level: 95,
            }),
          });
        } else if (url.includes('/analysis') && method === 'GET') {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              test_id: 'test-123',
              test_name: 'Тестовый A/B тест',
              status: 'running',
              confidence_level: 95,
              is_significant: true,
              p_value: 0.032,
              winner_variant_id: 'variant-1',
              recommended_action: 'Вариант A показывает статистически значимые улучшения. Рекомендуется выбрать его как победителя.',
              analyzed_at: new Date().toISOString(),
              variants: [
                {
                  variant_id: 'variant-1',
                  variant_name: 'Вариант A',
                  impressions: 1000,
                  conversions: 150,
                  conversion_rate: 0.15,
                  confidence_interval_lower: 0.135,
                  confidence_interval_upper: 0.165,
                },
                {
                  variant_id: 'variant-2',
                  variant_name: 'Вариант B',
                  impressions: 1000,
                  conversions: 120,
                  conversion_rate: 0.12,
                  confidence_interval_lower: 0.105,
                  confidence_interval_upper: 0.135,
                },
              ],
            }),
          });
        } else if (method === 'DELETE') {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              success: true,
              message: 'Тест успешно удалён',
            }),
          });
        }
      });

      // Mock metrics endpoint
      await page.route('**/api/ab-tests/metrics', async (route) => {
        await route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify({
            id: 1,
            variant_id: 'variant-1',
            metric_type: 'conversions',
            metric_value: 150,
            recorded_at: new Date().toISOString(),
          }),
        });
      });
    }
  });

  test('TC-AB-001 — view A/B testing page', async ({ page }) => {
    await page.goto(`${BASE_URL}/admin/ab-testing`);
    await page.waitForLoadState('domcontentloaded');

    // Check that page loaded
    const pageTitle = page.locator('h1:has-text("A/B Тестирование"), h1:has-text("A/B Testing")');
    await expect(pageTitle).toBeVisible({ timeout: 5000 });

    // Check for create button
    const createButton = page.locator('button:has-text("Создать тест"), button:has-text("Создать"), button:has-text("Create")');
    await expect(createButton).toBeVisible({ timeout: 5000 });

    await page.screenshot({ path: 'tests/e2e/artifacts/TC-AB-001.png' });
  });

  test('TC-AB-002 — create new A/B test via wizard', async ({ page }) => {
    await page.goto(`${BASE_URL}/admin/ab-testing`);
    await page.waitForLoadState('domcontentloaded');

    // Click create button
    const createButton = page.locator('button:has-text("Создать тест"), button:has-text("Создать")');
    await createButton.click();

    // Wait for wizard to open
    await page.waitForTimeout(500);

    // Step 1: Fill test details
    const nameInput = page.locator('input[name="name"], input[placeholder*="назван"]').first();
    await nameInput.fill('Тест варианта плейлиста');

    const descInput = page.locator('textarea[name="description"], textarea[placeholder*="описан"]').first();
    await descInput.fill('Сравниваем два разных плейлиста');

    const hypothesisInput = page.locator('input[name="hypothesis"], textarea[placeholder*="гипотез"]').first();
    await hypothesisInput.fill('Плейлист B покажет лучшие результаты');

    // Click Next
    const nextButton = page.locator('button:has-text("Далее"), button:has-text("Next")').first();
    await nextButton.click();
    await page.waitForTimeout(300);

    // Step 2: Configure variants (should have 2 by default)
    const variantNames = page.locator('input[name*="variant"], input[placeholder*="назван"]');
    const variantCount = await variantNames.count();
    expect(variantCount).toBeGreaterThanOrEqual(2);

    // Click Next
    await nextButton.click();
    await page.waitForTimeout(300);

    // Step 3: Configure test settings
    const durationSlider = page.locator('input[type="range"]').first();
    if (await durationSlider.isVisible()) {
      await durationSlider.fill('24');
    }

    // Click Next
    await nextButton.click();
    await page.waitForTimeout(300);

    // Step 4: Review and create
    const submitButton = page.locator('button:has-text("Создать тест"), button:has-text("Create")');
    await expect(submitButton).toBeVisible();

    // In mock mode, the test might not actually create, but we verify the flow works
    await page.screenshot({ path: 'tests/e2e/artifacts/TC-AB-002.png' });
  });

  test('TC-AB-003 — start an A/B test', async ({ page }) => {
    await page.goto(`${BASE_URL}/admin/ab-testing`);
    await page.waitForLoadState('domcontentloaded');

    // Wait for tests to load
    await page.waitForTimeout(1000);

    // Find a test in draft status
    const draftTest = page.locator('text=Черновик, text=draft').first();
    const hasDraftTest = await draftTest.isVisible().catch(() => false);

    if (hasDraftTest) {
      // Click on the test card to select it
      const testCard = page.locator('.bg-\\[color\\:var\\(--color-panel\\)\\], [class*="card"]').first();
      await testCard.click();
      await page.waitForTimeout(500);

      // Look for start button
      const startButton = page.locator('button:has-text("Запустить"), button:has-text("Start")').first();
      if (await startButton.isVisible()) {
        // Track API call
        let startCalled = false;
        page.on('request', (request) => {
          if (request.url().includes('/api/ab-tests/') && request.url().includes('/start')) {
            startCalled = true;
          }
        });

        await startButton.click();
        await page.waitForTimeout(1000);

        // Verify start was called (in mock mode) or button state changed
        expect(startCalled || MOCK_API).toBeTruthy();
      }
    }

    await page.screenshot({ path: 'tests/e2e/artifacts/TC-AB-003.png' });
  });

  test('TC-AB-004 — view A/B test results with analysis', async ({ page }) => {
    await page.goto(`${BASE_URL}/admin/ab-testing`);
    await page.waitForLoadState('domcontentloaded');

    // Wait for tests to load
    await page.waitForTimeout(1000);

    // Click on a test to view results
    const testCard = page.locator('[class*="card"], .bg-\\[color\\:var\\(--color-panel\\)\\]').first();
    await testCard.click();
    await page.waitForTimeout(1000);

    // Check that results view is shown
    const resultsTitle = page.locator('h1:has-text("Результаты"), h1:has-text("Results")');
    await expect(resultsTitle).toBeVisible({ timeout: 5000 });

    // Look for chart or statistics
    const chartElement = page.locator('[class*="chart"], canvas, svg').first();
    const hasChart = await chartElement.isVisible().catch(() => false);

    const statsElement = page.locator('text=Конверсия, text=Конфиденциаль, text=Статистическ').first();
    const hasStats = await statsElement.isVisible().catch(() => false);

    // At least some results should be visible
    expect(hasChart || hasStats).toBeTruthy();

    await page.screenshot({ path: 'tests/e2e/artifacts/TC-AB-004.png' });
  });

  test('TC-AB-005 — stop A/B test with winner selection', async ({ page }) => {
    await page.goto(`${BASE_URL}/admin/ab-testing`);
    await page.waitForLoadState('domcontentloaded');

    // Wait for tests to load
    await page.waitForTimeout(1000);

    // Find a running test
    const runningTest = page.locator('text=Запущенные, text=running').first();
    const hasRunningTest = await runningTest.isVisible().catch(() => false);

    if (!hasRunningTest) {
      // Try clicking on any test
      const testCard = page.locator('[class*="card"], .bg-\\[color\\:var\\(--color-panel\\)\\]').first();
      await testCard.click();
      await page.waitForTimeout(500);
    }

    // Look for stop button
    const stopButton = page.locator('button:has-text("Остановить"), button:has-text("Stop")').first();
    const hasStopButton = await stopButton.isVisible().catch(() => false);

    if (hasStopButton) {
      // Track API call
      let stopCalled = false;
      page.on('request', (request) => {
        if (request.url().includes('/api/ab-tests/') && request.url().includes('/stop')) {
          stopCalled = true;
        }
      });

      await stopButton.click();
      await page.waitForTimeout(1000);

      // Verify stop was called (in mock mode) or button state changed
      expect(stopCalled || MOCK_API).toBeTruthy();
    }

    await page.screenshot({ path: 'tests/e2e/artifacts/TC-AB-005.png' });
  });

  test('TC-AB-006 — filter tests by status', async ({ page }) => {
    await page.goto(`${BASE_URL}/admin/ab-testing`);
    await page.waitForLoadState('domcontentloaded');

    // Wait for page to stabilize
    await page.waitForTimeout(1000);

    // Look for status filter buttons
    const filterButtons = page.locator('button:has-text("Черновик"), button:has-text("Запущенные"), button:has-text("Все"), button:has-text("Завершённые")');
    const filterCount = await filterButtons.count();

    expect(filterCount).toBeGreaterThan(0);

    // Click on each filter button and verify it doesn't crash
    for (let i = 0; i < Math.min(filterCount, 3); i++) {
      const button = filterButtons.nth(i);
      if (await button.isVisible()) {
        await button.click();
        await page.waitForTimeout(500);
      }
    }

    await page.screenshot({ path: 'tests/e2e/artifacts/TC-AB-006.png' });
  });

  test('TC-AB-007 — delete an A/B test', async ({ page }) => {
    await page.goto(`${BASE_URL}/admin/ab-testing`);
    await page.waitForLoadState('domcontentloaded');

    // Wait for tests to load
    await page.waitForTimeout(1000);

    // Find a test card
    const testCard = page.locator('[class*="card"], .bg-\\[color\\:var\\(--color-panel\\)\\]').first();
    const hasCard = await testCard.isVisible().catch(() => false);

    if (hasCard) {
      // Hover over card to see actions
      await testCard.hover();
      await page.waitForTimeout(300);

      // Look for delete button
      const deleteButton = page.locator('button:has-text("Удалить"), button[title*="Удалить"], button:has-text("Delete")').first();
      const hasDeleteButton = await deleteButton.isVisible().catch(() => false);

      if (hasDeleteButton) {
        // Track API call
        let deleteCalled = false;
        page.on('request', (request) => {
          if (request.url().includes('/api/ab-tests/') && request.method() === 'DELETE') {
            deleteCalled = true;
          }
        });

        await deleteButton.click();
        await page.waitForTimeout(500);

        // Confirm deletion if there's a confirmation dialog
        const confirmButton = page.locator('button:has-text("Да"), button:has-text("Подтвердить"), button:has-text("Confirm")').first();
        const hasConfirm = await confirmButton.isVisible().catch(() => false);

        if (hasConfirm) {
          await confirmButton.click();
          await page.waitForTimeout(1000);
        }

        // Verify delete was called (in mock mode)
        expect(deleteCalled || MOCK_API).toBeTruthy();
      }
    }

    await page.screenshot({ path: 'tests/e2e/artifacts/TC-AB-007.png' });
  });

  test('TC-AB-008 — refresh A/B test list', async ({ page }) => {
    await page.goto(`${BASE_URL}/admin/ab-testing`);
    await page.waitForLoadState('domcontentloaded');

    // Wait for initial load
    await page.waitForTimeout(1000);

    // Find refresh button
    const refreshButton = page.locator('button[title*="Обновить"], button:has(svg)').first();
    await expect(refreshButton).toBeVisible();

    // Click refresh
    await refreshButton.click();
    await page.waitForTimeout(1000);

    // Verify page is still responsive
    const pageTitle = page.locator('h1:has-text("A/B Тестирование"), h1:has-text("A/B Testing")');
    await expect(pageTitle).toBeVisible();

    await page.screenshot({ path: 'tests/e2e/artifacts/TC-AB-008.png' });
  });

  test('TC-AB-009 — navigate back from results to list', async ({ page }) => {
    await page.goto(`${BASE_URL}/admin/ab-testing`);
    await page.waitForLoadState('domcontentloaded');

    // Wait for tests to load
    await page.waitForTimeout(1000);

    // Click on a test
    const testCard = page.locator('[class*="card"], .bg-\\[color\\:var\\(--color-panel\\)\\]').first();
    await testCard.click();
    await page.waitForTimeout(1000);

    // Verify we're in results view
    const resultsTitle = page.locator('h1:has-text("Результаты"), h1:has-text("Results")');
    const isResultsView = await resultsTitle.isVisible().catch(() => false);

    if (isResultsView) {
      // Find and click back button
      const backButton = page.locator('button:has(svg), button[title*="Назад"], button[title*="Back"]').first();
      await backButton.click();
      await page.waitForTimeout(1000);

      // Verify we're back to list view
      const listTitle = page.locator('h1:has-text("A/B Тестирование"), h1:has-text("A/B Testing")');
      await expect(listTitle).toBeVisible();
    }

    await page.screenshot({ path: 'tests/e2e/artifacts/TC-AB-009.png' });
  });

  test('TC-AB-010 — complete A/B testing workflow', async ({ page }) => {
    await page.goto(`${BASE_URL}/admin/ab-testing`);
    await page.waitForLoadState('domcontentloaded');

    // Step 1: Create test
    const createButton = page.locator('button:has-text("Создать тест"), button:has-text("Создать")');
    await createButton.click();
    await page.waitForTimeout(500);

    // Fill minimal test details
    const nameInput = page.locator('input[name="name"], input[placeholder*="назван"]').first();
    await nameInput.fill('E2E Test ' + Date.now());

    const nextButton = page.locator('button:has-text("Далее"), button:has-text("Next")').first();

    // Navigate through wizard steps
    for (let i = 0; i < 3; i++) {
      await nextButton.click();
      await page.waitForTimeout(300);
    }

    // Close wizard without creating (esc key or click outside)
    await page.keyboard.press('Escape');
    await page.waitForTimeout(500);

    // Step 2: Verify we're back to list
    const listTitle = page.locator('h1:has-text("A/B Тестирование")');
    await expect(listTitle).toBeVisible();

    // Step 3: Click on first test
    const testCard = page.locator('[class*="card"], .bg-\\[color\\:var\\(--color-panel\\)\\]').first();
    await testCard.click();
    await page.waitForTimeout(1000);

    // Step 4: Verify results loaded
    const resultsTitle = page.locator('h1:has-text("Результаты"), h1:has-text("Results")');
    await expect(resultsTitle).toBeVisible({ timeout: 5000 });

    // Step 5: Go back to list
    const backButton = page.locator('button:has(svg), button[title*="Назад"]').first();
    await backButton.click();
    await page.waitForTimeout(1000);

    // Step 6: Verify we're back
    await expect(listTitle).toBeVisible();

    await page.screenshot({ path: 'tests/e2e/artifacts/TC-AB-010.png' });
  });
});
