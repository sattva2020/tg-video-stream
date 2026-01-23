import { test, expect } from '@playwright/test';

test.describe('Auth Page Design', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
  });

  test('should use correct fonts', async ({ page }) => {
    // This test is expected to fail initially
    
    // Headings should use LandingSerif
    const heading = page.locator('h1, h2').first();
    await expect(heading).toHaveCSS('font-family', /LandingSerif/);
    
    // Inputs and body text should use LandingSans
    const input = page.locator('input').first();
    await expect(input).toHaveCSS('font-family', /LandingSans/);
  });

  test('should use correct colors', async ({ page }) => {
    // This test is expected to fail initially
    // We expect the form container (glass card) to have specific styling or the inputs to have specific colors
    
    const input = page.locator('input').first();
    // Inputs should have ink text
    await expect(input).toHaveCSS('color', 'rgb(74, 59, 50)'); // #4a3b32
    
    const button = page.locator('button[type="submit"]');
    // Button should match theme (e.g., ink background or outline)
    // This depends on exact implementation, but let's check for ink color presence
    // Expecting ink or gold, but definitely not default blue/gray if themed
    // For now, let's just check if it fails as expected
    await expect(button).toHaveCSS('background-color', 'rgb(74, 59, 50)'); // #4a3b32 (ink)
  });

  test('should be responsive on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 }); // iPhone SE size
    
    // Check for no horizontal scroll
    const scrollWidth = await page.evaluate(() => document.body.scrollWidth);
    const clientWidth = await page.evaluate(() => document.body.clientWidth);
    expect(scrollWidth).toBeLessThanOrEqual(clientWidth);
    
    // Check input width is appropriate
    // Card has px-4 (16px*2) wrapper padding + p-10 (40px*2) card padding = 112px total padding
    // 375 - 112 = 263px available width
    const input = page.locator('input').first();
    const inputBox = await input.boundingBox();
    expect(inputBox?.width).toBeGreaterThan(250);
    expect(inputBox?.width).toBeLessThan(300);
  });

  test('should show 3D scene on desktop', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    
    // Check card width constraint (max-w-md = 28rem = 448px)
    // The card is inside a wrapper with w-full max-w-md
    const cardWrapper = page.locator('.w-full.max-w-md');
    const cardBox = await cardWrapper.boundingBox();
    expect(cardBox?.width).toBeLessThanOrEqual(448);
    
    // Check if canvas exists
    const canvas = page.locator('canvas');
    await expect(canvas).toBeAttached();
  });

  test('should display error messages with correct styling', async ({ page }) => {
    // Trigger validation error
    const submitButton = page.locator('button[type="submit"]');
    await submitButton.click();
    
    // Check for email error
    const emailError = page.locator('p.text-red-600').first();
    await expect(emailError).toBeVisible();
    await expect(emailError).toHaveCSS('font-family', /LandingSans/);
    
    // Check color (red-600 is usually rgb(220, 38, 38))
    await expect(emailError).toHaveCSS('color', 'rgb(220, 38, 38)');
  });

  test('should show fallback background when WebGL is not available', async ({ page }) => {
    // Mock WebGL failure
    await page.addInitScript(() => {
      const originalGetContext = HTMLCanvasElement.prototype.getContext;
      // @ts-expect-error - Overriding native method for testing
      HTMLCanvasElement.prototype.getContext = function(contextId: string, ...args: any[]) {
        if (contextId === 'webgl' || contextId === 'experimental-webgl') {
          return null;
        }
        // @ts-expect-error - Calling original method with dynamic context
        return originalGetContext.apply(this, [contextId, ...args]);
      };
    });

    await page.reload();

    // Check for fallback element
    // It has class bg-[radial-gradient...]
    // We can check if Canvas is NOT present or if the fallback div IS present
    const canvas = page.locator('canvas');
    await expect(canvas).not.toBeAttached();

    const fallback = page.locator('.fixed.inset-0 > div.w-full.h-full');
    await expect(fallback).toBeVisible();
    // Check for gradient background
    await expect(fallback).toHaveCSS('background-image', /radial-gradient/);
  });
});
