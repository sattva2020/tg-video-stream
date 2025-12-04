import { test, expect } from '@playwright/test';

test.describe('Landing metric bars', () => {
  test('renders animated progress bars for uptime metrics', async ({ page }) => {
    await page.goto('/');
    await page.waitForTimeout(300);

    const metricsContainer = page.getByLabel('Metric snapshots');
    await expect(metricsContainer).toBeVisible();

    const bars = metricsContainer.getByTestId('feature-metric-bar');
    await expect(bars).toHaveCount(3);

    for (let i = 0; i < 3; i += 1) {
      const progressValue = await bars.nth(i).getAttribute('data-progress-target');
      expect(Number.parseFloat(progressValue ?? '0')).toBeGreaterThan(0);
    }
  });

  test('updates metric labels when switching locale to ru', async ({ page }) => {
    await page.addInitScript(() => {
      window.localStorage.setItem('landing:locale', 'ru');
      (window as Window & { __ACCEPT_LANGUAGE__?: string }).__ACCEPT_LANGUAGE__ = 'ru';
    });
    await page.goto('/');

    const labels = await page
      .getByLabel('Metric snapshots')
      .getByTestId('feature-metric-label')
      .allTextContents();

    expect(labels.some((text) => text.includes('Целевой аптайм'))).toBeTruthy();
    expect(labels.some((text) => text.includes('Инцидентов автоисправлено'))).toBeTruthy();
  });
});
