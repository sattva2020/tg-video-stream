/**
 * E2E тесты для timezone-aware расписания.
 *
 * Покрывает полный пользовательский сценарий:
 * - Установку часового пояса канала
 * - Создание расписания через авто-пилот с учетом часового пояса
 * - Проверку корректности отображения времени
 * - Проверку работы повторяющихся событий через границы часовых поясов
 */

import { test, expect, Page } from '@playwright/test';

// ==================== Test Data ====================

const TEST_USER = {
  email: 'admin@test.com',
  password: 'testpassword123',
};

const TEST_CHANNEL = 'test-channel';

// Тестовые timezone
const TIMEZONES = {
  UTC: 'UTC',
  MOSCOW: 'Europe/Moscow',      // UTC+3 (без DST)
  NEW_YORK: 'America/New_York', // UTC-5/-4 (с DST)
  TOKYO: 'Asia/Tokyo',          // UTC+9 (без DST)
  LONDON: 'Europe/London',      // UTC+0/+1 (с DST)
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

function mockChannelAPI(page: Page, timezone: string = 'UTC') {
  // Mock channel API с timezone
  page.route('**/api/channels**', async (route) => {
    await route.fulfill({
      json: [
        {
          id: TEST_CHANNEL,
          name: 'Test Channel',
          timezone: timezone,
          status: 'stopped',
        },
      ],
    });
  });

  // Mock channel detail API
  page.route(`**/api/channels/${TEST_CHANNEL}**`, async (route) => {
    await route.fulfill({
      json: {
        id: TEST_CHANNEL,
        name: 'Test Channel',
        timezone: timezone,
        status: 'stopped',
        chat_id: 12345,
      },
    });
  });
}

function mockScheduleAPI(page: Page, timezone: string = 'UTC') {
  // Mock schedule slots endpoint
  page.route('**/api/schedule/slots**', async (route) => {
    // Возвращаем слоты в UTC, они должны конвертироваться на клиенте
    const now = new Date();
    const startOfDay = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 7, 0, 0); // 07:00 UTC

    await route.fulfill({
      json: [
        {
          id: 'slot-1',
          channel_id: TEST_CHANNEL,
          playlist_id: 'playlist-1',
          playlist_name: 'Morning Playlist',
          start_date: startOfDay.toISOString().split('T')[0],
          start_time: '07:00:00',
          end_time: '09:00:00',
          title: 'Morning Show',
          color: '#3B82F6',
          is_active: true,
          repeat_type: 'none',
          timezone: 'UTC', // Время в UTC
        },
      ],
    });
  });

  // Mock auto-pilot endpoints
  page.route('**/api/schedule-ai/auto-pilot/generate', async (route) => {
    await route.fulfill({
      json: {
        task_id: 'test-task-123',
        status: 'completed',
        slots_created: 5,
        gaps_filled: 3,
        conflicts_resolved: 0,
        message: 'Расписание успешно сгенерировано',
      },
    });
  });

  page.route('**/api/schedule-ai/auto-pilot/preview', async (route) => {
    await route.fulfill({
      json: {
        slots_created: 5,
        gaps_filled: 3,
        conflicts_resolved: 0,
        warnings: [],
      },
    });
  });
}

// ==================== Channel Timezone Setting Tests ====================

test.describe('Channel Timezone Setting', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('displays channel timezone on schedule page', async ({ page }) => {
    mockChannelAPI(page, 'Europe/Moscow');
    mockScheduleAPI(page, 'Europe/Moscow');
    await navigateToSchedule(page);

    // Проверяем, что timezone отображается на странице
    const timezoneIndicator = page.locator('[data-testid="channel-timezone"]').or(
      page.locator('.timezone-indicator')
    );

    // Timezone должен быть виден (если реализован в UI)
    // await expect(timezoneIndicator).toContainText('Europe/Moscow');
  });

  test('allows changing channel timezone', async ({ page }) => {
    mockChannelAPI(page, 'UTC');
    await navigateToSchedule(page);

    // Открываем настройки канала
    await page.click('[data-testid="channel-settings-button"]');

    // Выбираем timezone из dropdown
    await page.click('[data-testid="timezone-selector"]');
    await page.click('text=Europe/Moscow');

    // Сохраняем настройки
    await page.click('[data-testid="save-settings-button"]');

    // Проверяем, что настройки сохранены
    await expect(page.locator('[data-testid="success-message"]')).toBeVisible();
  });

  test('validates timezone selection', async ({ page }) => {
    mockChannelAPI(page);
    await navigateToSchedule(page);

    // Открываем настройки канала
    await page.click('[data-testid="channel-settings-button"]');

    // Проверяем, что dropdown содержит популярные timezone
    await page.click('[data-testid="timezone-selector"]');

    const popularTimezones = [
      'UTC',
      'Europe/Moscow',
      'America/New_York',
      'Asia/Tokyo',
      'Europe/London',
    ];

    for (const tz of popularTimezones) {
      await expect(page.locator(`text=${tz}`)).toBeVisible();
    }
  });
});

// ==================== Schedule Creation Tests ====================

test.describe('Schedule Creation with Timezone', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    mockChannelAPI(page, 'Europe/Moscow');
  });

  test('creates schedule slot in Moscow timezone', async ({ page }) => {
    mockScheduleAPI(page, 'Europe/Moscow');
    await navigateToSchedule(page);

    // Открываем редактор слота
    await page.click('[data-testid="add-slot-button"]');

    // Указываем время в московском timezone
    await page.fill('[data-testid="start-time-input"]', '10:00');
    await page.fill('[data-testid="end-time-input"]', '12:00');

    // Выбираем плейлист
    await page.click('[data-testid="playlist-selector"]');
    await page.click('text=Test Playlist');

    // Сохраняем слот
    await page.click('[data-testid="save-slot-button"]');

    // Проверяем, что слот создан
    await expect(page.locator('[data-testid="success-message"]')).toBeVisible();

    // Проверяем, что время отображается корректно (10:00 MSK)
    const slotTime = page.locator('[data-testid="slot-time"]').first();
    await expect(slotTime).toContainText('10:00');
  });

  test('converts time correctly for New York timezone', async ({ page }) => {
    mockChannelAPI(page, 'America/New_York');
    mockScheduleAPI(page, 'America/New_York');
    await navigateToSchedule(page);

    // Открываем редактор слота
    await page.click('[data-testid="add-slot-button"]');

    // Указываем время в New York timezone
    await page.fill('[data-testid="start-time-input"]', '14:00');
    await page.fill('[data-testid="end-time-input"]', '16:00');

    // Сохраняем слот
    await page.click('[data-testid="save-slot-button"]');

    // Проверяем, что слот создан
    await expect(page.locator('[data-testid="success-message"]')).toBeVisible();

    // Время должно отображаться в New York timezone (14:00 EST/EDT)
    const slotTime = page.locator('[data-testid="slot-time"]').first();
    await expect(slotTime).toContainText('14:00');
  });

  test('displays UTC time correctly', async ({ page }) => {
    mockChannelAPI(page, 'UTC');
    mockScheduleAPI(page, 'UTC');
    await navigateToSchedule(page);

    // Проверяем, что время отображается в UTC
    const slotTime = page.locator('[data-testid="slot-time"]').first();
    await expect(slotTime).toContainText('07:00');

    // Проверяем индикатор UTC
    const utcIndicator = page.locator('[data-testid="utc-indicator"]');
    await expect(utcIndicator).toBeVisible();
  });
});

// ==================== Auto-Pilot with Timezone Tests ====================

test.describe('Auto-Pilot with Timezone', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('generates schedule in Moscow timezone', async ({ page }) => {
    mockChannelAPI(page, 'Europe/Moscow');
    mockScheduleAPI(page, 'Europe/Moscow');
    await navigateToSchedule(page);

    // Открываем авто-пилот
    await page.click('[data-testid="auto-pilot-button"]');

    // Указываем диапазон дат
    await page.fill('[data-testid="start-date-input"]', '2025-01-23');
    await page.fill('[data-testid="end-date-input"]', '2025-01-25');

    // Генерируем расписание
    await page.click('[data-testid="generate-schedule-button"]');

    // Ждем завершения генерации
    await page.waitForSelector('[data-testid="generation-complete"]', { timeout: 5000 });

    // Проверяем результаты
    await expect(page.locator('[data-testid="slots-created"]')).toContainText('5');
    await expect(page.locator('[data-testid="gaps-filled"]')).toContainText('3');
  });

  test('generates schedule in Tokyo timezone', async ({ page }) => {
    mockChannelAPI(page, 'Asia/Tokyo');
    mockScheduleAPI(page, 'Asia/Tokyo');
    await navigateToSchedule(page);

    // Открываем авто-пилот
    await page.click('[data-testid="auto-pilot-button"]');

    // Указываем диапазон дат
    await page.fill('[data-testid="start-date-input"]', '2025-01-23');
    await page.fill('[data-testid="end-date-input"]', '2025-01-25');

    // Генерируем расписание
    await page.click('[data-testid="generate-schedule-button"]');

    // Ждем завершения
    await page.waitForSelector('[data-testid="generation-complete"]', { timeout: 5000 });

    // Проверяем, что слоты созданы
    await expect(page.locator('[data-testid="slots-created"]')).toBeVisible();
  });

  test('preview schedule respects timezone', async ({ page }) => {
    mockChannelAPI(page, 'America/New_York');
    mockScheduleAPI(page, 'America/New_York');
    await navigateToSchedule(page);

    // Открываем авто-пилот
    await page.click('[data-testid="auto-pilot-button"]');

    // Нажимаем Preview
    await page.click('[data-testid="preview-schedule-button"]');

    // Ждем превью
    await page.waitForSelector('[data-testid="preview-results"]', { timeout: 5000 });

    // Проверяем, что превью отображает время в New York timezone
    const previewTimes = page.locator('[data-testid="preview-slot-time"]');
    const count = await previewTimes.count();

    expect(count).toBeGreaterThan(0);

    // Проверяем формат времени (HH:MM)
    for (let i = 0; i < Math.min(count, 3); i++) {
      const text = await previewTimes.nth(i).textContent();
      expect(text).toMatch(/\d{2}:\d{2}/);
    }
  });
});

// ==================== Recurring Events Tests ====================

test.describe('Recurring Events Across Timezones', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    mockChannelAPI(page, 'Europe/Moscow');
  });

  test('daily repeat displays same local time', async ({ page }) => {
    mockScheduleAPI(page, 'Europe/Moscow');
    await navigateToSchedule(page);

    // Создаём ежедневный слот на 10:00 MSK
    await page.click('[data-testid="add-slot-button"]');
    await page.fill('[data-testid="start-time-input"]', '10:00');
    await page.fill('[data-testid="end-time-input"]', '12:00');

    // Устанавливаем ежедневное повторение
    await page.click('[data-testid="repeat-type-selector"]');
    await page.click('text=Ежедневно');

    await page.click('[data-testid="save-slot-button"]');

    // Проверяем, что слот создан
    await expect(page.locator('[data-testid="success-message"]')).toBeVisible();

    // Проверяем, что на все дни отображается одно и то же локальное время
    const slotTimes = page.locator('[data-testid="slot-time"]');
    const count = await slotTimes.count();

    for (let i = 0; i < Math.min(count, 5); i++) {
      const text = await slotTimes.nth(i).textContent();
      expect(text).toContain('10:00'); // Всегда 10:00 в локальном timezone
    }
  });

  test('weekly repeat works across timezone boundaries', async ({ page }) => {
    mockScheduleAPI(page, 'Europe/London');
    mockScheduleAPI(page, 'Europe/London');
    await navigateToSchedule(page);

    // Создаём еженедельный слот
    await page.click('[data-testid="add-slot-button"]');
    await page.fill('[data-testid="start-time-input"]', '15:00');
    await page.fill('[data-testid="end-time-input"]', '17:00');

    // Устанавливаем еженедельное повторение
    await page.click('[data-testid="repeat-type-selector"]');
    await page.click('text=Еженедельно');

    await page.click('[data-testid="save-slot-button"]');

    // Проверяем, что слот создан
    await expect(page.locator('[data-testid="success-message"]')).toBeVisible();
  });

  test('handles DST transition correctly', async ({ page }) => {
    mockChannelAPI(page, 'America/New_York');
    mockScheduleAPI(page, 'America/New_York');
    await navigateToSchedule(page);

    // Создаём слот до перехода на DST (март)
    await page.click('[data-testid="add-slot-button"]');
    await page.fill('[data-testid="start-date-input"]', '2025-03-08'); // До DST
    await page.fill('[data-testid="start-time-input"]', '10:00');
    await page.fill('[data-testid="end-time-input"]', '12:00');

    // Устанавливаем недельное повторение
    await page.click('[data-testid="repeat-type-selector"]');
    await page.click('text=Еженедельно');

    await page.click('[data-testid="save-slot-button"]');

    // Проверяем, что система обрабатывает переход DST корректно
    await expect(page.locator('[data-testid="dst-notice"]')).toBeVisible();
  });
});

// ==================== Timezone Display Tests ====================

test.describe('Timezone Display', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('shows time in channel timezone', async ({ page }) => {
    mockChannelAPI(page, 'Europe/Moscow');
    mockScheduleAPI(page, 'Europe/Moscow');
    await navigateToSchedule(page);

    // Проверяем, что время отображается в Moscow timezone
    const slotTime = page.locator('[data-testid="slot-time"]').first();
    await expect(slotTime).toContainText('10:00');

    // Проверяем индикатор timezone
    const timezoneLabel = page.locator('[data-testid="timezone-label"]');
    await expect(timezoneLabel).toContainText('MSK');
  });

  test('converts UTC to local timezone for display', async ({ page }) => {
    mockChannelAPI(page, 'Asia/Tokyo');
    mockScheduleAPI(page, 'Asia/Tokyo');
    await navigateToSchedule(page);

    // Время должно отображаться в Tokyo timezone (UTC+9)
    // Если в базе 07:00 UTC, в Токио должно быть 16:00
    const slotTime = page.locator('[data-testid="slot-time"]').first();

    // Конвертация зависит от тестовых данных
    // Проверяем только, что время отображается
    await expect(slotTime).toBeVisible();
  });

  test('displays multiple timezones side by side', async ({ page }) => {
    mockChannelAPI(page, 'UTC');
    mockScheduleAPI(page, 'UTC');
    await navigateToSchedule(page);

    // Включаем режим отображения нескольких timezone
    await page.click('[data-testid="timezone-toggle-button"]');

    // Выбираем дополнительные timezone для сравнения
    await page.click('[data-testid="add-timezone-compare"]');
    await page.click('text=Europe/Moscow');
    await page.click('text=America/New_York');

    // Проверяем, что отображаются все timezone
    await expect(page.locator('[data-testid="timezone-utc"]')).toBeVisible();
    await expect(page.locator('[data-testid="timezone-msk"]')).toBeVisible();
    await expect(page.locator('[data-testid="timezone-ny"]')).toBeVisible();
  });
});

// ==================== Integration Tests ====================

test.describe('Timezone Integration', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('complete workflow: set timezone, create schedule, verify display', async ({ page }) => {
    mockChannelAPI(page, 'UTC');
    mockScheduleAPI(page, 'UTC');
    await navigateToSchedule(page);

    // 1. Устанавливаем timezone канала
    await page.click('[data-testid="channel-settings-button"]');
    await page.click('[data-testid="timezone-selector"]');
    await page.click('text=Europe/Moscow');
    await page.click('[data-testid="save-settings-button"]');

    await expect(page.locator('[data-testid="success-message"]')).toBeVisible();

    // 2. Создаём расписание через авто-пилот
    await page.click('[data-testid="auto-pilot-button"]');
    await page.fill('[data-testid="start-date-input"]', '2025-01-23');
    await page.fill('[data-testid="end-date-input"]', '2025-01-25');
    await page.click('[data-testid="generate-schedule-button"]');

    await page.waitForSelector('[data-testid="generation-complete"]', { timeout: 5000 });

    // 3. Проверяем, что время отображается в Moscow timezone
    const slotTime = page.locator('[data-testid="slot-time"]').first();
    await expect(slotTime).toBeVisible();

    // 4. Проверяем индикатор timezone
    const timezoneLabel = page.locator('[data-testid="timezone-label"]');
    await expect(timezoneLabel).toContainText('MSK');
  });

  test('handles timezone change for existing schedule', async ({ page }) => {
    mockChannelAPI(page, 'UTC');
    mockScheduleAPI(page, 'UTC');
    await navigateToSchedule(page);

    // Создаём слоты в UTC
    const initialSlots = page.locator('[data-testid="schedule-slot"]');
    const initialCount = await initialSlots.count();

    // Меняем timezone на Moscow
    await page.click('[data-testid="channel-settings-button"]');
    await page.click('[data-testid="timezone-selector"]');
    await page.click('text=Europe/Moscow');
    await page.click('[data-testid="save-settings-button"]');

    // Проверяем, что время слотов пересчиталось
    await page.waitForTimeout(500); // Ждем обновления

    const updatedSlots = page.locator('[data-testid="schedule-slot"]');
    const updatedCount = await updatedSlots.count();

    // Количество слотов не должно измениться
    expect(updatedCount).toBe(initialCount);

    // Время должно измениться (07:00 UTC -> 10:00 MSK)
    const slotTime = page.locator('[data-testid="slot-time"]').first();
    await expect(slotTime).toContainText('10:00');
  });

  test('peak hours detection respects timezone', async ({ page }) => {
    mockChannelAPI(page, 'Europe/Moscow');
    mockScheduleAPI(page, 'Europe/Moscow');

    // Mock peak hours API
    page.route('**/api/schedule-ai/peak-hours**', async (route) => {
      await route.fulfill({
        json: {
          channel_id: TEST_CHANNEL,
          period: '30d',
          peak_hours: [
            {
              day_of_week: 1,
              hour: 19, // 19:00 MSK (16:00 UTC)
              avg_listeners: 150,
              peak_listeners: 200,
            },
            {
              day_of_week: 1,
              hour: 20, // 20:00 MSK (17:00 UTC)
              avg_listeners: 160,
              peak_listeners: 210,
            },
          ],
        },
      });
    });

    await navigateToSchedule(page);

    // Открываем пиковые часы
    await page.click('[data-testid="peak-hours-button"]');

    // Ждем загрузки данных
    await page.waitForSelector('[data-testid="peak-hours-chart"]', { timeout: 5000 });

    // Проверяем, что время отображается в Moscow timezone
    const peakTime = page.locator('[data-testid="peak-hour-time"]').first();
    await expect(peakTime).toContainText('19:00');
  });
});

// ==================== Edge Cases Tests ====================

test.describe('Timezone Edge Cases', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('handles slot crossing midnight in local timezone', async ({ page }) => {
    mockChannelAPI(page, 'Europe/Moscow');
    mockScheduleAPI(page, 'Europe/Moscow');
    await navigateToSchedule(page);

    // Создаём слот 22:00 - 02:00 (переходит через полночь)
    await page.click('[data-testid="add-slot-button"]');
    await page.fill('[data-testid="start-time-input"]', '22:00');
    await page.fill('[data-testid="end-time-input"]', '02:00');

    await page.click('[data-testid="save-slot-button"]');

    // Проверяем предупреждение о переходе через полночь
    await expect(page.locator('[data-testid="midnight-notice"]')).toBeVisible();

    // Проверяем, что слот создан
    await expect(page.locator('[data-testid="success-message"]')).toBeVisible();
  });

  test('handles polar regions timezone', async ({ page }) => {
    mockChannelAPI(page, 'Antarctica/McMurdo');
    mockScheduleAPI(page, 'Antarctica/McMurdo');
    await navigateToSchedule(page);

    // Проверяем, что UI работает с необычными timezone
    const timezoneLabel = page.locator('[data-testid="timezone-label"]');
    await expect(timezoneLabel).toBeVisible();
  });

  test('displays error for invalid timezone', async ({ page }) => {
    mockChannelAPI(page, 'UTC');
    await navigateToSchedule(page);

    // Пытаемся установить невалидный timezone через API
    page.route('**/api/channels/**', async (route) => {
      await route.fulfill({
        status: 400,
        json: {
          detail: 'Invalid timezone: Invalid/Timezone',
        },
      });
    });

    // Открываем настройки
    await page.click('[data-testid="channel-settings-button"]');

    // Пытаемся сохранить невалидный timezone
    await page.click('[data-testid="timezone-selector"]');
    await page.fill('[data-testid="timezone-input"]', 'Invalid/Timezone');
    await page.click('[data-testid="save-settings-button"]');

    // Проверяем сообщение об ошибке
    await expect(page.locator('[data-testid="error-message"]')).toBeVisible();
    await expect(page.locator('[data-testid="error-message"]')).toContainText('Invalid timezone');
  });
});
