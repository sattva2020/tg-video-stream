import { test, expect } from '@playwright/test';

const expectations = {
  en: {
    heading: 'Always-on streaming',
    cta: 'Enter',
  },
  ru: {
    heading: 'Круглосуточные трансляции',
    cta: 'Войти',
  },
  uk: {
    heading: 'Безперервні стрими',
    cta: 'Увійти',
  },
  de: {
    heading: 'Durchgängiges Streaming',
    cta: 'Eintreten',
  },
} as const;

test.describe('Landing language switcher', () => {
  test('updates hero and CTA when selecting locales', async ({ page }) => {
    await page.goto('/');

    const trigger = page.getByTestId('language-switcher-trigger');
    const heading = page.getByRole('heading', { level: 1 });

    // Ensure default English copy is visible.
    await expect(heading).toContainText(expectations.en.heading);
    await expect(page.getByRole('link', { name: expectations.en.cta })).toBeVisible();

    const switchLocale = async (code: keyof typeof expectations) => {
      await trigger.click();
      await page.locator(`[data-locale="${code}"]`).click();
      await expect(heading).toContainText(expectations[code].heading);
      await expect(page.getByRole('link', { name: expectations[code].cta })).toBeVisible();
    };

    await switchLocale('ru');
    await switchLocale('uk');
    await switchLocale('de');
    await switchLocale('en');
  });
});
