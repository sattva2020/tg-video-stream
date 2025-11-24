import { test, expect } from '@playwright/test';

test.describe('Auth Page - errors', () => {
  test('register shows localized message when backend returns message_key (409)', async ({ page }) => {
    await page.goto('/');
    // navigate to register view
    // assume application shows auth at root and mode toggle exists
    await page.waitForSelector('[data-testid="auth-card"]');

    // intercept register API to return 409 with message_key
    await page.route('**/api/auth/register', route => {
      route.fulfill({
        status: 409,
        contentType: 'application/json',
        body: JSON.stringify({ code: 'conflict', message_key: 'auth.email_registered', hint: 'email_exists' }),
      });
    });

    // switch to register mode if needed
    if (await page.$('input#register-email')) {
      // already in register mode
    } else {
      await page.click('text=Register');
    }

    await page.fill('input#register-email', 'exist@example.com');
    await page.fill('input#register-password', 'ValidPass123!');
    await page.fill('input#register-confirm-password', 'ValidPass123!');
    await page.click('[data-testid="auth-primary-action"]');

    // Expect banner with localized message based on message_key (the client resolves via i18next)
    const banner = await page.waitForSelector('div[data-testid="auth-card"] >> text=Пользователь с таким email уже существует');
    expect(banner).toBeTruthy();
  });

  test('login shows localized message when backend returns pending (403)', async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('[data-testid="auth-card"]');

    // intercept login API to return 403 with message_key
    await page.route('**/api/auth/login', route => {
      route.fulfill({
        status: 403,
        contentType: 'application/json',
        body: JSON.stringify({ code: 'pending', message_key: 'auth.account_pending', hint: 'contact_admin' }),
      });
    });

    // ensure in login mode
    if (await page.$('input#login-email')) {
      // ok
    } else {
      await page.click('text=Login');
    }

    await page.fill('input#login-email', 'pending@example.com');
    await page.fill('input#login-password', 'AnyPassword1!');
    await page.click('[data-testid="auth-primary-action"]');

    const banner = await page.waitForSelector('div[data-testid="auth-card"] >> text=Аккаунт ожидает одобрения администратора');
    expect(banner).toBeTruthy();
  });
});
import { test, expect, type Page, type Locator } from '@playwright/test';

const AUTH_ROUTE = '/auth';

const gotoAuthPage = async (page: Page) => {
  await page.goto(AUTH_ROUTE, { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('[data-testid="auth-card"]', { state: 'visible', timeout: 15000 });
};

const readCssValue = async (locator: Locator, property: keyof CSSStyleDeclaration) =>
  locator.evaluate((node, cssProperty) => getComputedStyle(node as HTMLElement)[cssProperty as keyof CSSStyleDeclaration], property);

const readFontFamily = async (locator: Locator) =>
  locator.evaluate((node) => getComputedStyle(node as HTMLElement).fontFamily);

const assertNoHorizontalOverflow = async (page: Page, tolerance = 1) => {
  const { docOverflow, bodyOverflow } = await page.evaluate(() => {
    const doc = document.documentElement;
    const body = document.body;
    return {
      docOverflow: Math.max(0, doc.scrollWidth - doc.clientWidth),
      bodyOverflow: Math.max(0, body.scrollWidth - doc.clientWidth),
    };
  });

  expect(Math.max(docOverflow, bodyOverflow)).toBeLessThanOrEqual(tolerance);

  const overflowX = await page.evaluate(() => getComputedStyle(document.body).overflowX);
  expect(overflowX === 'hidden' || overflowX === 'visible').toBeTruthy();
};

test.describe('Auth Page • Theme consistency', () => {
  test('mirrors landing typography and palette in light mode', async ({ page }) => {
    await gotoAuthPage(page);

    await expect(page.getByTestId('auth-card')).toBeVisible();

    const headingFont = await readFontFamily(page.getByTestId('auth-headline'));
    expect(headingFont).toMatch(/LandingSerif/i);

    const bodyFont = await readFontFamily(page.getByTestId('auth-page'));
    expect(bodyFont).toMatch(/LandingSans/i);

    const bodyBg = await readCssValue(page.locator('body'), 'backgroundColor');
    expect(bodyBg).toBe('rgb(247, 226, 198)');

    const primaryButton = page.getByTestId('auth-primary-action');
    const buttonBg = await readCssValue(primaryButton, 'backgroundColor');
    const buttonText = await readCssValue(primaryButton, 'color');
    expect(buttonBg).toBe('rgb(30, 26, 25)');
    expect(buttonText).toBe('rgb(247, 226, 198)');

    await expect(page.locator('[data-testid="auth-zen-canvas"] canvas')).toBeVisible();
  });

  test('keeps dashboard preview synced with ink/parchment tokens', async ({ page }) => {
    await gotoAuthPage(page);

    const htmlTheme = await page.evaluate(() => document.documentElement.dataset.theme);
    expect(htmlTheme).toBe('light');

    const preview = page.getByTestId('dashboard-preview');
    const previewColor = await readCssValue(preview, 'color');
    expect(previewColor).toBe('rgb(30, 26, 25)');

    const previewBg = await readCssValue(preview, 'backgroundColor');
    expect(previewBg).toMatch(/rgba?\(255,\s*255,\s*255/);

    const subheadingFont = await readFontFamily(preview);
    expect(subheadingFont).toMatch(/LandingSans/i);
  });
});

test.describe('Auth Page • Responsive layout', () => {
  test.describe('320px touch viewport', () => {
    test.use({ viewport: { width: 320, height: 640 }, hasTouch: true, isMobile: true, deviceScaleFactor: 2 });

    test('maintains layout without horizontal scrolling', async ({ page }) => {
      await gotoAuthPage(page);

      await assertNoHorizontalOverflow(page);

      const authCard = page.getByTestId('auth-card');
      await expect(authCard).toBeVisible();

      const primaryAction = page.getByTestId('auth-primary-action');
      await primaryAction.scrollIntoViewIfNeeded();
      await expect(primaryAction).toBeVisible();
      await expect(primaryAction).toBeEnabled();

      const dashboardPreview = page.getByTestId('dashboard-preview');
      await expect(dashboardPreview).toBeVisible();
    });
  });

  test.describe('280px fallback viewport', () => {
    test.use({ viewport: { width: 280, height: 640 }, hasTouch: true, isMobile: true, deviceScaleFactor: 2 });

    test('still exposes CTA buttons without overflow', async ({ page }) => {
      await gotoAuthPage(page);

      await assertNoHorizontalOverflow(page, 2);

      const primaryAction = page.getByTestId('auth-primary-action');
      await primaryAction.scrollIntoViewIfNeeded();
      await expect(primaryAction).toBeVisible();
      await expect(primaryAction).toBeInViewport();

      const tabs = page.getByRole('tablist', { name: /Auth flow mode/i });
      await expect(tabs).toBeVisible();
    });
  });
});

test.describe('Auth Page • Error handling', () => {
  test('surfaces 403 pending status with styled toast', async ({ page }) => {
    test.skip(true, 'US3 error styling pending.');
    await gotoAuthPage(page);

    await page.route('/api/auth/login', (route) => {
      route.fulfill({
        status: 403,
        contentType: 'application/json',
        body: JSON.stringify({ code: 'pending', message: 'Учётная запись на модерации', hint: 'Проверьте статус позже' }),
      });
    });

    // TODO: submit form and assert toast palette once component готов.
  });

  test('renders 409 conflict inline hint on registration', async ({ page }) => {
    test.skip(true, 'US3 error styling pending.');
    await gotoAuthPage(page);

    await page.route('/api/auth/register', (route) => {
      route.fulfill({
        status: 409,
        contentType: 'application/json',
        body: JSON.stringify({ code: 'conflict', message: 'Пользователь уже существует' }),
      });
    });

    // TODO: trigger duplicate registration and assert inline error snapshot.
  });
});

test.describe('Auth Page • Theme toggle', () => {
  test('switches between light and dark modes and persists preference', async ({ page }) => {
    await gotoAuthPage(page);

    // Initial state: Light mode
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'light');
    await expect(page.locator('body')).toHaveCSS('background-color', 'rgb(247, 226, 198)'); // Parchment

    // Toggle to Dark mode
    const themeToggle = page.getByTestId('theme-toggle');
    await themeToggle.click();

    await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
    await expect(page.locator('body')).toHaveCSS('background-color', 'rgb(12, 10, 9)'); // Night Sky

    // Reload to verify persistence
    await page.reload();
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
    await expect(page.locator('body')).toHaveCSS('background-color', 'rgb(12, 10, 9)'); // Night Sky

    // Toggle back to Light mode
    await themeToggle.click();
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'light');
    await expect(page.locator('body')).toHaveCSS('background-color', 'rgb(247, 226, 198)'); // Parchment
  });
});
