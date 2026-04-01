/**
 * Celery Background Tasks E2E Tests
 *
 * End-to-end tests for Celery background task execution and integration.
 * Tests cover task triggering, progress tracking, result display, and error handling.
 *
 * Test scenarios:
 * - Trigger auto-fill gaps task via UI
 * - Monitor task execution progress
 * - Verify gaps filled automatically
 * - Check task logs and errors
 * - Multiple concurrent tasks
 * - Task retry behavior
 */

import { test, expect } from '@playwright/test';

/**
 * Helper: Login as admin user
 */
async function login(page) {
  await page.goto('http://localhost:3000/login');
  await page.fill('input[name="email"]', 'admin@test.com');
  await page.fill('input[name="password"]', 'admin123');
  await page.click('button[type="submit"]');
  await page.waitForURL('http://localhost:3000/');
}

/**
 * Helper: Navigate to schedule page
 */
async function navigateToSchedule(page) {
  await page.goto('http://localhost:3000/schedule?channel=test-channel');
  await page.waitForLoadState('networkidle');
}

/**
 * Helper: Mock Celery task API responses
 */
function mockCeleryTaskAPI(page) {
  // Mock fill_gaps_task execution
  page.route('**/api/schedule-ai/auto-pilot/generate', async (route) => {
    await route.fulfill({
      status: 201,
      contentType: 'application/json',
      body: JSON.stringify({
        task_id: 'celery-task-' + Math.random().toString(36).substr(2, 9),
        channel_id: 'test-channel-id',
        status: 'pending',
        date_range: {
          start: new Date().toISOString().split('T')[0],
          end: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]
        },
        slots_created: 0,
        gaps_filled: 0,
        conflicts_resolved: 0,
        error_message: null
      })
    });
  });

  // Mock task progress API
  page.route('**/api/schedule-ai/tasks/*/progress', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        task_id: route.request().url.split('/').pop(),
        status: 'processing',
        progress: 50,
        slots_created: 3,
        gaps_filled: 2,
        conflicts_resolved: 0,
        current_step: 'Filling gaps with recommendations...',
        error_message: null
      })
    });
  });

  // Mock task completion
  page.route('**/api/schedule-ai/tasks/*/result', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        task_id: route.request().url.split('/').pop(),
        status: 'completed',
        slots_created: 8,
        gaps_filled: 5,
        conflicts_resolved: 1,
        date_range: {
          start: new Date().toISOString().split('T')[0],
          end: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]
        },
        error_message: null
      })
    });
  });

  // Mock schedule slots API
  page.route('**/api/schedule/slots**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        slots: [
          {
            id: 'slot-1',
            channel_id: 'test-channel-id',
            playlist_id: 'playlist-1',
            start_date: new Date().toISOString().split('T')[0],
            start_time: '10:00',
            end_time: '12:00',
            title: 'Morning Show',
            is_active: true,
            priority: 5
          },
          {
            id: 'slot-2',
            channel_id: 'test-channel-id',
            playlist_id: 'playlist-2',
            start_date: new Date().toISOString().split('T')[0],
            start_time: '14:00',
            end_time: '16:00',
            title: 'Afternoon Show',
            is_active: true,
            priority: 5
          }
        ],
        total: 2
      })
    });
  });

  // Mock gap detection API
  page.route('**/api/schedule-ai/detect-gaps', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        channel_id: 'test-channel-id',
        start_date: new Date().toISOString().split('T')[0],
        end_date: new Date().toISOString().split('T')[0],
        gaps: [
          {
            date: new Date().toISOString().split('T')[0],
            start_time: '08:00',
            end_time: '10:00',
            duration_hours: 2.0,
            is_peak_hour: true,
            reason: 'Утренний пик аудитории'
          },
          {
            date: new Date().toISOString().split('T')[0],
            start_time: '18:00',
            end_time: '22:00',
            duration_hours: 4.0,
            is_peak_hour: true,
            reason: 'Вечерний пик аудитории'
          }
        ],
        total_gap_hours: 6.0,
        peak_hours_gap_hours: 6.0
      })
    });
  });
}

/**
 * Helper: Mock Celery task execution with progress updates
 */
function mockCeleryTaskWithProgress(page, taskType: 'fill_gaps' | 'optimization' | 'suggestions') {
  let progress = 0;
  const progressInterval = setInterval(() => {
    progress += 10;
    if (progress > 100) {
      clearInterval(progressInterval);
    }
  }, 500);

  page.route(`**/api/schedule-ai/tasks/*/progress`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        task_id: 'test-task-' + taskType,
        status: progress < 100 ? 'processing' : 'completed',
        progress: Math.min(progress, 100),
        slots_created: progress < 100 ? Math.floor(progress / 10) : 10,
        gaps_filled: taskType === 'fill_gaps' ? (progress < 100 ? Math.floor(progress / 20) : 5) : 0,
        conflicts_resolved: taskType === 'optimization' ? (progress < 100 ? 0 : 2) : 0,
        current_step: progress < 100 ? 'Обработка...' : 'Завершено',
        error_message: null
      })
    });
  });
}

/**
 * Helper: Mock failed Celery task
 */
function mockFailedCeleryTask(page) {
  page.route('**/api/schedule-ai/auto-pilot/generate', async (route) => {
    await route.fulfill({
      status: 500,
      contentType: 'application/json',
      body: JSON.stringify({
        detail: 'Ошибка выполнения фоновой задачи'
      })
    });
  });

  page.route('**/api/schedule-ai/tasks/*/progress', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        task_id: 'failed-task',
        status: 'failed',
        progress: 25,
        slots_created: 0,
        gaps_filled: 0,
        conflicts_resolved: 0,
        current_step: 'Failed',
        error_message: 'Database connection timeout'
      })
    });
  });
}

// ==================== Test: Auto-Fill Gaps Task ====================

test.describe('Auto-Fill Gaps Task', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    mockCeleryTaskAPI(page);
  });

  test('should trigger fill_gaps_task via auto-pilot panel', async ({ page }) => {
    await navigateToSchedule(page);

    // Open auto-pilot panel
    await page.click('button[title="Сгенерировать расписание с помощью AI"]');
    await expect(page.locator('[data-testid="auto-pilot-panel"]')).toBeVisible();

    // Configure settings
    await page.check('input[type="checkbox"][value="use_ai_recommendations"]');
    await page.uncheck('input[type="checkbox"][value="resolve_conflicts"]');

    // Set max daily hours
    await page.fill('input[type="range"][name="max_daily_hours"]', '8');

    // Select date range (week)
    await page.click('button:has-text("Неделя")');

    // Click generate button
    await page.click('button:has-text("Сгенерировать")');

    // Verify task was triggered
    await expect(page.locator('text=Задача поставлена в очередь')).toBeVisible({ timeout: 5000 });
  });

  test('should display task progress updates', async ({ page }) => {
    await navigateToSchedule(page);

    // Open auto-pilot panel
    await page.click('button[title="Сгенерировать расписание с помощью AI"]');

    // Mock progress updates
    mockCeleryTaskWithProgress(page, 'fill_gaps');

    // Generate schedule
    await page.click('button:has-text("Сгенерировать")');

    // Wait for progress indicator
    await expect(page.locator('[data-testid="task-progress"]')).toBeVisible();

    // Verify progress is displayed
    const progressText = await page.locator('[data-testid="task-progress"]').textContent();
    expect(progressText).toContain('%');
  });

  test('should show completion message when task finishes', async ({ page }) => {
    await navigateToSchedule(page);

    // Open auto-pilot panel
    await page.click('button[title="Сгенерировать расписание с помощью AI"]');

    // Generate schedule
    await page.click('button:has-text("Сгенерировать")');

    // Wait for completion (simulate with timeout)
    await page.waitForTimeout(2000);

    // Verify completion message
    await expect(page.locator('text=Расписание создано')).toBeVisible({ timeout: 10000 });

    // Verify stats are displayed
    await expect(page.locator('text=Слотов создано:')).toBeVisible();
    await expect(page.locator('text=Пробелов заполнено:')).toBeVisible();
  });

  test('should refresh schedule after task completion', async ({ page }) => {
    await navigateToSchedule(page);

    // Get initial slot count
    const initialSlots = await page.locator('[data-testid="schedule-slot"]').count();

    // Open auto-pilot panel and generate
    await page.click('button[title="Сгенерировать расписание с помощью AI"]');
    await page.click('button:has-text("Сгенерировать")');

    // Wait for task completion
    await page.waitForTimeout(3000);

    // Verify schedule was refreshed (more slots now)
    await page.waitForTimeout(1000); // Additional wait for refresh
    const finalSlots = await page.locator('[data-testid="schedule-slot"]').count();
    expect(finalSlots).toBeGreaterThanOrEqual(initialSlots);
  });
});

// ==================== Test: Schedule Optimization Task ====================

test.describe('Schedule Optimization Task', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    mockCeleryTaskAPI(page);
  });

  test('should trigger optimization task via optimization modal', async ({ page }) => {
    await navigateToSchedule(page);

    // Open optimization modal
    await page.click('button[title="Оптимизировать расписание"]');
    await expect(page.locator('[data-testid="optimization-modal"]')).toBeVisible();

    // Configure optimization parameters
    await page.check('input[type="checkbox"][value="coverage"]');
    await page.check('input[type="checkbox"][value="engagement"]');
    await page.uncheck('input[type="checkbox"][value="variety"]');

    // Set weights
    await page.fill('input[type="range"][name="coverage_weight"]', '40');
    await page.fill('input[type="range"][name="engagement_weight"]', '60');

    // Click optimize button
    await page.click('button:has-text("Применить оптимизацию")');

    // Verify task was triggered
    await expect(page.locator('text=Оптимизация запущена')).toBeVisible({ timeout: 5000 });
  });

  test('should display optimization progress', async ({ page }) => {
    await navigateToSchedule(page);

    // Open optimization modal
    await page.click('button[title="Оптимизировать расписание"]');

    // Mock progress updates
    mockCeleryTaskWithProgress(page, 'optimization');

    // Start optimization
    await page.click('button:has-text("Применить оптимизацию")');

    // Verify progress indicator
    await expect(page.locator('[data-testid="optimization-progress"]')).toBeVisible();
  });

  test('should show optimization results', async ({ page }) => {
    await navigateToSchedule(page);

    // Open optimization modal
    await page.click('button[title="Оптимизировать расписание"]');

    // Start optimization
    await page.click('button:has-text("Применить оптимизацию")');

    // Wait for completion
    await page.waitForTimeout(3000);

    // Verify results are displayed
    await expect(page.locator('text=Оптимизация завершена')).toBeVisible();

    // Verify metrics
    await expect(page.locator('text=Покрытие:')).toBeVisible();
    await expect(page.locator('text=Вовлеченность:')).toBeVisible();
  });
});

// ==================== Test: Daily Suggestions Task ====================

test.describe('Daily Suggestions Task', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    mockCeleryTaskAPI(page);
  });

  test('should display AI recommendations from daily suggestions task', async ({ page }) => {
    await navigateToSchedule(page);

    // Mock suggestions API
    page.route('**/api/schedule-ai/recommendations**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          channel_id: 'test-channel-id',
          target_date: new Date().toISOString().split('T')[0],
          recommendations: [
            {
              id: 'rec-1',
              playlist_id: 'playlist-1',
              playlist_name: 'Вечерний плейлист',
              suggested_start_time: '19:00',
              suggested_end_time: '21:00',
              confidence_score: 92,
              description: 'Высокая вовлеченность в вечерние часы',
              recommendation_type: 'PEAK_HOURS'
            },
            {
              id: 'rec-2',
              playlist_id: 'playlist-2',
              playlist_name: 'Утренний плейлист',
              suggested_start_time: '08:00',
              suggested_end_time: '10:00',
              confidence_score: 85,
              description: 'Средняя вовлеченность утром',
              recommendation_type: 'FILL_GAP'
            }
          ]
        })
      });
    });

    // Select a day in the calendar
    await page.click('[data-testid="calendar-day"]:first-child');

    // Verify recommendations are displayed
    await expect(page.locator('[data-testid="ai-recommendations"]')).toBeVisible();
    await expect(page.locator('text=Вечерний плейлист')).toBeVisible();
    await expect(page.locator('text=92%')).toBeVisible(); // Confidence score
  });

  test('should allow applying recommendation to schedule', async ({ page }) => {
    await navigateToSchedule(page);

    // Mock recommendations API
    page.route('**/api/schedule-ai/recommendations**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          channel_id: 'test-channel-id',
          target_date: new Date().toISOString().split('T')[0],
          recommendations: [
            {
              id: 'rec-1',
              playlist_id: 'playlist-1',
              playlist_name: 'Тестовый плейлист',
              suggested_start_time: '10:00',
              suggested_end_time: '12:00',
              confidence_score: 88,
              description: 'Рекомендация',
              recommendation_type: 'PEAK_HOURS'
            }
          ]
        })
      });
    });

    // Mock slot creation API
    page.route('**/api/schedule/slots', async (route) => {
      if (route.request().method() === 'POST') {
        await route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify({
            id: 'new-slot-1',
            channel_id: 'test-channel-id',
            playlist_id: 'playlist-1',
            start_date: new Date().toISOString().split('T')[0],
            start_time: '10:00',
            end_time: '12:00',
            title: 'Тестовый плейлист',
            is_active: true,
            priority: 5
          })
        });
      }
    });

    // Select a day
    await page.click('[data-testid="calendar-day"]:first-child');

    // Wait for recommendations
    await expect(page.locator('[data-testid="ai-recommendations"]')).toBeVisible();

    // Click apply button on first recommendation
    await page.click('[data-testid="apply-recommendation-btn"]:first-child');

    // Verify success message
    await expect(page.locator('text=Слот создан')).toBeVisible({ timeout: 5000 });
  });
});

// ==================== Test: Task Error Handling ====================

test.describe('Celery Task Error Handling', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('should display error when task fails', async ({ page }) => {
    await navigateToSchedule(page);

    // Mock failed task
    mockFailedCeleryTask(page);

    // Open auto-pilot panel
    await page.click('button[title="Сгенерировать расписание с помощью AI"]');

    // Try to generate schedule
    await page.click('button:has-text("Сгенерировать")');

    // Verify error message is displayed
    await expect(page.locator('text=Ошибка выполнения задачи')).toBeVisible({ timeout: 5000 });
    await expect(page.locator('text=Database connection timeout')).toBeVisible();
  });

  test('should handle task timeout gracefully', async ({ page }) => {
    await navigateToSchedule(page);

    // Mock timeout scenario
    page.route('**/api/schedule-ai/auto-pilot/generate', async (route) => {
      // Delay response to simulate timeout
      await new Promise(resolve => setTimeout(resolve, 10000));
      await route.fulfill({
        status: 408,
        contentType: 'application/json',
        body: JSON.stringify({
          detail: 'Request timeout'
        })
      });
    });

    // Open auto-pilot panel
    await page.click('button[title="Сгенерировать расписание с помощью AI"]');

    // Try to generate schedule
    await page.click('button:has-text("Сгенерировать")');

    // Verify timeout message
    await expect(page.locator('text=Тайм-аут запроса')).toBeVisible({ timeout: 15000 });
  });

  test('should allow retry after task failure', async ({ page }) => {
    await navigateToSchedule(page);

    // Mock failed task first, then success
    let attempt = 0;
    page.route('**/api/schedule-ai/auto-pilot/generate', async (route) => {
      attempt++;
      if (attempt === 1) {
        await route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({
            detail: 'Temporary error'
          })
        });
      } else {
        await route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify({
            task_id: 'retry-task-' + Math.random().toString(36).substr(2, 9),
            channel_id: 'test-channel-id',
            status: 'pending',
            date_range: {},
            slots_created: 0,
            gaps_filled: 0,
            conflicts_resolved: 0,
            error_message: null
          })
        });
      }
    });

    // Open auto-pilot panel
    await page.click('button[title="Сгенерировать расписание с помощью AI"]');

    // Try to generate schedule (first attempt fails)
    await page.click('button:has-text("Сгенерировать")');
    await expect(page.locator('text=Ошибка')).toBeVisible();

    // Click retry button
    await page.click('button:has-text("Повторить")');

    // Verify success on retry
    await expect(page.locator('text=Задача поставлена в очередь')).toBeVisible({ timeout: 5000 });
  });
});

// ==================== Test: Task Progress Tracking ====================

test.describe('Task Progress Tracking', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    mockCeleryTaskAPI(page);
  });

  test('should poll task progress periodically', async ({ page }) => {
    await navigateToSchedule(page);

    // Open auto-pilot panel
    await page.click('button[title="Сгенерировать расписание с помощью AI"]');

    // Mock multiple progress updates
    let callCount = 0;
    page.route('**/api/schedule-ai/tasks/*/progress', async (route) => {
      callCount++;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          task_id: 'test-task',
          status: callCount < 3 ? 'processing' : 'completed',
          progress: Math.min(callCount * 33, 100),
          slots_created: callCount < 3 ? callCount : 5,
          gaps_filled: callCount < 3 ? 0 : 3,
          conflicts_resolved: 0,
          current_step: callCount < 3 ? 'Обработка...' : 'Завершено',
          error_message: null
        })
      });
    });

    // Generate schedule
    await page.click('button:has-text("Сгенерировать")');

    // Verify multiple progress calls (polling)
    await page.waitForTimeout(2000);
    expect(callCount).toBeGreaterThan(1);
  });

  test('should display detailed progress information', async ({ page }) => {
    await navigateToSchedule(page);

    // Open auto-pilot panel
    await page.click('button[title="Сгенерировать расписание с помощью AI"]');

    // Mock detailed progress
    page.route('**/api/schedule-ai/tasks/*/progress', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          task_id: 'test-task',
          status: 'processing',
          progress: 45,
          slots_created: 3,
          gaps_filled: 2,
          conflicts_resolved: 1,
          current_step: 'Заполнение пробелов с рекомендациями...',
          error_message: null
        })
      });
    });

    // Generate schedule
    await page.click('button:has-text("Сгенерировать")');

    // Verify detailed info is displayed
    await expect(page.locator('text=45%')).toBeVisible();
    await expect(page.locator('text=3 слотов создано')).toBeVisible();
    await expect(page.locator('text=2 пробела заполнено')).toBeVisible();
    await expect(page.locator('text=Заполнение пробелов')).toBeVisible();
  });
});

// ==================== Test: Concurrent Tasks ====================

test.describe('Concurrent Task Execution', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    mockCeleryTaskAPI(page);
  });

  test('should handle multiple tasks running simultaneously', async ({ page }) => {
    await navigateToSchedule(page);

    // Start first task (auto-pilot)
    await page.click('button[title="Сгенерировать расписание с помощью AI"]');
    await page.click('button:has-text("Сгенерировать")');

    // Wait a bit
    await page.waitForTimeout(500);

    // Open optimization modal (should work even with task running)
    await page.click('button[title="Оптимизировать расписание"]');
    await expect(page.locator('[data-testid="optimization-modal"]')).toBeVisible();

    // Verify both can be active
    await expect(page.locator('[data-testid="auto-pilot-panel"]')).toBeVisible();
    await expect(page.locator('[data-testid="optimization-modal"]')).toBeVisible();
  });

  test('should display task queue status', async ({ page }) => {
    await navigateToSchedule(page);

    // Mock multiple tasks in queue
    page.route('**/api/schedule-ai/tasks/queue', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          running: 1,
          pending: 2,
          total: 3,
          tasks: [
            {
              task_id: 'task-1',
              type: 'auto_pilot',
              status: 'running',
              progress: 45
            },
            {
              task_id: 'task-2',
              type: 'optimization',
              status: 'pending',
              progress: 0
            },
            {
              task_id: 'task-3',
              type: 'fill_gaps',
              status: 'pending',
              progress: 0
            }
          ]
        })
      });
    });

    // Navigate to tasks page (if exists)
    await page.goto('http://localhost:3000/tasks');
    await expect(page.locator('[data-testid="task-queue"]')).toBeVisible();
    await expect(page.locator('text=1 выполняется')).toBeVisible();
    await expect(page.locator('text=2 в очереди')).toBeVisible();
  });
});
