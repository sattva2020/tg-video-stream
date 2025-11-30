import { test, expect } from '@playwright/test';

const ensureEnglishLocale = async (page: import('@playwright/test').Page) => {
  await page.addInitScript(() => {
    window.localStorage.setItem('landing:locale', 'en');
    (window as Window & { __ACCEPT_LANGUAGE__?: string }).__ACCEPT_LANGUAGE__ = 'en';
  });
};

test.describe('Landing responsive layout', () => {
  test('keeps CTA visible and removes horizontal scroll at 280px width', async ({ page }) => {
    await ensureEnglishLocale(page);
    await page.setViewportSize({ width: 280, height: 720 });
    await page.goto('/');

    const hasHorizontalScroll = await page.evaluate(() => {
      return document.documentElement.scrollWidth > window.innerWidth;
    });
    expect(hasHorizontalScroll).toBeFalsy();

    const cta = page.getByRole('link', { name: /enter/i });
    await expect(cta).toBeVisible();

    const isCTAInViewport = await cta.evaluate((node) => {
      const rect = node.getBoundingClientRect();
      return rect.left >= 0 && rect.right <= window.innerWidth && rect.top >= 0 && rect.bottom <= window.innerHeight;
    });

    expect(isCTAInViewport).toBeTruthy();
  });
});
