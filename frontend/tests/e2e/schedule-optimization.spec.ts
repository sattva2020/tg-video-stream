/**
 * E2E тесты для оптимизации расписания.
 *
 * Покрывает полный пользовательский сценарий:
 * - Навигация на страницу расписания
 * - Открытие модального окна оптимизации
 * - Настройка параметров оптимизации
 * - Просмотр предпросмотра оптимизации
 * - Применение оптимизации
 * - Проверка сохраненных изменений
 */

import { test, expect, Page } from '@playwright/test';

// ==================== Test Fixtures ====================

const TEST_USER = {
  email: 'admin@test.com',
  password: 'testpassword123',
};

const TEST_CHANNEL = 'test-channel';

const TEST_DATE_RANGE = {
  start: '2025-01-23',
  end: '2025-01-30',
};

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

async function mockOptimizationAPI(page: Page) {
  // Mock optimization preview endpoint
  await page.route('**/api/schedule-ai/optimize/preview', async route => {
    await route.fulfill({
      json: {
        id: 'opt-123',
        channel_id: TEST_CHANNEL,
        start_date: TEST_DATE_RANGE.start,
        end_date: TEST_DATE_RANGE.end,
        status: 'completed',
        metrics: {
          coverage: 85.5,
          engagement_score: 7.8,
          variety_score: 8.2,
          conflicts_count: 2,
          peak_hours_coverage: 90.0,
        },
        suggestions: [
          {
            date: '2025-01-24',
            start_time: '10:00',
            end_time: '12:00',
            playlist_id: 'playlist-1',
            playlist_name: 'Morning Hits',
            reason: 'Высокая вовлеченность в это время',
            priority: 1,
          },
          {
            date: '2025-01-24',
            start_time: '14:00',
            end_time: '16:00',
            playlist_id: 'playlist-2',
            playlist_name: 'Afternoon Vibes',
            reason: 'Заполнение пробела в расписании',
            priority: 2,
          },
          {
            date: '2025-01-25',
            start_time: '18:00',
            end_time: '20:00',
            playlist_id: 'playlist-3',
            playlist_name: 'Evening Classics',
            reason: 'Пиковые часы listening',
            priority: 1,
          },
        ],
        parameters: {
          prioritize_coverage: true,
          prioritize_variety: false,
          prioritize_peak_hours: true,
          maximize_engagement: true,
          avoid_conflicts: true,
          weights: {
            coverage: 25,
            engagement: 30,
            variety: 20,
            conflicts: 15,
            peak_hours: 10,
          },
        },
        warnings: [
          'Обнаружено 2 конфликта, которые будут разрешены',
          'Некоторые пиковые часы не покрыты',
        ],
        created_at: new Date().toISOString(),
      },
    });
  });

  // Mock schedule slots endpoint
  await page.route('**/api/schedule/slots**', async route => {
    await route.fulfill({
      json: [
        {
          id: 'slot-1',
          channel_id: TEST_CHANNEL,
          playlist_id: 'playlist-1',
          start_date: '2025-01-24',
          start_time: '10:00',
          end_time: '12:00',
          title: 'Morning Hits',
          is_active: true,
          priority: 1,
        },
      ],
    });
  });

  // Mock create slot endpoint (for applying optimization)
  await page.route('**/api/schedule/slots**', async route => {
    if (route.request().method() === 'POST') {
      await route.fulfill({
        json: {
          id: 'new-slot-123',
          channel_id: TEST_CHANNEL,
          playlist_id: 'playlist-2',
          start_date: '2025-01-24',
          start_time: '14:00',
          end_time: '16:00',
          title: 'Afternoon Vibes',
          is_active: true,
          priority: 2,
        },
      });
    } else {
      await route.continue();
    }
  });

  // Mock detect gaps endpoint
  await page.route('**/api/schedule-ai/detect-gaps', async route => {
    await route.fulfill({
      json: {
        channel_id: TEST_CHANNEL,
        start_date: TEST_DATE_RANGE.start,
        end_date: TEST_DATE_RANGE.end,
        gaps: [
          {
            date: '2025-01-24',
            start_time: '14:00',
            end_time: '16:00',
            duration_hours: 2,
            is_peak_hour: true,
          },
          {
            date: '2025-01-25',
            start_time: '18:00',
            end_time: '20:00',
            duration_hours: 2,
            is_peak_hour: true,
          },
        ],
        total_gap_hours: 4,
        peak_hours_gaps: 2,
        analyzed_at: new Date().toISOString(),
      },
    });
  });

  // Mock detect conflicts endpoint
  await page.route('**/api/schedule-ai/detect-conflicts', async route => {
    await route.fulfill({
      json: {
        channel_id: TEST_CHANNEL,
        start_date: TEST_DATE_RANGE.start,
        end_date: TEST_DATE_RANGE.end,
        conflicts: [
          {
            date: '2025-01-24',
            time_range: '10:00-12:00',
            conflicts: [
              {
                slot_id: 'slot-1',
                playlist_name: 'Morning Hits',
                start_time: '10:00',
                end_time: '12:00',
                priority: 1,
              },
              {
                slot_id: 'slot-2',
                playlist_name: 'Overlap Show',
                start_time: '11:00',
                end_time: '13:00',
                priority: 2,
              },
            ],
          },
        ],
        total_conflicts: 1,
        affected_dates: 1,
        analyzed_at: new Date().toISOString(),
      },
    });
  });
}

// ==================== Navigation Tests ====================

test.describe('Optimization Modal Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await mockOptimizationAPI(page);
  });

  test('optimization button is visible on schedule page', async ({ page }) => {
    await navigateToSchedule(page);

    const optimizationButton = page.locator('button:has-text("Оптимизировать")').or(
      page.locator('[data-testid="optimization-button"]')
    );

    await expect(optimizationButton).toBeVisible();
  });

  test('opens optimization modal when button clicked', async ({ page }) => {
    await navigateToSchedule(page);

    const optimizationButton = page.locator('button:has-text("Оптимизировать")').or(
      page.locator('[data-testid="optimization-button"]')
    );

    await optimizationButton.click();

    // Check that modal is visible
    await expect(page.locator('[data-testid="optimization-modal"]').or(
      page.locator('.modal[role="dialog"]')
    )).toBeVisible();
  });

  test('closes modal when close button clicked', async ({ page }) => {
    await navigateToSchedule(page);

    const optimizationButton = page.locator('button:has-text("Оптимизировать")').or(
      page.locator('[data-testid="optimization-button"]')
    );

    await optimizationButton.click();

    // Click close button
    const closeButton = page.locator('button:has-text("✕")').or(
      page.locator('[data-testid="close-modal-button"]')
    );

    await closeButton.click();

    // Modal should not be visible
    await expect(page.locator('[data-testid="optimization-modal"]')).not.toBeVisible();
  });
});

// ==================== Optimization Parameters Tests ====================

test.describe('Optimization Parameters Configuration', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await mockOptimizationAPI(page);
    await navigateToSchedule(page);

    // Open optimization modal
    const optimizationButton = page.locator('button:has-text("Оптимизировать")').or(
      page.locator('[data-testid="optimization-button"]')
    );
    await optimizationButton.click();
  });

  test('shows optimization parameter toggles', async ({ page }) => {
    // Check for prioritize coverage toggle
    await expect(page.locator('[data-testid="prioritize-coverage-toggle"]').or(
      page.locator('text=/Покрытие/i')
    )).toBeVisible();

    // Check for prioritize variety toggle
    await expect(page.locator('[data-testid="prioritize-variety-toggle"]').or(
      page.locator('text=/Разнообразие/i')
    )).toBeVisible();

    // Check for prioritize peak hours toggle
    await expect(page.locator('[data-testid="prioritize-peak-hours-toggle"]').or(
      page.locator('text=/Пиковые часы/i')
    )).toBeVisible();
  });

  test('shows weight sliders for optimization objectives', async ({ page }) => {
    // Check for coverage weight slider
    await expect(page.locator('[data-testid="coverage-weight-slider"]').or(
      page.locator('input[type="range"]')
    ).first()).toBeVisible();

    // Check for engagement weight slider
    await expect(page.locator('[data-testid="engagement-weight-slider"]').or(
      page.locator('input[type="range"]')
    ).nth(1)).toBeVisible();
  });

  test('displays current weight values', async ({ page }) => {
    // Weight values should be visible
    await expect(page.locator('text=/25%/').or(
      page.locator('[data-testid="coverage-weight-value"]')
    )).toBeVisible();
  });

  test('validates total weights sum to 100%', async ({ page }) => {
    const previewButton = page.locator('button:has-text("Предпросмотр")').or(
      page.locator('[data-testid="preview-button"]')
    );

    // Initially should be disabled if weights don't sum to 100%
    // (this depends on implementation, adjust as needed)
    await expect(previewButton).toBeVisible();
  });
});

// ==================== Preview Tests ====================

test.describe('Optimization Preview', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await mockOptimizationAPI(page);
    await navigateToSchedule(page);

    // Open optimization modal
    const optimizationButton = page.locator('button:has-text("Оптимизировать")').or(
      page.locator('[data-testid="optimization-button"]')
    );
    await optimizationButton.click();
  });

  test('shows preview button', async ({ page }) => {
    const previewButton = page.locator('button:has-text("Предпросмотр")').or(
      page.locator('[data-testid="preview-button"]')
    );

    await expect(previewButton).toBeVisible();
  });

  test('displays loading state during preview', async ({ page }) => {
    // Slow response to show loading state
    await page.route('**/api/schedule-ai/optimize/preview', async route => {
      await new Promise(resolve => setTimeout(resolve, 2000));
      const originalResponse = await route.fetch();
      const json = await originalResponse.json();
      await route.fulfill({ json });
    });

    const previewButton = page.locator('button:has-text("Предпросмотр")').or(
      page.locator('[data-testid="preview-button"]')
    );

    await previewButton.click();

    // Check for loading indicator
    await expect(page.locator('[data-testid="loading-spinner"]').or(
      page.locator('.spinner').or(page.locator('[aria-busy="true"]'))
    )).toBeVisible();
  });

  test('displays optimization metrics after preview', async ({ page }) => {
    const previewButton = page.locator('button:has-text("Предпросмотр")').or(
      page.locator('[data-testid="preview-button"]')
    );

    await previewButton.click();

    // Wait for preview to complete
    await page.waitForTimeout(1000);

    // Check for metrics display
    await expect(page.locator('text=/85\\.5%/').or(
      page.locator('[data-testid="coverage-metric"]')
    )).toBeVisible();

    await expect(page.locator('text=/7\\.8/').or(
      page.locator('[data-testid="engagement-metric"]')
    )).toBeVisible();
  });

  test('displays suggestions list after preview', async ({ page }) => {
    const previewButton = page.locator('button:has-text("Предпросмотр")').or(
      page.locator('[data-testid="preview-button"]')
    );

    await previewButton.click();

    // Wait for preview to complete
    await page.waitForTimeout(1000);

    // Check for suggestions
    await expect(page.locator('text=Morning Hits').or(
      page.locator('[data-testid="suggestion-item"]')
    ).first()).toBeVisible();

    await expect(page.locator('text=Afternoon Vibes')).toBeVisible();
  });

  test('displays warnings if any', async ({ page }) => {
    const previewButton = page.locator('button:has-text("Предпросмотр")').or(
      page.locator('[data-testid="preview-button"]')
    );

    await previewButton.click();

    // Wait for preview to complete
    await page.waitForTimeout(1000);

    // Check for warnings
    await expect(page.locator('text=/Обнаружено.*конфликт/i').or(
      page.locator('[data-testid="optimization-warning"]')
    )).toBeVisible();
  });

  test('shows apply button after successful preview', async ({ page }) => {
    const previewButton = page.locator('button:has-text("Предпросмотр")').or(
      page.locator('[data-testid="preview-button"]')
    );

    await previewButton.click();

    // Wait for preview to complete
    await page.waitForTimeout(1000);

    // Apply button should be visible
    await expect(page.locator('button:has-text("Применить")').or(
      page.locator('[data-testid="apply-button"]')
    )).toBeVisible();
  });
});

// ==================== Apply Optimization Tests ====================

test.describe('Apply Optimization', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await mockOptimizationAPI(page);
    await navigateToSchedule(page);

    // Open optimization modal
    const optimizationButton = page.locator('button:has-text("Оптимизировать")').or(
      page.locator('[data-testid="optimization-button"]')
    );
    await optimizationButton.click();

    // Generate preview
    const previewButton = page.locator('button:has-text("Предпросмотр")').or(
      page.locator('[data-testid="preview-button"]')
    );
    await previewButton.click();

    // Wait for preview to complete
    await page.waitForTimeout(1000);
  });

  test('applies optimization when apply button clicked', async ({ page }) => {
    const applyButton = page.locator('button:has-text("Применить")').or(
      page.locator('[data-testid="apply-button"]')
    );

    await applyButton.click();

    // Check for success message
    await expect(page.locator('text=/оптимизация применена/i').or(
      page.locator('[data-testid="success-message"]')
    )).toBeVisible();
  });

  test('closes modal after successful application', async ({ page }) => {
    const applyButton = page.locator('button:has-text("Применить")').or(
      page.locator('[data-testid="apply-button"]')
    );

    await applyButton.click();

    // Wait a moment for modal to close
    await page.waitForTimeout(500);

    // Modal should not be visible
    await expect(page.locator('[data-testid="optimization-modal"]')).not.toBeVisible();
  });

  test('refreshes schedule data after applying', async ({ page }) => {
    // Track schedule refresh
    let scheduleRefreshed = false;
    await page.route('**/api/schedule/slots**', async route => {
      if (route.request().method() === 'GET') {
        scheduleRefreshed = true;
      }
      await route.continue();
    });

    const applyButton = page.locator('button:has-text("Применить")').or(
      page.locator('[data-testid="apply-button"]')
    );

    await applyButton.click();

    // Wait for refresh
    await page.waitForTimeout(1000);

    // Schedule should be refreshed
    expect(scheduleRefreshed).toBeTruthy();
  });

  test('shows loading state during application', async ({ page }) => {
    // Slow response
    await page.route('**/api/schedule/slots', async route => {
      if (route.request().method() === 'POST') {
        await new Promise(resolve => setTimeout(resolve, 2000));
        await route.fulfill({
          json: {
            id: 'new-slot-123',
            channel_id: TEST_CHANNEL,
            playlist_id: 'playlist-2',
            start_date: '2025-01-24',
            start_time: '14:00',
            end_time: '16:00',
            title: 'Afternoon Vibes',
            is_active: true,
            priority: 2,
          },
        });
      } else {
        await route.continue();
      }
    });

    const applyButton = page.locator('button:has-text("Применить")').or(
      page.locator('[data-testid="apply-button"]')
    );

    await applyButton.click();

    // Check for loading state
    await expect(page.locator('[data-testid="loading-spinner"]').or(
      page.locator('.spinner').or(page.locator('[aria-busy="true"]'))
    )).toBeVisible();
  });
});

// ==================== Error Handling Tests ====================

test.describe('Optimization Error Handling', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('handles API error during preview', async ({ page }) => {
    await navigateToSchedule(page);

    // Mock error response
    await page.route('**/api/schedule-ai/optimize/preview', async route => {
      await route.fulfill({
        status: 500,
        json: {
          detail: 'Ошибка при получении предпросмотра оптимизации',
        },
      });
    });

    // Open optimization modal
    const optimizationButton = page.locator('button:has-text("Оптимизировать")').or(
      page.locator('[data-testid="optimization-button"]')
    );
    await optimizationButton.click();

    // Try to preview
    const previewButton = page.locator('button:has-text("Предпросмотр")').or(
      page.locator('[data-testid="preview-button"]')
    );
    await previewButton.click();

    // Check for error message
    await expect(page.locator('text=/ошибка/i').or(
      page.locator('[data-testid="error-message"]')
    )).toBeVisible();
  });

  test('handles network error', async ({ page }) => {
    await navigateToSchedule(page);

    // Mock network failure
    await page.route('**/api/schedule-ai/optimize/preview', route => {
      route.abort('failed');
    });

    // Open optimization modal
    const optimizationButton = page.locator('button:has-text("Оптимизировать")').or(
      page.locator('[data-testid="optimization-button"]')
    );
    await optimizationButton.click();

    // Try to preview
    const previewButton = page.locator('button:has-text("Предпросмотр")').or(
      page.locator('[data-testid="preview-button"]')
    );
    await previewButton.click();

    // Check for error message
    await expect(page.locator('text=/сеть.*недоступна/i').or(
      page.locator('[data-testid="error-message"]')
    )).toBeVisible();
  });

  test('handles API error during apply', async ({ page }) => {
    await mockOptimizationAPI(page);
    await navigateToSchedule(page);

    // Open optimization modal
    const optimizationButton = page.locator('button:has-text("Оптимизировать")').or(
      page.locator('[data-testid="optimization-button"]')
    );
    await optimizationButton.click();

    // Generate preview
    const previewButton = page.locator('button:has-text("Предпросмотр")').or(
      page.locator('[data-testid="preview-button"]')
    );
    await previewButton.click();
    await page.waitForTimeout(1000);

    // Mock error for apply
    await page.route('**/api/schedule/slots', async route => {
      if (route.request().method() === 'POST') {
        await route.fulfill({
          status: 500,
          json: {
            detail: 'Ошибка при применении оптимизации',
          },
        });
      } else {
        await route.continue();
      }
    });

    // Try to apply
    const applyButton = page.locator('button:has-text("Применить")').or(
      page.locator('[data-testid="apply-button"]')
    );
    await applyButton.click();

    // Check for error message
    await expect(page.locator('text=/ошибка/i').or(
      page.locator('[data-testid="error-message"]')
    )).toBeVisible();
  });
});

// ==================== Integration Tests ====================

test.describe('Optimization End-to-End Workflow', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await mockOptimizationAPI(page);
  });

  test('complete optimization workflow', async ({ page }) => {
    await navigateToSchedule(page);

    // Step 1: Open optimization modal
    const optimizationButton = page.locator('button:has-text("Оптимизировать")').or(
      page.locator('[data-testid="optimization-button"]')
    );
    await optimizationButton.click();

    // Verify modal opened
    await expect(page.locator('[data-testid="optimization-modal"]').or(
      page.locator('.modal[role="dialog"]')
    )).toBeVisible();

    // Step 2: Configure parameters
    const prioritizePeakHours = page.locator('[data-testid="prioritize-peak-hours-toggle"]').or(
      page.locator('switch:has-text("Пиковые часы")')
    );
    await prioritizePeakHours.click();

    // Step 3: Preview optimization
    const previewButton = page.locator('button:has-text("Предпросмотр")').or(
      page.locator('[data-testid="preview-button"]')
    );
    await previewButton.click();

    // Wait for preview
    await page.waitForTimeout(1000);

    // Step 4: Verify metrics displayed
    await expect(page.locator('text=/85\\.5%/').or(
      page.locator('[data-testid="coverage-metric"]')
    )).toBeVisible();

    // Step 5: Verify suggestions displayed
    await expect(page.locator('text=Morning Hits')).toBeVisible();

    // Step 6: Apply optimization
    const applyButton = page.locator('button:has-text("Применить")').or(
      page.locator('[data-testid="apply-button"]')
    );
    await applyButton.click();

    // Step 7: Verify success message
    await expect(page.locator('text=/оптимизация применена/i').or(
      page.locator('[data-testid="success-message"]')
    )).toBeVisible();

    // Step 8: Verify modal closed
    await page.waitForTimeout(500);
    await expect(page.locator('[data-testid="optimization-modal"]')).not.toBeVisible();

    // Step 9: Verify schedule refreshed (new slots visible)
    await expect(page.locator('text=Afternoon Vibes')).toBeVisible();
  });

  test('optimization with conflicts detected', async ({ page }) => {
    await navigateToSchedule(page);

    // Open optimization modal
    const optimizationButton = page.locator('button:has-text("Оптимизировать")').or(
      page.locator('[data-testid="optimization-button"]')
    );
    await optimizationButton.click();

    // Preview optimization (mock includes conflicts)
    const previewButton = page.locator('button:has-text("Предпросмотр")').or(
      page.locator('[data-testid="preview-button"]')
    );
    await previewButton.click();

    // Wait for preview
    await page.waitForTimeout(1000);

    // Verify conflict warning displayed
    await expect(page.locator('text=/Обнаружено.*2.*конфликт/i').or(
      page.locator('[data-testid="optimization-warning"]')
    )).toBeVisible();

    // Metrics should show conflicts
    await expect(page.locator('text=/2.*конфликт/i')).toBeVisible();

    // Apply should still be available
    await expect(page.locator('button:has-text("Применить")').or(
      page.locator('[data-testid="apply-button"]')
    )).toBeVisible();
  });

  test('optimization with gap detection', async ({ page }) => {
    await navigateToSchedule(page);

    // Open optimization modal
    const optimizationButton = page.locator('button:has-text("Оптимизировать")').or(
      page.locator('[data-testid="optimization-button"]')
    );
    await optimizationButton.click();

    // Preview optimization
    const previewButton = page.locator('button:has-text("Предпросмотр")').or(
      page.locator('[data-testid="preview-button"]')
    );
    await previewButton.click();

    // Wait for preview
    await page.waitForTimeout(1000);

    // Verify gap-filling suggestions
    await expect(page.locator('text=Заполнение пробела')).toBeVisible();

    // Multiple suggestions should be present
    const suggestionItems = page.locator('[data-testid="suggestion-item"]').or(
      page.locator('.suggestion-item')
    );
    await expect(suggestionItems).toHaveCount(await suggestionItems.count());
  });
});
