import { test, expect } from '@playwright/test';

type BenefitExpectation = {
  label: string;
  metric?: string;
};

type LocaleExpectation = {
  code: 'en' | 'ru' | 'uk' | 'de';
  benefits: BenefitExpectation[];
};

const LOCALES: LocaleExpectation[] = [
  {
    code: 'en',
    benefits: [
      { label: 'Automated 24/7 uptime', metric: '365 days live' },
      { label: 'Managed playlist ingestion', metric: '50+ videos rotating' },
      { label: 'Instant switching without lag', metric: '<100 ms latency' },
    ],
  },
  {
    code: 'ru',
    benefits: [
      { label: 'Автоматический аптайм 24/7', metric: '365 дней в эфире' },
      { label: 'Умное управление плейлистами', metric: '50+ видео в ротации' },
      { label: 'Мгновенное переключение без лагов', metric: '<100 мс задержка' },
    ],
  },
  {
    code: 'uk',
    benefits: [
      { label: 'Автоматичний аптайм 24/7', metric: '365 днів наживо' },
      { label: 'Керований імпорт плейлистів', metric: '50+ відео в ротації' },
      { label: 'Миттєве перемикання без затримок', metric: '<100 мс затримки' },
    ],
  },
  {
    code: 'de',
    benefits: [
      { label: 'Automatischer 24/7-Betrieb', metric: '365 Tage live' },
      { label: 'Verwaltetes Playlist-Ingest', metric: '50+ Videos in Rotation' },
      { label: 'Sofortiges Umschalten ohne Lag', metric: '<100 ms Latenz' },
    ],
  },
];

for (const locale of LOCALES) {
  test(`renders ${locale.code} benefits in order`, async ({ page }) => {
    await page.addInitScript((selectedLocale) => {
      window.localStorage.clear();
      window.localStorage.setItem('landing:locale', selectedLocale);
      (window as Window & { __ACCEPT_LANGUAGE__?: string }).__ACCEPT_LANGUAGE__ = selectedLocale;
    }, locale.code);

    await page.goto('/');

    const benefits = page.getByTestId('hero-benefits').getByRole('listitem');
    await expect(benefits).toHaveCount(locale.benefits.length);

    for (const [index, expected] of locale.benefits.entries()) {
      const item = benefits.nth(index);
      await expect(item).toContainText(expected.label);
      if (expected.metric) {
        await expect(item).toContainText(expected.metric);
      }
    }
  });
}
