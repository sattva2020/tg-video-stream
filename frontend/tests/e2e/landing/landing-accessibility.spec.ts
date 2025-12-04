import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

const prepareLocale = async (page: import('@playwright/test').Page) => {
  await page.addInitScript(() => {
    window.localStorage.setItem('landing:locale', 'en');
    (window as Window & { __ACCEPT_LANGUAGE__?: string }).__ACCEPT_LANGUAGE__ = 'en';
  });
};

test.describe('Landing accessibility', () => {
  test('CTA reachable within 3 tabs and passes axe-core smoke', async ({ page }) => {
    await prepareLocale(page);
    await page.goto('/');

    const cta = page.getByRole('link', { name: /get started/i }).first();
    let reached = false;

    for (let attempt = 0; attempt < 3; attempt += 1) {
      await page.keyboard.press('Tab');
      const isFocused = await cta.evaluate((node) => node === document.activeElement);
      if (isFocused) {
        reached = true;
        break;
      }
    }

    expect(reached).toBeTruthy();

    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze();

    expect(accessibilityScanResults.violations, accessibilityScanResults.url).toEqual([]);
  });
});
