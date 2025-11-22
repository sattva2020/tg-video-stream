import { test, expect } from '@playwright/test';

test.describe('Landing visual metrics', () => {
  test('collects fps samples for ZenScene', async ({ page }) => {
    await page.goto('/');
    await page.waitForTimeout(2000);

    const metrics = await page.evaluate(() => window.__landingMetrics);
    expect(metrics).toBeTruthy();
    expect(metrics?.mode).toBe('webgl');
    expect(metrics?.fpsSamples ?? 0).toBeGreaterThanOrEqual(5);
    expect(metrics?.averageFps ?? 0).toBeGreaterThanOrEqual(45);
  });

  test('records fallback latency when WebGL is disabled', async ({ page }) => {
    await page.addInitScript(() => {
      (window as Window & { __DISABLE_WEBGL__?: boolean }).__DISABLE_WEBGL__ = true;
    });

    await page.goto('/');
    await page.waitForTimeout(200);

    const metrics = await page.evaluate(() => window.__landingMetrics);
    expect(metrics).toBeTruthy();
    expect(metrics?.mode).toBe('poster');
    expect(metrics?.fallbackReason).toBeDefined();
    expect(metrics?.fallbackLatencyMs ?? 0).toBeLessThanOrEqual(500);
  });
});
