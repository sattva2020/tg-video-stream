import { test, expect } from '@playwright/test';

test.describe('Landing CTA', () => {
  test('renders hero block and redirects CTA to /login', async ({ page }) => {
    await page.goto('/');

    await expect(page.getByText('Telegram 24/7 Video Streamer')).toBeVisible();
    await expect(page.getByRole('heading', { level: 1 })).toContainText('Always-on streaming');

    const cta = page.getByRole('link', { name: /enter/i });
    await expect(cta).toBeVisible();
    await expect(cta).toHaveAttribute('href', '/login');

    await cta.click();
    await expect(page).toHaveURL(/\/login$/);
  });
});
