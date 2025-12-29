import { test, expect } from '@playwright/test';

/**
 * E2E тесты для критических флоу стриминга
 * Проверяем end-to-end работу основного функционала
 */

const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:3000';
const ADMIN_EMAIL = process.env.MCP_ADMIN_EMAIL || 'admin@sattva.com';
const ADMIN_PASSWORD = process.env.MCP_ADMIN_PASSWORD || 'Zxy1234567';

test.describe('Streaming Critical Flows', () => {
  test.beforeEach(async ({ page }) => {
    // Переходим на страницу
    await page.goto(BASE_URL);
    
    // Логинимся как админ
    await page.fill('input[type="email"]', ADMIN_EMAIL);
    await page.fill('input[type="password"]', ADMIN_PASSWORD);
    await page.click('button[type="submit"]');
    
    // Ждем загрузки дашборда
    await page.waitForURL('**/dashboard', { timeout: 10000 });
  });

  test('должен запустить и остановить стрим', async ({ page }) => {
    // Находим кнопку старта стрима
    const startButton = page.locator('button:has-text("Start Stream")');
    await expect(startButton).toBeVisible({ timeout: 5000 });
    
    // Запускаем стрим
    await startButton.click();
    
    // Ждем индикатор активного стрима
    await expect(page.locator('text=Streaming')).toBeVisible({ timeout: 10000 });
    
    // Проверяем что показывается текущий трек
    const currentTrack = page.locator('[data-testid="current-track"]');
    await expect(currentTrack).toBeVisible({ timeout: 5000 });
    
    // Останавливаем стрим
    const stopButton = page.locator('button:has-text("Stop Stream")');
    await stopButton.click();
    
    // Ждем подтверждения остановки
    await expect(page.locator('text=Stream stopped')).toBeVisible({ timeout: 5000 });
  });

  test('должен переключить трек во время стрима', async ({ page }) => {
    // Запускаем стрим
    await page.click('button:has-text("Start Stream")');
    await expect(page.locator('text=Streaming')).toBeVisible({ timeout: 10000 });
    
    // Получаем название текущего трека
    const currentTrack = await page.locator('[data-testid="current-track-title"]').textContent();
    
    // Нажимаем "Next Track"
    await page.click('button:has-text("Next")');
    
    // Ждем смены трека
    await page.waitForTimeout(2000);
    
    // Проверяем что трек изменился
    const newTrack = await page.locator('[data-testid="current-track-title"]').textContent();
    expect(newTrack).not.toBe(currentTrack);
  });

  test('должен показывать плейлист', async ({ page }) => {
    // Переходим в плейлист
    await page.click('a:has-text("Playlist")');
    
    // Ждем загрузки плейлиста
    await expect(page.locator('[data-testid="playlist-item"]').first()).toBeVisible({ timeout: 5000 });
    
    // Проверяем что есть треки
    const tracks = await page.locator('[data-testid="playlist-item"]').count();
    expect(tracks).toBeGreaterThan(0);
    
    // Проверяем структуру трека
    const firstTrack = page.locator('[data-testid="playlist-item"]').first();
    await expect(firstTrack.locator('[data-testid="track-title"]')).toBeVisible();
    await expect(firstTrack.locator('[data-testid="track-artist"]')).toBeVisible();
  });

  test('должен управлять громкостью', async ({ page }) => {
    // Запускаем стрим
    await page.click('button:has-text("Start Stream")');
    await expect(page.locator('text=Streaming')).toBeVisible({ timeout: 10000 });
    
    // Находим слайдер громкости
    const volumeSlider = page.locator('[data-testid="volume-slider"]');
    await expect(volumeSlider).toBeVisible();
    
    // Изменяем громкость (например, на 50%)
    const sliderBounds = await volumeSlider.boundingBox();
    if (sliderBounds) {
      await page.mouse.click(
        sliderBounds.x + sliderBounds.width * 0.5,
        sliderBounds.y + sliderBounds.height / 2
      );
    }
    
    // Проверяем что значение изменилось
    await page.waitForTimeout(500);
    const volumeValue = await page.locator('[data-testid="volume-value"]').textContent();
    expect(volumeValue).toContain('%');
  });

  test('должен показывать историю треков', async ({ page }) => {
    // Переходим в историю
    await page.click('a:has-text("History")');
    
    // Ждем загрузки
    await page.waitForLoadState('networkidle');
    
    // Проверяем наличие истории или пустого состояния
    const historyItems = await page.locator('[data-testid="history-item"]').count();
    const emptyState = await page.locator('text=No history yet').count();
    
    expect(historyItems + emptyState).toBeGreaterThan(0);
  });
});

test.describe('Admin Streaming Controls', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(BASE_URL);
    await page.fill('input[type="email"]', ADMIN_EMAIL);
    await page.fill('input[type="password"]', ADMIN_PASSWORD);
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard', { timeout: 10000 });
    
    // Переходим в админку
    await page.click('a:has-text("Admin")');
    await page.waitForURL('**/admin/**', { timeout: 5000 });
  });

  test('должен показывать метрики стрима', async ({ page }) => {
    // Проверяем наличие метрик
    await expect(page.locator('text=CPU Usage')).toBeVisible({ timeout: 5000 });
    await expect(page.locator('text=Memory Usage')).toBeVisible({ timeout: 5000 });
    
    // Проверяем что значения метрик отображаются
    const cpuValue = page.locator('[data-testid="cpu-usage"]');
    await expect(cpuValue).toBeVisible();
    
    const memoryValue = page.locator('[data-testid="memory-usage"]');
    await expect(memoryValue).toBeVisible();
  });

  test('должен управлять плейлистом', async ({ page }) => {
    // Переходим в управление плейлистом
    await page.click('a:has-text("Playlist Management")');
    
    // Проверяем возможность добавления трека
    const addButton = page.locator('button:has-text("Add Track")');
    await expect(addButton).toBeVisible({ timeout: 5000 });
    
    // Проверяем возможность удаления трека
    const firstTrack = page.locator('[data-testid="playlist-track"]').first();
    if (await firstTrack.count() > 0) {
      await firstTrack.hover();
      const deleteButton = firstTrack.locator('button[aria-label="Delete"]');
      await expect(deleteButton).toBeVisible();
    }
  });

  test('должен показывать активные подключения', async ({ page }) => {
    // Ищем секцию с подключениями
    const connectionsSection = page.locator('text=Active Connections');
    
    if (await connectionsSection.count() > 0) {
      await expect(connectionsSection).toBeVisible();
      
      // Проверяем отображение количества слушателей
      await expect(page.locator('[data-testid="listeners-count"]')).toBeVisible();
    }
  });

  test('должен конфигурировать качество стрима', async ({ page }) => {
    // Переходим в настройки
    await page.click('a:has-text("Settings")');
    
    // Ищем настройки качества
    const qualitySelect = page.locator('[data-testid="stream-quality"]');
    
    if (await qualitySelect.count() > 0) {
      await expect(qualitySelect).toBeVisible();
      
      // Проверяем доступные опции
      await qualitySelect.click();
      await expect(page.locator('text=High')).toBeVisible();
      await expect(page.locator('text=Medium')).toBeVisible();
      await expect(page.locator('text=Low')).toBeVisible();
    }
  });
});

test.describe('User Streaming Experience', () => {
  const USER_EMAIL = 'user@sattva.com';
  const USER_PASSWORD = 'User1234567';

  test.beforeEach(async ({ page }) => {
    await page.goto(BASE_URL);
    await page.fill('input[type="email"]', USER_EMAIL);
    await page.fill('input[type="password"]', USER_PASSWORD);
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard', { timeout: 10000 });
  });

  test('обычный пользователь может слушать стрим', async ({ page }) => {
    // Проверяем что отображается плеер
    const player = page.locator('[data-testid="audio-player"]');
    await expect(player).toBeVisible({ timeout: 5000 });
    
    // Проверяем что есть кнопка play/pause
    const playButton = page.locator('button[aria-label="Play"]');
    await expect(playButton).toBeVisible();
  });

  test('обычный пользователь НЕ может управлять стримом', async ({ page }) => {
    // Проверяем что кнопок управления стримом нет
    const startStreamButton = page.locator('button:has-text("Start Stream")');
    await expect(startStreamButton).not.toBeVisible();
    
    const stopStreamButton = page.locator('button:has-text("Stop Stream")');
    await expect(stopStreamButton).not.toBeVisible();
  });

  test('пользователь может видеть текущий трек', async ({ page }) => {
    // Проверяем отображение информации о треке
    const trackInfo = page.locator('[data-testid="current-track-info"]');
    
    // Должна быть либо информация о треке, либо сообщение "Not streaming"
    await expect(
      trackInfo.or(page.locator('text=Not streaming'))
    ).toBeVisible({ timeout: 5000 });
  });
});

test.describe('Stream Error Handling', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(BASE_URL);
    await page.fill('input[type="email"]', ADMIN_EMAIL);
    await page.fill('input[type="password"]', ADMIN_PASSWORD);
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard', { timeout: 10000 });
  });

  test('должен показывать ошибку при недоступности API', async ({ page }) => {
    // Блокируем API запросы
    await page.route('**/api/stream/**', route => route.abort());
    
    // Пытаемся запустить стрим
    await page.click('button:has-text("Start Stream")');
    
    // Должна показаться ошибка
    await expect(page.locator('text=Error')).toBeVisible({ timeout: 5000 });
  });

  test('должен восстановиться после сетевой ошибки', async ({ page }) => {
    let requestCount = 0;
    
    // Первые 2 запроса фейлим, потом пропускаем
    await page.route('**/api/stream/status', route => {
      requestCount++;
      if (requestCount <= 2) {
        route.abort();
      } else {
        route.continue();
      }
    });
    
    // Ждем автоматического retry и восстановления
    await expect(page.locator('[data-testid="stream-status"]')).toBeVisible({ timeout: 15000 });
  });
});

test.describe('Stream Performance', () => {
  test('должен загружаться быстро', async ({ page }) => {
    const startTime = Date.now();
    
    await page.goto(BASE_URL);
    await page.fill('input[type="email"]', ADMIN_EMAIL);
    await page.fill('input[type="password"]', ADMIN_PASSWORD);
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard', { timeout: 10000 });
    
    const loadTime = Date.now() - startTime;
    
    // Dashboard должен загрузиться за разумное время (< 5 секунд)
    expect(loadTime).toBeLessThan(5000);
  });

  test('не должно быть memory leaks при переключении треков', async ({ page }) => {
    await page.goto(`${BASE_URL}/dashboard`);
    
    // Получаем начальное количество используемой памяти
    const initialMetrics = await page.metrics();
    
    // Переключаем треки 10 раз
    for (let i = 0; i < 10; i++) {
      await page.click('button:has-text("Next")');
      await page.waitForTimeout(500);
    }
    
    // Получаем финальные метрики
    const finalMetrics = await page.metrics();
    
    // Используемая память не должна вырасти более чем на 50MB
    const memoryGrowth = finalMetrics.JSHeapUsedSize - initialMetrics.JSHeapUsedSize;
    expect(memoryGrowth).toBeLessThan(50 * 1024 * 1024); // 50MB
  });
});
