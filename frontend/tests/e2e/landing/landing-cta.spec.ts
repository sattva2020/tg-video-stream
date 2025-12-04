import { test, expect } from '@playwright/test';

test.describe('Landing CTA', () => {
  test('renders hero block and redirects CTA to /login', async ({ page }) => {
    await page.goto('/');

    await expect(page.getByText('Telegram broadcast automation')).toBeVisible();
    await expect(page.getByRole('heading', { level: 1 })).toContainText('24/7 Telegram broadcasting');

    const cta = page.getByRole('link', { name: /get started/i }).first();
    await expect(cta).toBeVisible();
    await expect(cta).toHaveAttribute('href', '/login');

    await cta.click();
    await expect(page).toHaveURL(/\/login$/);
  });
});
