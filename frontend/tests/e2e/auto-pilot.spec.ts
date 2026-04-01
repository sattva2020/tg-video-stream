/**
 * E2E тесты для функции авто-пилота расписания.
 *
 * Покрывает полный пользовательский сценарий:
 * - Навигация на страницу расписания
 * - Открытие панели авто-пилота
 * - Выбор диапазона дат
 * - Генерация расписания
 * - Проверка созданных слотов
 * - Проверка разрешения конфликтов
 */

import { test, expect, Page } from '@playwright/test';

// ==================== Test Fixtures ====================

const TEST_USER = {
  email: 'admin@test.com',
  password: 'testpassword123',
};

const TEST_CHANNEL = 'test-channel';

// ==================== Helper Functions ====================

async function login(page: Page) {
  await page.goto('/login');
  await page.fill('[data-testid="email-input"]', TEST_USER.email);
  await page.fill('[data-testid="password-input"]', TEST_USER.password);
  await page.click('[data-testid="login-button"]');
  await page.waitForURL('/dashboard');
}

async function navigateToSchedule(page: Page) {
  await page.click('[data-testid="nav-schedule"]');
  await page.waitForURL('/schedule');
  await expect(page.locator('h1')).toContainText(/расписание|schedule/i);
}

async function mockScheduleAPI(page: Page) {
  // Mock schedule slots endpoint
  await page.route('**/api/schedule/slots**', async route => {
    await route.fulfill({
      json: [],
    });
  });

  // Mock auto-pilot generate endpoint
  await page.route('**/api/schedule-ai/auto-pilot/generate', async route => {
    await route.fulfill({
      json: {
        task_id: 'test-task-123',
        status: 'completed',
        slots_created: 10,
        gaps_filled: 5,
        conflicts_resolved: 2,
        message: 'Расписание успешно сгенерировано',
      },
    });
  });

  // Mock auto-pilot preview endpoint
  await page.route('**/api/schedule-ai/auto-pilot/preview', async route => {
    await route.fulfill({
      json: {
        slots_created: 10,
        gaps_filled: 5,
        conflicts_resolved: 2,
        warnings: [],
      },
    });
  });

  // Mock recommendations endpoint
  await page.route('**/api/schedule-ai/recommendations**', async route => {
    await route.fulfill({
      json: {
        recommendations: [
          {
            id: 'rec-1',
            date: '2025-01-23',
            start_time: '10:00',
            end_time: '12:00',
            playlist_id: 'playlist-1',
            playlist_name: 'Morning Playlist',
            reason: 'Высокая вовлеченность в это время',
            confidence: 0.9,
            type: 'PEAK_HOURS',
          },
        ],
      },
    });
  });

  // Mock peak hours endpoint
  await page.route('**/api/schedule-ai/peak-hours**', async route => {
    await route.fulfill({
      json: {
        channel_id: TEST_CHANNEL,
        period: '30d',
        peak_hours: [
          {
            day_of_week: 1,
            hour: 10,
            avg_listeners: 150,
            peak_listeners: 200,
          },
        ],
      },
    });
  });
}

// ==================== Navigation Tests ====================

test.describe('Auto-Pilot Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await mockScheduleAPI(page);
  });

  test('auto-pilot button is visible on schedule page', async ({ page }) => {
    await navigateToSchedule(page);

    const autoPilotButton = page.locator('button:has-text("AI")').or(
      page.locator('[data-testid="auto-pilot-button"]')
    );

    await expect(autoPilotButton).toBeVisible();
  });

  test('opens auto-pilot panel when button clicked', async ({ page }) => {
    await navigateToSchedule(page);

    const autoPilotButton = page.locator('button:has-text("AI")').or(
      page.locator('[data-testid="auto-pilot-button"]')
    );

    await autoPilotButton.click();

    // Check that panel is visible
    await expect(page.locator('[data-testid="auto-pilot-panel"]')).toBeVisible();
  });
});

// ==================== Date Range Selection Tests ====================

test.describe('Auto-Pilot Date Range Selection', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await mockScheduleAPI(page);
    await navigateToSchedule(page);

    // Open auto-pilot panel
    const autoPilotButton = page.locator('button:has-text("AI")').or(
      page.locator('[data-testid="auto-pilot-button"]')
    );
    await autoPilotButton.click();
  });

  test('shows date range selector', async ({ page }) => {
    await expect(page.locator('[data-testid="date-range-selector"]')).toBeVisible();
  });

  test('has preset range options', async ({ page }) => {
    // Check for week preset
    await expect(page.locator('button:has-text("Неделя")').or(
      page.locator('[data-testid="preset-week"]')
    )).toBeVisible();

    // Check for month preset
    await expect(page.locator('button:has-text("Месяц")').or(
      page.locator('[data-testid="preset-month"]')
    )).toBeVisible();
  });

  test('can select custom date range', async ({ page }) => {
    const customButton = page.locator('button:has-text("Custom")').or(
      page.locator('[data-testid="preset-custom"]')
    );

    await customButton.click();

    // Date inputs should be visible
    await expect(page.locator('input[type="date"]').first()).toBeVisible();
  });
});

// ==================== AI Settings Tests ====================

test.describe('Auto-Pilot AI Settings', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await mockScheduleAPI(page);
    await navigateToSchedule(page);

    // Open auto-pilot panel
    const autoPilotButton = page.locator('button:has-text("AI")').or(
      page.locator('[data-testid="auto-pilot-button"]')
    );
    await autoPilotButton.click();
  });

  test('shows AI recommendations toggle', async ({ page }) => {
    const toggle = page.locator('[data-testid="use-ai-toggle"]').or(
      page.locator('switch:has-text("AI рекомендации")')
    );

    await expect(toggle).toBeVisible();
  });

  test('can toggle AI recommendations', async ({ page }) => {
    const toggle = page.locator('[data-testid="use-ai-toggle"]').or(
      page.locator('switch:has-text("AI рекомендации")')
    );

    // Toggle on
    await toggle.click();

    // Toggle off
    await toggle.click();
  });

  test('shows max daily hours slider', async ({ page }) => {
    const slider = page.locator('[data-testid="max-hours-slider"]').or(
      page.locator('input[type="range"]')
    );

    await expect(slider).toBeVisible();
  });

  test('shows conflict resolution toggle', async ({ page }) => {
    const toggle = page.locator('[data-testid="resolve-conflicts-toggle"]').or(
      page.locator('switch:has-text("Разрешение конфликтов")')
    );

    await expect(toggle).toBeVisible();
  });
});

// ==================== Schedule Generation Tests ====================

test.describe('Auto-Pilot Schedule Generation', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await mockScheduleAPI(page);
    await navigateToSchedule(page);

    // Open auto-pilot panel
    const autoPilotButton = page.locator('button:has-text("AI")').or(
      page.locator('[data-testid="auto-pilot-button"]')
    );
    await autoPilotButton.click();
  });

  test('shows generate button', async ({ page }) => {
    const generateButton = page.locator('button:has-text("Генерировать")').or(
      page.locator('[data-testid="generate-schedule-button"]')
    );

    await expect(generateButton).toBeVisible();
  });

  test('generates schedule when button clicked', async ({ page }) => {
    const generateButton = page.locator('button:has-text("Генерировать")').or(
      page.locator('[data-testid="generate-schedule-button"]')
    );

    await generateButton.click();

    // Check for success message
    await expect(page.locator('text=Расписание успешно сгенерировано')).toBeVisible();
  });

  test('shows loading state during generation', async ({ page }) => {
    // Slow response to show loading state
    await page.route('**/api/schedule-ai/auto-pilot/generate', async route => {
      await new Promise(resolve => setTimeout(resolve, 2000));
      await route.fulfill({
        json: {
          task_id: 'test-task-123',
          status: 'completed',
          slots_created: 10,
          gaps_filled: 5,
          conflicts_resolved: 2,
          message: 'Расписание успешно сгенерировано',
        },
      });
    });

    const generateButton = page.locator('button:has-text("Генерировать")').or(
      page.locator('[data-testid="generate-schedule-button"]')
    );

    await generateButton.click();

    // Check for loading indicator
    await expect(page.locator('[data-testid="loading-spinner"]').or(
      page.locator('.spinner')
    )).toBeVisible();
  });

  test('displays generation results', async ({ page }) => {
    const generateButton = page.locator('button:has-text("Генерировать")').or(
      page.locator('[data-testid="generate-schedule-button"]')
    );

    await generateButton.click();

    // Check for results display
    await expect(page.locator('[data-testid="generation-results"]')).toBeVisible();

    // Check for slots created count
    await expect(page.locator('text=10').or(
      page.locator('[data-testid="slots-created-count"]')
    )).toBeVisible();

    // Check for gaps filled count
    await expect(page.locator('text=5').or(
      page.locator('[data-testid="gaps-filled-count"]')
    )).toBeVisible();

    // Check for conflicts resolved count
    await expect(page.locator('text=2').or(
      page.locator('[data-testid="conflicts-resolved-count"]')
    )).toBeVisible();
  });
});

// ==================== Preview Tests ====================

test.describe('Auto-Pilot Preview', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await mockScheduleAPI(page);
    await navigateToSchedule(page);

    // Open auto-pilot panel
    const autoPilotButton = page.locator('button:has-text("AI")').or(
      page.locator('[data-testid="auto-pilot-button"]')
    );
    await autoPilotButton.click();
  });

  test('shows preview button', async ({ page }) => {
    const previewButton = page.locator('button:has-text("Предпросмотр")').or(
      page.locator('[data-testid="preview-button"]')
    );

    await expect(previewButton).toBeVisible();
  });

  test('shows preview results when clicked', async ({ page }) => {
    const previewButton = page.locator('button:has-text("Предпросмотр")').or(
      page.locator('[data-testid="preview-button"]')
    );

    await previewButton.click();

    // Check for preview results
    await expect(page.locator('[data-testid="preview-results"]')).toBeVisible();
  });

  test('preview does not create slots', async ({ page }) => {
    let createSlotCalled = false;

    // Track if create slot endpoint was called
    await page.route('**/api/schedule/slots**', async route => {
      createSlotCalled = true;
      await route.continue();
    });

    const previewButton = page.locator('button:has-text("Предпросмотр")').or(
      page.locator('[data-testid="preview-button"]')
    );

    await previewButton.click();

    // Wait for preview to complete
    await page.waitForTimeout(1000);

    // Verify that create slot endpoint was not called
    expect(createSlotCalled).toBe(false);
  });
});

// ==================== Error Handling Tests ====================

test.describe('Auto-Pilot Error Handling', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await navigateToSchedule(page);

    // Open auto-pilot panel
    const autoPilotButton = page.locator('button:has-text("AI")').or(
      page.locator('[data-testid="auto-pilot-button"]')
    );
    await autoPilotButton.click();
  });

  test('handles API error gracefully', async ({ page }) => {
    // Mock error response
    await page.route('**/api/schedule-ai/auto-pilot/generate', async route => {
      await route.fulfill({
        status: 500,
        json: {
          detail: 'Internal server error',
        },
      });
    });

    const generateButton = page.locator('button:has-text("Генерировать")').or(
      page.locator('[data-testid="generate-schedule-button"]')
    );

    await generateButton.click();

    // Check for error message
    await expect(page.locator('text=Ошибка').or(
      page.locator('[data-testid="error-message"]')
    )).toBeVisible();
  });

  test('handles network error gracefully', async ({ page }) => {
    // Mock network error
    await page.route('**/api/schedule-ai/auto-pilot/generate', async route => {
      await route.abort('failed');
    });

    const generateButton = page.locator('button:has-text("Генерировать")').or(
      page.locator('[data-testid="generate-schedule-button"]')
    );

    await generateButton.click();

    // Check for error message
    await expect(page.locator('text=Ошибка сети').or(
      page.locator('[data-testid="error-message"]')
    )).toBeVisible();
  });

  test('handles unauthorized access', async ({ page }) => {
    // Mock unauthorized response
    await page.route('**/api/schedule-ai/auto-pilot/generate', async route => {
      await route.fulfill({
        status: 403,
        json: {
          detail: 'Not enough permissions',
        },
      });
    });

    const generateButton = page.locator('button:has-text("Генерировать")').or(
      page.locator('[data-testid="generate-schedule-button"]')
    );

    await generateButton.click();

    // Check for authorization error message
    await expect(page.locator('text=Недостаточно прав').or(
      page.locator('[data-testid="error-message"]')
    )).toBeVisible();
  });
});

// ==================== Integration Tests ====================

test.describe('Auto-Pilot End-to-End Flow', () => {
  test('complete auto-pilot workflow', async ({ page }) => {
    await login(page);
    await mockScheduleAPI(page);
    await navigateToSchedule(page);

    // Step 1: Navigate to schedule page
    await expect(page).toHaveURL(/\/schedule/);

    // Step 2: Click auto-pilot button
    const autoPilotButton = page.locator('button:has-text("AI")').or(
      page.locator('[data-testid="auto-pilot-button"]')
    );
    await autoPilotButton.click();

    // Step 3: Select date range (week preset)
    const weekPreset = page.locator('button:has-text("Неделя")').or(
      page.locator('[data-testid="preset-week"]')
    );
    await weekPreset.click();

    // Step 4: Configure AI settings
    const aiToggle = page.locator('[data-testid="use-ai-toggle"]').or(
      page.locator('switch:has-text("AI рекомендации")')
    );
    await aiToggle.click();

    // Step 5: Preview schedule
    const previewButton = page.locator('button:has-text("Предпросмотр")').or(
      page.locator('[data-testid="preview-button"]')
    );
    await previewButton.click();

    // Check preview results
    await expect(page.locator('[data-testid="preview-results"]')).toBeVisible();

    // Step 6: Generate schedule
    const generateButton = page.locator('button:has-text("Генерировать")').or(
      page.locator('[data-testid="generate-schedule-button"]')
    );
    await generateButton.click();

    // Step 7: Verify success
    await expect(page.locator('text=Расписание успешно сгенерировано')).toBeVisible();

    // Step 8: Check results
    await expect(page.locator('[data-testid="generation-results"]')).toBeVisible();
    await expect(page.locator('[data-testid="slots-created-count"]')).toContainText('10');
    await expect(page.locator('[data-testid="gaps-filled-count"]')).toContainText('5');
    await expect(page.locator('[data-testid="conflicts-resolved-count"]')).toContainText('2');

    // Step 9: Close panel
    const closeButton = page.locator('button:has-text("✕")').or(
      page.locator('[data-testid="close-panel-button"]')
    );
    await closeButton.click();

    // Verify panel is closed
    await expect(page.locator('[data-testid="auto-pilot-panel"]')).not.toBeVisible();
  });

  test('generates schedule with conflict resolution', async ({ page }) => {
    await login(page);

    // Mock schedule with existing conflicts
    await page.route('**/api/schedule/slots**', async route => {
      await route.fulfill({
        json: [
          {
            id: 'slot-1',
            date: '2025-01-23',
            start_time: '10:00',
            end_time: '12:00',
            playlist_id: 'playlist-1',
            priority: 5,
          },
          {
            id: 'slot-2',
            date: '2025-01-23',
            start_time: '11:00',
            end_time: '13:00',
            playlist_id: 'playlist-2',
            priority: 3,
          },
        ],
      });
    });

    // Mock conflict detection
    await page.route('**/api/schedule-ai/detect-conflicts', async route => {
      await route.fulfill({
        json: {
          conflicts: [
            {
              date: '2025-01-23',
              conflicting_slots: [
                { id: 'slot-1', start_time: '10:00', end_time: '12:00' },
                { id: 'slot-2', start_time: '11:00', end_time: '13:00' },
              ],
            },
          ],
        },
      });
    });

    // Mock conflict resolution
    await page.route('**/api/schedule-ai/resolve-conflicts', async route => {
      await route.fulfill({
        json: {
          resolutions_applied: 1,
          slots_removed: 1,
          slots_modified: 0,
          remaining_conflicts: 0,
        },
      });
    });

    await mockScheduleAPI(page);
    await navigateToSchedule(page);

    // Open auto-pilot panel
    const autoPilotButton = page.locator('button:has-text("AI")').or(
      page.locator('[data-testid="auto-pilot-button"]')
    );
    await autoPilotButton.click();

    // Enable conflict resolution
    const conflictToggle = page.locator('[data-testid="resolve-conflicts-toggle"]').or(
      page.locator('switch:has-text("Разрешение конфликтов")')
    );
    await conflictToggle.click();

    // Generate schedule
    const generateButton = page.locator('button:has-text("Генерировать")').or(
      page.locator('[data-testid="generate-schedule-button"]')
    );
    await generateButton.click();

    // Verify conflicts were resolved
    await expect(page.locator('[data-testid="conflicts-resolved-count"]')).toContainText('1');
  });
});
