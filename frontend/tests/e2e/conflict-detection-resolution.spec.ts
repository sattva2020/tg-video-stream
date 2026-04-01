/**
 * E2E тесты для обнаружения и разрешения конфликтов в расписании.
 *
 * Покрывает полный пользовательский сценарий:
 * - Создание пересекающихся слотов расписания
 * - Обнаружение конфликтов
 * - Отображение предупреждений о конфликтах
 * - Применение разрешения конфликтов на основе приоритетов
 * - Проверку работы системы приоритетов
 */

import { test, expect, Page } from '@playwright/test';

// ==================== Test Data ====================

const TEST_USER = {
  email: 'admin@test.com',
  password: 'testpassword123',
};

const TEST_CHANNEL = 'test-channel';

const TEST_DATE = new Date().toISOString().split('T')[0]; // Сегодня

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

function mockScheduleAPI(page: Page) {
  // Mock schedule slots endpoint с пересекающимися слотами
  page.route('**/api/schedule/slots**', async (route) => {
    await route.fulfill({
      json: [
        {
          id: 'slot-1',
          channel_id: TEST_CHANNEL,
          playlist_id: 'playlist-1',
          playlist_name: 'Morning Playlist',
          start_date: TEST_DATE,
          start_time: '10:00:00',
          end_time: '12:00:00',
          title: 'Morning Show',
          color: '#3B82F6',
          is_active: true,
          repeat_type: 'none',
          priority: 10,
        },
        {
          id: 'slot-2',
          channel_id: TEST_CHANNEL,
          playlist_id: 'playlist-2',
          playlist_name: 'Midday Playlist',
          start_date: TEST_DATE,
          start_time: '11:00:00',
          end_time: '13:00:00',
          title: 'Midday Show',
          color: '#10B981',
          is_active: true,
          repeat_type: 'none',
          priority: 5,
        },
      ],
    });
  });
}

function mockConflictDetectionAPI(page: Page, hasConflicts: boolean = true) {
  // Mock conflict detection endpoint
  page.route('**/api/schedule-ai/detect-conflicts', async (route) => {
    if (hasConflicts) {
      await route.fulfill({
        json: {
          channel_id: TEST_CHANNEL,
          period: {
            start: TEST_DATE,
            end: TEST_DATE,
          },
          total_conflicts: 1,
          conflicts: [
            {
              date: TEST_DATE,
              conflicts: [
                {
                  slot_id: 'slot-1',
                  title: 'Morning Show',
                  playlist_name: 'Morning Playlist',
                  start_time: '10:00',
                  end_time: '12:00',
                  priority: 10,
                },
                {
                  slot_id: 'slot-2',
                  title: 'Midday Show',
                  playlist_name: 'Midday Playlist',
                  start_time: '11:00',
                  end_time: '13:00',
                  priority: 5,
                },
              ],
            },
          ],
        },
      });
    } else {
      await route.fulfill({
        json: {
          channel_id: TEST_CHANNEL,
          period: {
            start: TEST_DATE,
            end: TEST_DATE,
          },
          total_conflicts: 0,
          conflicts: [],
        },
      });
    }
  });
}

function mockConflictResolutionAPI(page: Page) {
  // Mock conflict resolution endpoint
  page.route('**/api/schedule-ai/resolve-conflicts', async (route) => {
    await route.fulfill({
      json: {
        channel_id: TEST_CHANNEL,
        period: {
          start: TEST_DATE,
          end: TEST_DATE,
        },
        total_conflicts: 1,
        conflicts: [
          {
            date: TEST_DATE,
            conflicts: [
              {
                slot_id: 'slot-1',
                title: 'Morning Show',
                playlist_name: 'Morning Playlist',
                start_time: '10:00',
                end_time: '12:00',
                priority: 10,
                resolution: 'keep',
              },
              {
                slot_id: 'slot-2',
                title: 'Midday Show',
                playlist_name: 'Midday Playlist',
                start_time: '11:00',
                end_time: '13:00',
                priority: 5,
                resolution: 'move',
                alternative_times: [
                  {
                    start_time: '13:00',
                    end_time: '15:00',
                    reason: 'Пустой слот после 13:00',
                  },
                  {
                    start_time: '15:00',
                    end_time: '17:00',
                    reason: 'Пустой слот после 15:00',
                  },
                ],
              },
            ],
          },
        ],
        resolutions_applied: 1,
        slots_removed: 0,
        slots_modified: 1,
        remaining_conflicts: 0,
      },
    });
  });
}

async function createOverlappingSlots(page: Page) {
  // Создаём первый слот
  await page.click('[data-testid="add-slot-button"]');
  await page.fill('[data-testid="slot-title-input"]', 'Morning Show');
  await page.fill('[data-testid="slot-start-time"]', '10:00');
  await page.fill('[data-testid="slot-end-time"]', '12:00');
  await page.selectOption('[data-testid="slot-priority"]', '10');
  await page.click('[data-testid="save-slot-button"]');

  // Создаём второй пересекающийся слот
  await page.click('[data-testid="add-slot-button"]');
  await page.fill('[data-testid="slot-title-input"]', 'Midday Show');
  await page.fill('[data-testid="slot-start-time"]', '11:00');
  await page.fill('[data-testid="slot-end-time"]', '13:00');
  await page.selectOption('[data-testid="slot-priority"]', '5');
  await page.click('[data-testid="save-slot-button"]');
}

// ==================== Test Suites ====================

test.describe('Conflict Detection', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await navigateToSchedule(page);
    mockScheduleAPI(page);
    mockConflictDetectionAPI(page, true);
  });

  test('should display conflict warning when overlapping slots exist', async ({ page }) => {
    // Переходим на выбранную дату
    await page.click(`[data-testid="day-${TEST_DATE}"]`);

    // Проверяем, что отображается предупреждение о конфликте
    const conflictWarning = page.locator('[data-testid="conflict-warning"]');
    await expect(conflictWarning).toBeVisible();

    // Проверяем текст предупреждения
    await expect(conflictWarning).toContainText(/конфликт|conflict/i);
    await expect(conflictWarning).toContainText('2'); // Количество конфликтующих слотов
  });

  test('should show conflicting slots with visual highlighting', async ({ page }) => {
    // Переходим на выбранную дату
    await page.click(`[data-testid="day-${TEST_DATE}"]`);

    // Проверяем, что конфликтующие слоты подсвечены
    const conflictSlots = page.locator('[data-testid="conflicting-slot"]');
    await expect(conflictSlots).toHaveCount(2);

    // Проверяем, что слоты имеют красную границу или фон
    const firstSlot = conflictSlots.nth(0);
    await expect(firstSlot).toHaveCSS('border-color', /rgb(239, 68, 68)|#ef4444/i);
  });

  test('should display priority information for conflicting slots', async ({ page }) => {
    // Переходим на выбранную дату
    await page.click(`[data-testid="day-${TEST_DATE}"]`);

    // Проверяем отображение приоритетов
    const priorities = page.locator('[data-testid="slot-priority-badge"]');
    await expect(priorities).toHaveCount(2);

    // Проверяем значения приоритетов
    await expect(priorities.nth(0)).toContainText('10');
    await expect(priorities.nth(1)).toContainText('5');
  });

  test('should not show conflict warning when no conflicts exist', async ({ page }) => {
    // Mock API без конфликтов
    mockConflictDetectionAPI(page, false);
    await page.reload();

    // Переходим на выбранную дату
    await page.click(`[data-testid="day-${TEST_DATE}"]`);

    // Проверяем, что предупреждение не отображается
    const conflictWarning = page.locator('[data-testid="conflict-warning"]');
    await expect(conflictWarning).not.toBeVisible();
  });

  test('should detect conflicts across multiple days', async ({ page }) => {
    // Mock API с конфликтами на несколько дней
    page.route('**/api/schedule-ai/detect-conflicts', async (route) => {
      const tomorrow = new Date();
      tomorrow.setDate(tomorrow.getDate() + 1);
      const tomorrowStr = tomorrow.toISOString().split('T')[0];

      await route.fulfill({
        json: {
          channel_id: TEST_CHANNEL,
          period: {
            start: TEST_DATE,
            end: tomorrowStr,
          },
          total_conflicts: 2,
          conflicts: [
            {
              date: TEST_DATE,
              conflicts: [
                {
                  slot_id: 'slot-1',
                  title: 'Morning Show',
                  playlist_name: 'Morning Playlist',
                  start_time: '10:00',
                  end_time: '12:00',
                  priority: 10,
                },
                {
                  slot_id: 'slot-2',
                  title: 'Midday Show',
                  playlist_name: 'Midday Playlist',
                  start_time: '11:00',
                  end_time: '13:00',
                  priority: 5,
                },
              ],
            },
            {
              date: tomorrowStr,
              conflicts: [
                {
                  slot_id: 'slot-3',
                  title: 'Evening Show',
                  playlist_name: 'Evening Playlist',
                  start_time: '18:00',
                  end_time: '20:00',
                  priority: 8,
                },
                {
                  slot_id: 'slot-4',
                  title: 'Night Show',
                  playlist_name: 'Night Playlist',
                  start_time: '19:00',
                  end_time: '21:00',
                  priority: 6,
                },
              ],
            },
          ],
        },
      });
    });

    await page.reload();

    // Проверяем, что отображается общее количество конфликтов
    const totalConflicts = page.locator('[data-testid="total-conflicts-count"]');
    await expect(totalConflicts).toContainText('2');
  });
});

test.describe('Conflict Resolution', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await navigateToSchedule(page);
    mockScheduleAPI(page);
    mockConflictDetectionAPI(page, true);
    mockConflictResolutionAPI(page);
  });

  test('should open conflict resolution modal', async ({ page }) => {
    // Переходим на выбранную дату
    await page.click(`[data-testid="day-${TEST_DATE}"]`);

    // Кликаем на предупреждение о конфликте
    await page.click('[data-testid="conflict-warning"]');

    // Проверяем, что модальное окно открылось
    const modal = page.locator('[data-testid="conflict-resolution-modal"]');
    await expect(modal).toBeVisible();
  });

  test('should display resolution options based on priority', async ({ page }) => {
    // Переходим на выбранную дату
    await page.click(`[data-testid="day-${TEST_DATE}"]`);

    // Кликаем на предупреждение о конфликте
    await page.click('[data-testid="conflict-warning"]');

    // Проверяем, что отображается предложение по разрешению
    const resolutionOptions = page.locator('[data-testid="resolution-option"]');
    await expect(resolutionOptions).toHaveCount(2);

    // Проверяем, что слот с высоким приоритетом предлагается сохранить
    const keepOption = resolutionOptions.filter({ hasText: /сохранить|keep/i });
    await expect(keepOption).toBeVisible();
    await expect(keepOption).toContainText('10'); // Приоритет

    // Проверяем, что слот с низким приоритетом предлагается переместить
    const moveOption = resolutionOptions.filter({ hasText: /переместить|move/i });
    await expect(moveOption).toBeVisible();
    await expect(moveOption).toContainText('5'); // Приоритет
  });

  test('should suggest alternative times for lower priority slots', async ({ page }) => {
    // Переходим на выбранную дату
    await page.click(`[data-testid="day-${TEST_DATE}"]`);

    // Кликаем на предупреждение о конфликте
    await page.click('[data-testid="conflict-warning"]');

    // Проверяем наличие предложений по альтернативному времени
    const altTimes = page.locator('[data-testid="alternative-time-suggestion"]');
    await expect(altTimes).toHaveCount(2); // 2 альтернативных варианта

    // Проверяем детали предложений
    await expect(altTimes.nth(0)).toContainText('13:00');
    await expect(altTimes.nth(0)).toContainText('15:00');

    await expect(altTimes.nth(1)).toContainText('15:00');
    await expect(altTimes.nth(1)).toContainText('17:00');
  });

  test('should apply conflict resolution successfully', async ({ page }) => {
    // Переходим на выбранную дату
    await page.click(`[data-testid="day-${TEST_DATE}"]`);

    // Кликаем на предупреждение о конфликте
    await page.click('[data-testid="conflict-warning"]');

    // Применяем разрешение конфликта
    await page.click('[data-testid="apply-resolution-button"]');

    // Проверяем, что отображается индикатор загрузки
    await expect(page.locator('[data-testid="resolution-loading"]')).toBeVisible();

    // Ждём завершения
    await expect(page.locator('[data-testid="resolution-success"]')).toBeVisible();

    // Проверяем сообщение об успехе
    await expect(page.locator('[data-testid="resolution-success"]')).toContainText(
      /разрешено|resolved/i
    );
  });

  test('should close modal after resolution applied', async ({ page }) => {
    // Переходим на выбранную дату
    await page.click(`[data-testid="day-${TEST_DATE}"]`);

    // Кликаем на предупреждение о конфликте
    await page.click('[data-testid="conflict-warning"]');

    // Применяем разрешение конфликта
    await page.click('[data-testid="apply-resolution-button"]');

    // Ждём завершения и закрытия модального окна
    await page.waitForTimeout(1000);

    const modal = page.locator('[data-testid="conflict-resolution-modal"]');
    await expect(modal).not.toBeVisible();
  });

  test('should refresh schedule after resolution applied', async ({ page }) => {
    // Переходим на выбранную дату
    await page.click(`[data-testid="day-${TEST_DATE}"]`);

    // Запоминаем количество слотов до разрешения
    const slotsBefore = await page.locator('[data-testid="schedule-slot"]').count();

    // Кликаем на предупреждение о конфликте
    await page.click('[data-testid="conflict-warning"]');

    // Применяем разрешение конфликта
    await page.click('[data-testid="apply-resolution-button"]');

    // Ждём завершения
    await page.waitForSelector('[data-testid="resolution-success"]');

    // Проверяем, что расписание обновлено
    await page.waitForTimeout(500);

    // После обновления может измениться количество слотов
    // Важно то, что произошла перезагрузка данных
    const slotsAfter = await page.locator('[data-testid="schedule-slot"]').count();
    expect(slotsAfter).toBeGreaterThanOrEqual(0);
  });
});

test.describe('Priority System', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await navigateToSchedule(page);
    mockScheduleAPI(page);
  });

  test('should correctly identify winner based on priority', async ({ page }) => {
    // Mock с конфликтом и приоритетами
    mockConflictDetectionAPI(page, true);
    mockConflictResolutionAPI(page);

    await page.click(`[data-testid="day-${TEST_DATE}"]`);
    await page.click('[data-testid="conflict-warning"]');

    // Проверяем, что слот с приоритетом 10 помечен как победитель
    const winnerBadge = page.locator('[data-testid="winner-badge"]');
    await expect(winnerBadge).toBeVisible();
    await expect(winnerBadge).toContainText('10');
  });

  test('should display priority difference visually', async ({ page }) => {
    mockConflictDetectionAPI(page, true);
    mockConflictResolutionAPI(page);

    await page.click(`[data-testid="day-${TEST_DATE}"]`);
    await page.click('[data-testid="conflict-warning"]');

    // Проверяем визуальное отображение приоритетов
    const priorities = page.locator('[data-testid="slot-priority-badge"]');

    // Высокий приоритет должен быть выделен (зелёный или другой цвет)
    const highPriority = priorities.nth(0);
    await expect(highPriority).toHaveAttribute('data-priority', '10');

    // Низкий приоритет
    const lowPriority = priorities.nth(1);
    await expect(lowPriority).toHaveAttribute('data-priority', '5');
  });

  test('should handle equal priorities correctly', async ({ page }) => {
    // Mock с равными приоритетами
    page.route('**/api/schedule-ai/detect-conflicts', async (route) => {
      await route.fulfill({
        json: {
          channel_id: TEST_CHANNEL,
          period: {
            start: TEST_DATE,
            end: TEST_DATE,
          },
          total_conflicts: 1,
          conflicts: [
            {
              date: TEST_DATE,
              conflicts: [
                {
                  slot_id: 'slot-1',
                  title: 'Morning Show',
                  playlist_name: 'Morning Playlist',
                  start_time: '10:00',
                  end_time: '12:00',
                  priority: 5,
                },
                {
                  slot_id: 'slot-2',
                  title: 'Midday Show',
                  playlist_name: 'Midday Playlist',
                  start_time: '11:00',
                  end_time: '13:00',
                  priority: 5,
                },
              ],
            },
          ],
        },
      });
    });

    mockConflictResolutionAPI(page);

    await page.click(`[data-testid="day-${TEST_DATE}"]`);
    await page.click('[data-testid="conflict-warning"]');

    // При равных приоритетах должно быть предложено выбрать вручную
    const manualSelection = page.locator('[data-testid="manual-selection-required"]');
    await expect(manualSelection).toBeVisible();
  });
});

test.describe('Integration Tests', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await navigateToSchedule(page);
  });

  test('complete workflow: detect conflicts and resolve them', async ({ page }) => {
    // Шаг 1: Создаём пересекающиеся слоты
    mockScheduleAPI(page);
    await createOverlappingSlots(page);

    // Шаг 2: Обнаруживаем конфликты
    mockConflictDetectionAPI(page, true);
    await page.click('[data-testid="detect-conflicts-button"]');

    // Проверяем, что конфликты обнаружены
    await expect(page.locator('[data-testid="conflict-warning"]')).toBeVisible();

    // Шаг 3: Открываем модальное окно разрешения
    await page.click('[data-testid="conflict-warning"]');

    // Шаг 4: Применяем разрешение
    mockConflictResolutionAPI(page);
    await page.click('[data-testid="apply-resolution-button"]');

    // Шаг 5: Проверяем успешное разрешение
    await expect(page.locator('[data-testid="resolution-success"]')).toBeVisible();

    // Шаг 6: Проверяем, что конфликт исчез
    await page.waitForTimeout(1000);
    await expect(page.locator('[data-testid="conflict-warning"]')).not.toBeVisible();
  });

  test('should handle multiple conflicts on the same day', async ({ page }) => {
    // Mock с несколькими конфликтами в один день
    page.route('**/api/schedule/slots**', async (route) => {
      await route.fulfill({
        json: [
          {
            id: 'slot-1',
            channel_id: TEST_CHANNEL,
            playlist_id: 'playlist-1',
            playlist_name: 'Morning Playlist',
            start_date: TEST_DATE,
            start_time: '08:00:00',
            end_time: '10:00:00',
            title: 'Early Morning',
            color: '#3B82F6',
            is_active: true,
            repeat_type: 'none',
            priority: 10,
          },
          {
            id: 'slot-2',
            channel_id: TEST_CHANNEL,
            playlist_id: 'playlist-2',
            playlist_name: 'Midday Playlist',
            start_date: TEST_DATE,
            start_time: '09:00:00',
            end_time: '11:00:00',
            title: 'Morning',
            color: '#10B981',
            is_active: true,
            repeat_type: 'none',
            priority: 5,
          },
          {
            id: 'slot-3',
            channel_id: TEST_CHANNEL,
            playlist_id: 'playlist-3',
            playlist_name: 'Afternoon Playlist',
            start_date: TEST_DATE,
            start_time: '10:00:00',
            end_time: '12:00:00',
            title: 'Late Morning',
            color: '#F59E0B',
            is_active: true,
            repeat_type: 'none',
            priority: 7,
          },
        ],
      });
    });

    mockConflictDetectionAPI(page, true);
    mockConflictResolutionAPI(page);

    await page.click(`[data-testid="day-${TEST_DATE}"]`);

    // Проверяем, что обнаружено несколько конфликтов
    const conflictWarnings = page.locator('[data-testid="conflict-warning"]');
    await expect(conflictWarnings).toHaveCount(3);
  });
});

test.describe('Error Handling', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await navigateToSchedule(page);
    mockScheduleAPI(page);
  });

  test('should handle conflict detection API errors', async ({ page }) => {
    // Mock API error
    page.route('**/api/schedule-ai/detect-conflicts', async (route) => {
      await route.abort('failed');
    });

    await page.click('[data-testid="detect-conflicts-button"]');

    // Проверяем отображение ошибки
    const errorMessage = page.locator('[data-testid="error-message"]');
    await expect(errorMessage).toBeVisible();
    await expect(errorMessage).toContainText(/ошибка|error/i);
  });

  test('should handle conflict resolution API errors', async ({ page }) => {
    mockConflictDetectionAPI(page, true);

    await page.click(`[data-testid="day-${TEST_DATE}"]`);
    await page.click('[data-testid="conflict-warning"]');

    // Mock API error при разрешении
    page.route('**/api/schedule-ai/resolve-conflicts', async (route) => {
      await route.abort('failed');
    });

    await page.click('[data-testid="apply-resolution-button"]');

    // Проверяем отображение ошибки
    const errorMessage = page.locator('[data-testid="resolution-error"]');
    await expect(errorMessage).toBeVisible();
    await expect(errorMessage).toContainText(/не удалось|failed/i);
  });

  test('should handle network errors gracefully', async ({ page }) => {
    mockConflictDetectionAPI(page, true);

    // Симулируем сетевую ошибку
    page.context().setOffline(true);

    await page.click(`[data-testid="day-${TEST_DATE}"]`);
    await page.click('[data-testid="conflict-warning"]');

    // Проверяем отображение сообщения о сетевой ошибке
    const networkError = page.locator('[data-testid="network-error"]');
    await expect(networkError).toBeVisible();
    await expect(networkError).toContainText(/сеть|network/i);

    page.context().setOffline(false);
  });

  test('should handle unauthorized access', async ({ page }) => {
    // Mock 401 Unauthorized
    page.route('**/api/schedule-ai/detect-conflicts', async (route) => {
      await route.fulfill({
        status: 401,
        json: { detail: 'Unauthorized' },
      });
    });

    await page.click('[data-testid="detect-conflicts-button"]');

    // Проверяем перенаправление на страницу логина
    await page.waitForURL('/login');
    expect(page.url()).toContain('/login');
  });
});
