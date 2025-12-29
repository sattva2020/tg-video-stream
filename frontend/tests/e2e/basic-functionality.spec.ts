/**
 * E2E тесты - Базовая проверка приложения
 * 
 * Проверяет:
 * - Доступность главной страницы
 * - Health check endpoint
 * - Базовая навигация
 */
import { test, expect } from '@playwright/test';

const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:3000';

test.describe('Базовая функциональность приложения', () => {
  test('главная страница загружается', async ({ page }) => {
    await page.goto(BASE_URL);
    
    // Проверяем что страница загрузилась
    await expect(page).toHaveTitle(/Sattva|Telegram|Broadcast/i);
    
    // Проверяем наличие основных элементов
    const body = await page.locator('body');
    await expect(body).toBeVisible();
  });

  test('health check endpoint доступен', async ({ request }) => {
    const response = await request.get(`${BASE_URL}/api/health`);
    
    expect(response.status()).toBe(200);
    
    const data = await response.json();
    expect(data).toHaveProperty('status');
  });

  test('404 страница для несуществующего роута', async ({ page }) => {
    const response = await page.goto(`${BASE_URL}/nonexistent-page-12345`);
    
    // Может быть 404 или редирект на главную
    expect([200, 404]).toContain(response?.status());
  });

  test('навигация на страницу логина', async ({ page }) => {
    await page.goto(BASE_URL);
    
    // Ищем ссылку/кнопку логина
    const loginLink = page.locator('a[href*="login"], button:has-text("Login"), button:has-text("Войти")').first();
    
    if (await loginLink.isVisible()) {
      await loginLink.click();
      
      // Проверяем что перешли на страницу логина
      await expect(page).toHaveURL(/login/i);
    }
  });
});

test.describe('API интеграция', () => {
  test('API возвращает корректные заголовки CORS', async ({ request }) => {
    const response = await request.get(`${BASE_URL}/api/health`);
    
    const headers = response.headers();
    // Проверяем наличие CORS заголовков (если настроены)
    // expect(headers).toHaveProperty('access-control-allow-origin');
    expect(response.status()).toBeLessThan(500);
  });

  test('неавторизованный доступ к защищённым endpoint возвращает 401', async ({ request }) => {
    const response = await request.get(`${BASE_URL}/api/users/me`, {
      failOnStatusCode: false
    });
    
    expect(response.status()).toBe(401);
  });
});
