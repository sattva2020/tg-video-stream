import { test, expect } from '@playwright/test';

test.describe('Landing visual fallbacks', () => {
  test('renders ZenScene on capable devices', async ({ page }) => {
    await page.goto('/');

    const background = page.getByTestId('visual-background');
    await expect(background).toHaveAttribute('data-visual-mode', 'webgl');
    await expect(background).toHaveAttribute('data-webgl-ready', 'true');
    await expect(background.locator('canvas')).toHaveCount(1);
  });

  test('switches to gradient when prefers-reduced-motion is enabled', async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.goto('/');

    const background = page.getByTestId('visual-background');
    await expect(background).toHaveAttribute('data-visual-mode', 'gradient');
    await expect(background).toHaveAttribute('data-fallback-reason', 'reduced-motion');
    await expect(background.locator('canvas')).toHaveCount(0);
  });

  test('falls back to poster when WebGL is unavailable', async ({ page }) => {
    await page.addInitScript(() => {
      (window as Window & { __DISABLE_WEBGL__?: boolean }).__DISABLE_WEBGL__ = true;
      window.localStorage.clear();
    });
    await page.goto('/');

    const background = page.getByTestId('visual-background');
    await expect(background).toHaveAttribute('data-visual-mode', 'poster');
    await expect(background).toHaveAttribute('data-poster-visible', 'true');
    await expect(background.locator('canvas')).toHaveCount(0);
  });
});
