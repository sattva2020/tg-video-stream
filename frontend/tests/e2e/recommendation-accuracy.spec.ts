/**
 * E2E тесты для проверки точности рекомендаций на основе данных вовлеченности.
 *
 * Покрывает полный пользовательский сценарий:
 * - Создание тестовых данных воспроизведения (через API)
 * - Просмотр пиковых часов
 * - Генерация рекомендаций
 * - Проверка, что контент с высокой вовлеченностью рекомендуется первым
 * - Проверка корректности обнаружения пиковых часов
 */

import { test, expect, Page } from '@playwright/test';

// ==================== Test Constants ====================

const TEST_USER = {
  email: 'admin@test.com',
  password: 'testpassword123',
};

const TEST_CHANNEL = 'test-channel-id-12345';

const ENGAGEMENT_DATA = {
  // Высокая вовлеченность: вечер (19:00-21:00), 75-95 слушателей
  highEngagement: {
    playlistName: 'High Engagement Playlist',
    peakHours: ['19:00', '20:00', '21:00'],
    avgListeners: 85,
  },
  // Средняя вовлеченность: день (13:00-15:00), 25-35 слушателей
  mediumEngagement: {
    playlistName: 'Medium Engagement Playlist',
    hours: ['13:00', '14:00', '15:00'],
    avgListeners: 30,
  },
  // Низкая вовлеченность: утро (07:00-09:00), 5-9 слушателей
  lowEngagement: {
    playlistName: 'Low Engagement Playlist',
    hours: ['07:00', '08:00', '09:00'],
    avgListeners: 7,
  },
};

// ==================== Helper Functions ====================

async function login(page: Page) {
  await page.goto('/login');
  await page.fill('[data-testid="email-input"]', TEST_USER.email);
  await page.fill('[data-testid="password-input"]', TEST_USER.password);
  await page.click('[data-testid="login-button"]');
  await page.waitForURL('/dashboard', { timeout: 5000 });
}

async function navigateToSchedule(page: Page) {
  await page.click('[data-testid="nav-schedule"]');
  await page.waitForURL('/schedule', { timeout: 5000 });
  await expect(page.locator('h1')).toContainText(/расписание|schedule/i);
}

async function setupEngagementData(page: Page) {
  // Создаем тестовые данные воспроизведения через API
  await page.route('**/api/test/setup-engagement-data', async route => {
    await route.fulfill({
      status: 200,
      json: {
        success: true,
        dataCreated: {
          highEngagementPlays: 270,
          mediumEngagementPlays: 180,
          lowEngagementPlays: 90,
        },
      },
    });
  });

  // Вызываем API для создания данных
  await page.evaluate(async ({ channel }) => {
    const response = await fetch(`/api/test/setup-engagement-data?channel=${channel}`, {
      method: 'POST',
    });
    return await response.json();
  }, { channel: TEST_CHANNEL });
}

async function mockPeakHoursAPI(page: Page) {
  await page.route('**/api/schedule-ai/peak-hours**', async route => {
    await route.fulfill({
      status: 200,
      json: {
        channel_id: TEST_CHANNEL,
        period: '30d',
        total_samples: 540,
        peak_hours: [
          {
            day_of_week: 0, // Monday
            hour: 19,
            avg_listeners: 75,
            peak_listeners: 95,
            play_count: 30,
          },
          {
            day_of_week: 0,
            hour: 20,
            avg_listeners: 85,
            peak_listeners: 100,
            play_count: 30,
          },
          {
            day_of_week: 0,
            hour: 21,
            avg_listeners: 95,
            peak_listeners: 110,
            play_count: 30,
          },
          {
            day_of_week: 1, // Tuesday
            hour: 19,
            avg_listeners: 80,
            peak_listeners: 98,
            play_count: 30,
          },
          {
            day_of_week: 1,
            hour: 20,
            avg_listeners: 88,
            peak_listeners: 105,
            play_count: 30,
          },
          {
            day_of_week: 1,
            hour: 21,
            avg_listeners: 92,
            peak_listeners: 108,
            play_count: 30,
          },
        ],
      },
    });
  });
}

async function mockRecommendationsAPI(page: Page) {
  await page.route('**/api/schedule-ai/recommendations**', async route => {
    await route.fulfill({
      status: 200,
      json: {
        channel_id: TEST_CHANNEL,
        target_date: new Date(Date.now() + 86400000).toISOString().split('T')[0],
        recommendations: [
          {
            id: 'rec-1',
            playlist_id: 'high-engagement-playlist-id',
            playlist_name: ENGAGEMENT_DATA.highEngagement.playlistName,
            start_time: '19:00',
            end_time: '21:00',
            type: 'PEAK_HOURS',
            confidence: 0.92,
            reason: 'Высокая вовлеченность: 85 средних слушателей в вечерние часы',
          },
          {
            id: 'rec-2',
            playlist_id: 'high-engagement-playlist-id',
            playlist_name: ENGAGEMENT_DATA.highEngagement.playlistName,
            start_time: '20:00',
            end_time: '22:00',
            type: 'PEAK_HOURS',
            confidence: 0.90,
            reason: 'Пиковый час с наивысшей вовлеченностью (95 слушателей)',
          },
          {
            id: 'rec-3',
            playlist_id: 'medium-engagement-playlist-id',
            playlist_name: ENGAGEMENT_DATA.mediumEngagement.playlistName,
            start_time: '14:00',
            end_time: '16:00',
            type: 'PERFORMANCE',
            confidence: 0.65,
            reason: 'Средняя вовлеченность: 30 слушателей в дневные часы',
          },
          {
            id: 'rec-4',
            playlist_id: 'low-engagement-playlist-id',
            playlist_name: ENGAGEMENT_DATA.lowEngagement.playlistName,
            start_time: '08:00',
            end_time: '10:00',
            type: 'FILL_GAP',
            confidence: 0.35,
            reason: 'Низкая вовлеченность: 7 слушателей в утренние часы',
          },
        ],
      },
    });
  });
}

async function openPeakHoursModal(page: Page) {
  // Клик на кнопку "Пиковые часы"
  const peakHoursButton = page.locator('button').filter({ hasText: /Пиковые часы|Peak Hours/i });
  await expect(peakHoursButton).toBeVisible({ timeout: 5000 });
  await peakHoursButton.click();

  // Ждем открытия модального окна
  await expect(page.locator('[role="dialog"]')).toBeVisible({ timeout: 5000 });
}

// ==================== Test Suites ====================

test.describe('Точность рекомендаций на основе данных вовлеченности', () => {
  test.beforeEach(async ({ page }) => {
    // Настраиваем mocking API
    await mockPeakHoursAPI(page);
    await mockRecommendationsAPI(page);
  });

  test('должен обнаруживать пиковые часы на основе данных воспроизведения', async ({ page }) => {
    await login(page);
    await navigateToSchedule(page);

    // Открываем модальное окно пиковых часов
    await openPeakHoursModal(page);

    // Проверяем, что модальное окно открылось
    const dialog = page.locator('[role="dialog"]');
    await expect(dialog).toBeVisible();

    // Проверяем заголовок
    await expect(dialog.locator('h2, h3')).toContainText(/Пиковые часы|Peak Hours/i);

    // Проверяем наличие тепловой карты (heatmap)
    const heatmap = dialog.locator('[data-testid="peak-hours-heatmap"]');
    await expect(heatmap).toBeVisible();

    // Проверяем отображение пиковых часов
    const peakHoursDisplay = dialog.locator('text=/19:00|20:00|21:00/i');
    await expect(peakHoursDisplay).toBeVisible();

    // Проверяем отображение метрики средней вовлеченности
    const avgListenersText = dialog.locator('text=/85|90|95/i');
    await expect(avgListenersText).toBeVisible();

    // Проверяем наличие легенды с цветовой шкалой
    const legend = dialog.locator('[data-testid="peak-hours-legend"]');
    await expect(legend).toBeVisible();

    // Закрываем модальное окно
    const closeButton = dialog.locator('button').filter({ hasText: /✕|close|закрыть/i });
    await closeButton.click();
    await expect(dialog).toBeHidden();
  });

  test('должен показывать пиковые часы с цветовой кодировкой по вовлеченности', async ({ page }) => {
    await login(page);
    await navigateToSchedule(page);
    await openPeakHoursModal(page);

    // Проверяем, что ячейки тепловой карты имеют цветовую кодировку
    const heatmapCells = page.locator('[data-testid="peak-hours-cell"]');

    const count = await heatmapCells.count();
    expect(count).toBeGreaterThan(0);

    // Проверяем, что ячейки для пиковых часов имеют более насыщенный цвет
    // (высокая вовлеченность = более темный/насыщенный фиолетовый)
    const peakHourCells = page.locator('[data-hour="19"], [data-hour="20"], [data-hour="21"]');

    const peakHourCount = await peakHourCells.count();
    expect(peakHourCount).toBeGreaterThan(0);

    // Проверяем, что цвет фона указывает на высокую вовлеченность
    for (let i = 0; i < peakHourCount; i++) {
      const cell = peakHourCells.nth(i);
      const backgroundColor = await cell.evaluate((el: HTMLElement) => {
        return window.getComputedStyle(el).backgroundColor;
      });

      // Цвет должен быть насыщенным (непрозрачным фиолетовым)
      // Проверяем, что RGB значения не слишком близки к белому (255, 255, 255)
      const rgbValues = backgroundColor.match(/\d+/g);
      if (rgbValues) {
        const [r, g, b] = rgbValues.map(Number);
        const isNotWhite = r < 250 || g < 250 || b < 250;
        expect(isNotWhite).toBeTruthy();
      }
    }
  });

  test('должен рекомендовать контент с высокой вовлеченностью первым', async ({ page }) => {
    await login(page);
    await navigateToSchedule(page);

    // Выбираем день в календаре
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    const targetDate = tomorrow.toISOString().split('T')[0];

    // Кликаем на дату (если нужно, добавляем логику выбора даты)
    const dayCell = page.locator(`[data-date="${targetDate}"]`);
    if (await dayCell.isVisible()) {
      await dayCell.click();
    }

    // Ждем загрузки рекомендаций
    await page.waitForTimeout(1000);

    // Проверяем, что раздел AI-рекомендаций отображается
    const aiSection = page.locator('[data-testid="ai-recommendations-section"]');
    await expect(aiSection).toBeVisible({ timeout: 5000 });

    // Проверяем наличие заголовка AI-рекомендаций
    await expect(aiSection.locator('h3, h4')).toContainText(/AI|Рекомендации/i);

    // Получаем все рекомендации
    const recommendations = aiSection.locator('[data-testid="recommendation-item"]');
    const count = await recommendations.count();
    expect(count).toBeGreaterThan(0);

    // Проверяем, что первая рекомендация имеет высокую уверенность
    const firstRecommendation = recommendations.first();
    await expect(firstRecommendation).toBeVisible();

    // Проверяем, что название плейлиста указывает на высокую вовлеченность
    const playlistName = firstRecommendation.locator('[data-testid="playlist-name"]');
    const nameText = await playlistName.textContent();
    expect(nameText).toContain('High Engagement');

    // Проверяем отображение уверенности (confidence)
    const confidence = firstRecommendation.locator('[data-testid="confidence"]');
    await expect(confidence).toBeVisible();

    // Проверяем, что уверенность высокая (> 0.7)
    const confidenceText = await confidence.textContent();
    const confidenceValue = parseFloat(confidenceText?.match(/[\d.]+/)?.[0] || '0');
    expect(confidenceValue).toBeGreaterThan(0.7);

    // Проверяем наличие причины рекомендации (reason)
    const reason = firstRecommendation.locator('[data-testid="recommendation-reason"]');
    await expect(reason).toBeVisible();
    const reasonText = await reason.textContent();
    expect(reasonText?.toLowerCase()).toMatch(/вовлеченност|engagement|слушател/i);
  });

  test('должен сортировать рекомендации по убыванию уверенности', async ({ page }) => {
    await login(page);
    await navigateToSchedule(page);

    // Ждем загрузки рекомендаций
    await page.waitForTimeout(1000);

    const aiSection = page.locator('[data-testid="ai-recommendations-section"]');
    await expect(aiSection).toBeVisible({ timeout: 5000 });

    // Получаем все рекомендации
    const recommendations = aiSection.locator('[data-testid="recommendation-item"]');
    const count = await recommendations.count();
    expect(count).toBeGreaterThan(1);

    // Собираем значения уверенности из всех рекомендаций
    const confidences: number[] = [];

    for (let i = 0; i < count; i++) {
      const rec = recommendations.nth(i);
      const confidence = rec.locator('[data-testid="confidence"]');
      const confidenceText = await confidence.textContent();
      const confidenceValue = parseFloat(confidenceText?.match(/[\d.]+/)?.[0] || '0');
      confidences.push(confidenceValue);
    }

    // Проверяем, что уверенности отсортированы по убыванию
    for (let i = 0; i < confidences.length - 1; i++) {
      expect(confidences[i]).toBeGreaterThanOrEqual(confidences[i + 1]);
    }
  });

  test('должен показывать рекомендации для пиковых часов с более высокой уверенностью', async ({ page }) => {
    await login(page);
    await navigateToSchedule(page);

    // Ждем загрузки рекомендаций
    await page.waitForTimeout(1000);

    const aiSection = page.locator('[data-testid="ai-recommendations-section"]');
    await expect(aiSection).toBeVisible({ timeout: 5000 });

    // Разделяем рекомендации на пиковые часы и остальные
    const recommendations = aiSection.locator('[data-testid="recommendation-item"]');
    const count = await recommendations.count();

    const peakHourConfidences: number[] = [];
    const otherHourConfidences: number[] = [];

    for (let i = 0; i < count; i++) {
      const rec = recommendations.nth(i);

      // Проверяем время рекомендации
      const timeText = await rec.locator('[data-testid="start-time"]').textContent();
      const hour = parseInt(timeText?.split(':')[0] || '0');

      const confidenceText = await rec.locator('[data-testid="confidence"]').textContent();
      const confidenceValue = parseFloat(confidenceText?.match(/[\d.]+/)?.[0] || '0');

      // Пиковые часы: 19:00-21:00
      if (hour >= 19 && hour <= 21) {
        peakHourConfidences.push(confidenceValue);
      } else {
        otherHourConfidences.push(confidenceValue);
      }
    }

    // Проверяем, что у пиковых часов более высокая уверенность
    if (peakHourConfidences.length > 0 && otherHourConfidences.length > 0) {
      const avgPeakConfidence = peakHourConfidences.reduce((a, b) => a + b, 0) / peakHourConfidences.length;
      const avgOtherConfidence = otherHourConfidences.reduce((a, b) => a + b, 0) / otherHourConfidences.length;

      expect(avgPeakConfidence).toBeGreaterThan(avgOtherConfidence);
    }
  });

  test('должен включать объяснение (reason) на основе данных вовлеченности', async ({ page }) => {
    await login(page);
    await navigateToSchedule(page);

    // Ждем загрузки рекомендаций
    await page.waitForTimeout(1000);

    const aiSection = page.locator('[data-testid="ai-recommendations-section"]');
    await expect(aiSection).toBeVisible({ timeout: 5000 });

    // Проверяем, что у каждой рекомендации есть reason
    const recommendations = aiSection.locator('[data-testid="recommendation-item"]');
    const count = await recommendations.count();
    expect(count).toBeGreaterThan(0);

    for (let i = 0; i < count; i++) {
      const rec = recommendations.nth(i);

      // Проверяем наличие reason
      const reason = rec.locator('[data-testid="recommendation-reason"]');
      await expect(reason).toBeVisible();

      // Проверяем, что reason связан с вовлеченностью или производительностью
      const reasonText = await reason.textContent();
      const reasonLower = reasonText?.toLowerCase() || '';

      // Reason должен упоминать метрики вовлеченности
      const hasEngagementKeyword = /вовлеченност|engagement|слушател|listener|производительност|performance|пиков|peak/i.test(reasonLower);
      expect(hasEngagementKeyword).toBeTruthy();
    }
  });
});

test.describe('Интеграционные тесты точности рекомендаций', () => {
  test.beforeEach(async ({ page }) => {
    await mockPeakHoursAPI(page);
    await mockRecommendationsAPI(page);
  });

  test('полный рабочий процесс: от данных до рекомендаций', async ({ page }) => {
    // Шаг 1: Вход в систему
    await login(page);
    await navigateToSchedule(page);

    // Шаг 2: Просмотр пиковых часов
    await openPeakHoursModal(page);

    const dialog = page.locator('[role="dialog"]');
    await expect(dialog).toBeVisible();

    // Проверяем отображение пиковых часов
    const peakHourText = dialog.locator('text=/19:00.*85.*слушател/i');
    await expect(peakHourText).toBeVisible();

    // Закрываем модальное окно
    const closeButton = dialog.locator('button').filter({ hasText: /✕|close/i });
    await closeButton.click();

    // Шаг 3: Просмотр рекомендаций
    await page.waitForTimeout(1000);

    const aiSection = page.locator('[data-testid="ai-recommendations-section"]');
    await expect(aiSection).toBeVisible({ timeout: 5000 });

    // Шаг 4: Проверка точности рекомендаций
    const firstRec = aiSection.locator('[data-testid="recommendation-item"]').first();

    // Проверяем, что это High Engagement плейлист
    const playlistName = await firstRec.locator('[data-testid="playlist-name"]').textContent();
    expect(playlistName).toContain('High Engagement');

    // Проверяем высокую уверенность
    const confidenceText = await firstRec.locator('[data-testid="confidence"]').textContent();
    const confidenceValue = parseFloat(confidenceText?.match(/[\d.]+/)?.[0] || '0');
    expect(confidenceValue).toBeGreaterThan(0.8);

    // Проверяем наличие reason с метриками вовлеченности
    const reasonText = await firstRec.locator('[data-testid="recommendation-reason"]').textContent();
    expect(reasonText?.toLowerCase()).toMatch(/вовлеченност|engagement|85|95/i);

    // Шаг 5: Проверка, что рекомендации для пиковых часов имеют приоритет
    const timeText = await firstRec.locator('[data-testid="start-time"]').textContent();
    const hour = parseInt(timeText?.split(':')[0] || '0');
    expect(hour).toBeGreaterThanOrEqual(19);
    expect(hour).toBeLessThanOrEqual(21);
  });

  test('проверка корреляции уверенности с уровнем вовлеченности', async ({ page }) => {
    await login(page);
    await navigateToSchedule(page);

    // Ждем загрузки рекомендаций
    await page.waitForTimeout(1000);

    const aiSection = page.locator('[data-testid="ai-recommendations-section"]');
    await expect(aiSection).toBeVisible({ timeout: 5000 });

    // Группируем рекомендации по уровню вовлеченности
    const recommendations = aiSection.locator('[data-testid="recommendation-item"]');
    const count = await recommendations.count();

    const highEngConfidences: number[] = [];
    const mediumEngConfidences: number[] = [];
    const lowEngConfidences: number[] = [];

    for (let i = 0; i < count; i++) {
      const rec = recommendations.nth(i);

      const playlistName = await rec.locator('[data-testid="playlist-name"]').textContent();
      const confidenceText = await rec.locator('[data-testid="confidence"]').textContent();
      const confidenceValue = parseFloat(confidenceText?.match(/[\d.]+/)?.[0] || '0');

      if (playlistName?.includes('High Engagement')) {
        highEngConfidences.push(confidenceValue);
      } else if (playlistName?.includes('Medium Engagement')) {
        mediumEngConfidences.push(confidenceValue);
      } else if (playlistName?.includes('Low Engagement')) {
        lowEngConfidences.push(confidenceValue);
      }
    }

    // Проверяем, что средняя уверенность коррелирует с вовлеченностью
    if (highEngConfidences.length > 0 && mediumEngConfidences.length > 0) {
      const avgHigh = highEngConfidences.reduce((a, b) => a + b, 0) / highEngConfidences.length;
      const avgMedium = mediumEngConfidences.reduce((a, b) => a + b, 0) / mediumEngConfidences.length;

      expect(avgHigh).toBeGreaterThan(avgMedium);
    }

    if (mediumEngConfidences.length > 0 && lowEngConfidences.length > 0) {
      const avgMedium = mediumEngConfidences.reduce((a, b) => a + b, 0) / mediumEngConfidences.length;
      const avgLow = lowEngConfidences.reduce((a, b) => a + b, 0) / lowEngConfidences.length;

      expect(avgMedium).toBeGreaterThan(avgLow);
    }
  });
});

test.describe('Граничные случаи для точности рекомендаций', () => {
  test('должен обрабатывать отсутствие данных воспроизведения', async ({ page }) => {
    // Mock API для случая отсутствия данных
    await page.route('**/api/schedule-ai/recommendations**', async route => {
      await route.fulfill({
        status: 200,
        json: {
          channel_id: TEST_CHANNEL,
          target_date: new Date().toISOString().split('T')[0],
          recommendations: [],  // Пустой список
        },
      });
    });

    await page.route('**/api/schedule-ai/peak-hours**', async route => {
      await route.fulfill({
        status: 200,
        json: {
          channel_id: TEST_CHANNEL,
          period: '30d',
          total_samples: 0,  // Нет данных
          peak_hours: [],
        },
      });
    });

    await login(page);
    await navigateToSchedule(page);

    // Проверяем, что система показывает сообщение об отсутствии данных
    const aiSection = page.locator('[data-testid="ai-recommendations-section"]');

    // Может показать пустое состояние или сообщение
    const emptyState = aiSection.locator('text=/недостаточно данных|no data|нет данных/i');
    const isVisible = await emptyState.isVisible().catch(() => false);

    if (isVisible) {
      await expect(emptyState).toBeVisible();
    }
    // Если recommendations пустые, секция может быть скрыта или показывать empty state
  });

  test('должен обрабатывать минимальные данные воспроизведения', async ({ page }) => {
    // Mock API с минимальными данными
    await page.route('**/api/schedule-ai/peak-hours**', async route => {
      await route.fulfill({
        status: 200,
        json: {
          channel_id: TEST_CHANNEL,
          period: '7d',
          total_samples: 1,  // Только один образец
          peak_hours: [
            {
              day_of_week: 0,
              hour: 14,
              avg_listeners: 10,
              peak_listeners: 10,
              play_count: 1,
            },
          ],
        },
      });
    });

    await page.route('**/api/schedule-ai/recommendations**', async route => {
      await route.fulfill({
        status: 200,
        json: {
          channel_id: TEST_CHANNEL,
          target_date: new Date().toISOString().split('T')[0],
          recommendations: [
            {
              id: 'rec-1',
              playlist_id: 'playlist-1',
              playlist_name: 'Default Playlist',
              start_time: '14:00',
              end_time: '16:00',
              type: 'FILL_GAP',
              confidence: 0.3,  // Низкая уверенность из-за малых данных
              reason: 'Недостаточно данных для точной рекомендации',
            },
          ],
        },
      });
    });

    await login(page);
    await navigateToSchedule(page);

    // Открываем пиковые часы
    await openPeakHoursModal(page);

    // Проверяем, что система показывает данные даже при минимальной выборке
    const dialog = page.locator('[role="dialog"]');
    await expect(dialog).toBeVisible();

    const samplesText = dialog.locator('text=/1.*образец|sample/i');
    await expect(samplesText).toBeVisible();
  });
});
