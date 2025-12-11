import { test, expect } from '@playwright/test';

test.describe('Notifications Feature', () => {
  test.beforeEach(async ({ page }) => {
    // Авторизация
    await page.goto('/auth');
    await page.waitForLoadState('networkidle');
    
    // Предполагаем, что есть тестовый пользователь или Google auth
    // TODO: добавить авторизацию если потребуется
  });

  test('Notification Channels page accessible', async ({ page }) => {
    await page.goto('/notifications/channels');
    await page.waitForLoadState('networkidle');
    
    // Проверяем, что страница загрузилась
    await expect(page).toHaveURL(/\/notifications\/channels/);
    
    // Проверяем наличие заголовка
    const heading = page.locator('h1, h2').filter({ hasText: /channel/i }).first();
    await expect(heading).toBeVisible();
  });

  test('Can navigate to Templates page', async ({ page }) => {
    await page.goto('/notifications/templates');
    await page.waitForLoadState('networkidle');
    
    await expect(page).toHaveURL(/\/notifications\/templates/);
  });

  test('Can navigate to Recipients page', async ({ page }) => {
    await page.goto('/notifications/recipients');
    await page.waitForLoadState('networkidle');
    
    await expect(page).toHaveURL(/\/notifications\/recipients/);
  });

  test('Can navigate to Rules page', async ({ page }) => {
    await page.goto('/notifications/rules');
    await page.waitForLoadState('networkidle');
    
    await expect(page).toHaveURL(/\/notifications\/rules/);
  });

  test('Can navigate to Logs page', async ({ page }) => {
    await page.goto('/notifications/logs');
    await page.waitForLoadState('networkidle');
    
    await expect(page).toHaveURL(/\/notifications\/logs/);
  });

  test('API endpoints respond correctly', async ({ page }) => {
    const response = await page.request.get('https://sattva-streamer.top/api/notifications/channels');
    expect(response.status()).toBe(200);
    
    const data = await response.json();
    expect(Array.isArray(data)).toBeTruthy();
  });
});
