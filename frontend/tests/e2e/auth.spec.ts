import { test, expect } from '@playwright/test';

const ADMIN_EMAIL = process.env.MCP_ADMIN_EMAIL ?? 'admin@sattva.com';
const ADMIN_PASSWORD = process.env.MCP_ADMIN_PASSWORD ?? 'Zxy1234567';
const DUPLICATE_EMAIL = 'duplicate@sattva.com';
// strong password to satisfy client-side RegisterSchema (min 12 chars, upper, lower, number, special)
const REGISTER_STRONG_PASSWORD = process.env.REGISTER_STRONG_PASSWORD ?? 'Zxy1234567!A';
test.describe('Auth smoke tests', () => {
  test('TC-AUTH-001 — positive login (admin)', async ({ page }) => {
    await page.goto('/login');
    const usernameField = page.locator('input[name="username"], input[name="email"], input[placeholder*="Email"], input[placeholder*="Электрон"]');
    const passwordField = page.locator('input[name="password"], input[placeholder*="Пароль"]');
    await usernameField.first().fill(ADMIN_EMAIL);
    await passwordField.first().fill(ADMIN_PASSWORD);
    await Promise.all([
      page.waitForResponse(resp => resp.url().includes('/api/auth/login') && resp.status() === 200),
      page.click('button[type="submit"]'),
    ]);
    await expect(page).toHaveURL(/dashboard/);
    const token = await page.evaluate(() => localStorage.getItem('token'));
    expect(token).toBeTruthy();
    await page.screenshot({ path: 'tests/e2e/artifacts/TC-AUTH-001.png' });
  });

  test('TC-AUTH-002 — invalid password shows error', async ({ page }) => {
    await page.goto('/login');
    const usernameField2 = page.locator('input[name="username"], input[name="email"], input[placeholder*="Email"], input[placeholder*="Электрон"]');
    const passwordField2 = page.locator('input[name="password"], input[placeholder*="Пароль"]');
    await usernameField2.first().fill(ADMIN_EMAIL);
    await passwordField2.first().fill('Wrong123!');
    // nothing to fill here — this is login page
    const [resp] = await Promise.all([
      page.waitForResponse(r => r.url().includes('/api/auth/login')),
      page.click('button[type="submit"]'),
    ]);
    // server may rate-limit frequent invalid attempts (429) — accept either
    expect([401, 429].includes(resp.status())).toBeTruthy();
    const invalidCount = await page.locator('text=Invalid email or password.').count();
    const tooManyCount = await page.locator('text=Too many requests').count();
    const loginFailedCount = await page.locator('text=Login failed. Please try again later.').count();
    expect(invalidCount + tooManyCount + loginFailedCount).toBeGreaterThan(0);
    await page.screenshot({ path: 'tests/e2e/artifacts/TC-AUTH-002.png' });
  });

  test('TC-REG-001 — register new user', async ({ page }) => {
    await page.goto('/register');
    const emailField = page.locator('input[name="email"], input[placeholder*="Email"], input[placeholder*="Электрон"]');
    // use unique email to avoid collisions with existing DB entries
    const dynamicEmail = `newuser-${Date.now()}@sattva.com`;
    const passwordField3 = page.locator('input[name="password"], input[placeholder*="Пароль"]');
    await page.waitForTimeout(300);
    await emailField.first().fill(dynamicEmail);
    await passwordField3.first().fill(REGISTER_STRONG_PASSWORD);
    // fill confirm password for duplicate check
    const confirmField2 = page.locator('input[name="confirmPassword"], input[placeholder*="Confirm"]');
    await confirmField2.first().fill(REGISTER_STRONG_PASSWORD);
    const [resp] = await Promise.all([
      page.waitForResponse(r => r.url().includes('/api/auth/register')),
      page.click('button[type="submit"]'),
    ]);
    expect([200, 201].includes(resp.status())).toBeTruthy();
    await expect(page).toHaveURL(/dashboard/);
    await page.screenshot({ path: 'tests/e2e/artifacts/TC-REG-001.png' });
  });

  test('TC-REG-002 — registration duplicate returns 409', async ({ page }) => {
    // Ensure duplicate user exists via API before attempting UI registration
    await page.request.post('http://localhost:8080/api/auth/register', { json: { email: DUPLICATE_EMAIL, password: REGISTER_STRONG_PASSWORD } }).catch(() => {});
    await page.goto('/register');
    // Give the page animation a moment to settle
    await page.waitForTimeout(300);
    await page.fill('input[name="email"]', DUPLICATE_EMAIL);
    await page.fill('input[name="password"]', REGISTER_STRONG_PASSWORD);
    // fill confirm password for duplicate case (AuthPage3D requires confirmPassword)
    const confirmFieldDup = page.locator('input[name="confirmPassword"], input[placeholder*="Confirm"]');
    await confirmFieldDup.first().fill(REGISTER_STRONG_PASSWORD);
    const [resp] = await Promise.all([
      page.waitForResponse(r => r.url().includes('/api/auth/register'), { timeout: 10000 }),
      page.click('button[type="submit"]'),
    ]);
    expect(resp.status()).toBe(409);
    // UI may show different localized messages depending on the page variant — accept either
    const existsCount = await page.locator('text=Email already exists').count();
    const regFailedCount = await page.locator('text=Registration failed').count();
    expect(existsCount + regFailedCount).toBeGreaterThan(0);
    await page.screenshot({ path: 'tests/e2e/artifacts/TC-REG-002.png' });
  });

  test('TC-REG-003 — weak password is rejected client-side', async ({ page }) => {
    await page.goto('/register');
    const emailField3 = page.locator('input[name="email"], input[placeholder*="Email"], input[placeholder*="Электрон"]');
    const passwordField5 = page.locator('input[name="password"], input[placeholder*="Пароль"]');
    await emailField3.first().fill('weakpass@sattva.com');
    await passwordField5.first().fill('Weakpass1');
    // confirm password required to validate
    const confirmField3 = page.locator('input[name="confirmPassword"], input[placeholder*="Confirm"]');
    await confirmField3.first().fill('Weakpass1');
    await page.waitForSelector('button[type="submit"]', { state: 'visible' });
    await page.click('button[type="submit"]');
    // expect client-side validation error message
    await expect(page.locator('text=Password must be at least 12 characters')).toBeVisible();
    await page.screenshot({ path: 'tests/e2e/artifacts/TC-REG-003.png' });
  });

  test('TC-REG-006 — double click submit sends single request', async ({ page }) => {
    await page.goto('/register');
    const emailField4 = page.locator('input[name="email"], input[placeholder*="Email"], input[placeholder*="Электрон"]');
    const passwordField6 = page.locator('input[name="password"], input[placeholder*="Пароль"]');
    // use a unique email for double-click test to avoid collisions
    const dcEmail = `doubleclick-${Date.now()}@sattva.com`;
    await page.waitForTimeout(300);
    await emailField4.first().fill(dcEmail);
    await passwordField6.first().fill(REGISTER_STRONG_PASSWORD);
    const confirmField4 = page.locator('input[name="confirmPassword"], input[placeholder*="Confirm"]');
    await confirmField4.first().fill(REGISTER_STRONG_PASSWORD);
    const requests: any[] = [];
    page.on('request', req => {
      if (req.url().includes('/api/auth/register')) requests.push(req);
    });
    await page.locator('button[type="submit"]').dblclick();
    const resp = await page.waitForResponse(r => r.url().includes('/api/auth/register'), { timeout: 10000 });
    expect([200, 201].includes(resp.status())).toBeTruthy();
    expect(requests.length).toBe(1);
    await page.screenshot({ path: 'tests/e2e/artifacts/TC-REG-006.png' });
  });
});
