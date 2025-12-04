import { test, expect } from '@playwright/test';

const expectations = {
  en: {
    heading: '24/7 Telegram broadcasting without OBS or hardware',
    cta: 'Get Started',
  },
  ru: {
    heading: '24/7 трансляции в Telegram без OBS и серверов',
    cta: 'Начать работу',
  },
  uk: {
    heading: '24/7 мовлення в Telegram без OBS і серверів',
    cta: 'Почати роботу',
  },
  de: {
    heading: '24/7 Telegram Broadcasting ohne OBS oder Hardware',
    cta: 'Jetzt starten',
  },
} as const;

test.describe('Landing language switcher', () => {
  test('updates hero and CTA when selecting locales', async ({ page }) => {
    await page.goto('/');

    const trigger = page.getByTestId('language-switcher-trigger');
    const heading = page.getByRole('heading', { level: 1 });

    // Ensure default English copy is visible.
    await expect(heading).toContainText(expectations.en.heading);
    await expect(page.getByRole('link', { name: expectations.en.cta }).first()).toBeVisible();

    const switchLocale = async (code: keyof typeof expectations) => {
      await trigger.click();
      await page.locator(`[data-locale="${code}"]`).click();
      await expect(heading).toContainText(expectations[code].heading);
      await expect(page.getByRole('link', { name: expectations[code].cta }).first()).toBeVisible();
    };

    await switchLocale('ru');
    await switchLocale('uk');
    await switchLocale('de');
    await switchLocale('en');
  });
});
