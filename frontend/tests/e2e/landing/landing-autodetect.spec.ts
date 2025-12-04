import { test, expect } from '@playwright/test';

type Scenario = {
  header: string;
  expectedLocale: 'en' | 'ru' | 'uk' | 'de';
  expectedHeadingSnippet: string;
  expectFallbackHint?: boolean;
};

const scenarios: Scenario[] = [
  {
    header: 'ru-RU,ru;q=0.9,en;q=0.8',
    expectedLocale: 'ru',
    expectedHeadingSnippet: 'Круглосуточное вещание в Telegram',
  },
  {
    header: 'uk-UA,uk;q=0.9,en;q=0.6',
    expectedLocale: 'uk',
    expectedHeadingSnippet: 'Безперервне мовлення в Telegram',
  },
  {
    header: 'de-DE,de;q=0.9,en;q=0.5',
    expectedLocale: 'de',
    expectedHeadingSnippet: 'Durchgängiges Broadcasting in Telegram',
  },
  {
    header: 'es-ES,es;q=0.9,fr;q=0.8',
    expectedLocale: 'en',
    expectedHeadingSnippet: 'Always-on Telegram broadcasting',
    expectFallbackHint: true,
  },
];

let matches = 0;

test.describe.configure({ mode: 'serial' });

test.describe('Landing locale autodetect', () => {
  for (const scenario of scenarios) {
    test(`detects locale for header ${scenario.header}`, async ({ page }) => {
      await page.addInitScript((headerValue) => {
        window.localStorage.clear();
        (window as Window & { __ACCEPT_LANGUAGE__?: string }).__ACCEPT_LANGUAGE__ = headerValue;
      }, scenario.header);

      await page.goto('/');

      const heading = page.getByRole('heading', { level: 1 });
      await expect(heading).toContainText(scenario.expectedHeadingSnippet);

      const hint = page.getByTestId('language-fallback-hint');
      await expect(hint).toHaveCount(scenario.expectFallbackHint ? 1 : 0);

      matches += 1;
    });
  }

  test.afterAll(() => {
    const total = scenarios.length;
    const accuracy = Math.round((matches / total) * 100);
    console.info(`[landing-autodetect] locale accuracy: ${matches}/${total} (${accuracy}%)`);
  });
});
