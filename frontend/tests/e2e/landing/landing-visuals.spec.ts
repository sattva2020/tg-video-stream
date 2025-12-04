import { test, expect } from '@playwright/test';

test.describe('Landing visual background', () => {
  test('renders particle background with 30 nodes by default', async ({ page }) => {
    await page.goto('/');

    const background = page.getByTestId('visual-background');
    await expect(background).toHaveAttribute('data-visual-mode', 'particles');
    await expect(background).toHaveAttribute('data-particle-count', '30');
    await expect(background.getByTestId('visual-particle')).toHaveCount(30);
  });

  test('switches to minimal mode when prefers-reduced-motion is enabled', async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.goto('/');

    const background = page.getByTestId('visual-background');
    await expect(background).toHaveAttribute('data-visual-mode', 'minimal');
    await expect(background).toHaveAttribute('data-reduced-motion', 'true');
    await expect(background.getByTestId('visual-particle')).toHaveCount(0);
  });

  test('allows forcing minimal visuals via window override', async ({ page }) => {
    await page.addInitScript(() => {
      (window as Window & { __VISUAL_BACKGROUND_MODE__?: 'particles' | 'minimal' }).__VISUAL_BACKGROUND_MODE__ =
        'minimal';
    });

    await page.goto('/');

    const background = page.getByTestId('visual-background');
    await expect(background).toHaveAttribute('data-visual-mode', 'minimal');
    await expect(background.getByTestId('visual-particle')).toHaveCount(0);
  });
});
