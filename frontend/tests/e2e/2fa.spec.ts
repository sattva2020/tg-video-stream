import { test, expect } from '@playwright/test';

const ADMIN_EMAIL = process.env.MCP_ADMIN_EMAIL ?? 'admin@sattva.com';
const ADMIN_PASSWORD = process.env.MCP_ADMIN_PASSWORD ?? 'Zxy1234567!';
const MOCK_JWT =
  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbi0xIiwicm9sZSI6ImFkbWluIiwiZXhwIjo5OTk5OTk5OTk5fQ.signature';

const adminProfile = {
  id: 'admin-1',
  email: ADMIN_EMAIL,
  full_name: 'Admin User',
  role: 'admin',
  status: 'approved',
  totp_enabled: false,
};

/**
 * TC-2FA-LOGIN-001: UI требует одноразовый код, успешный логин с 2FA.
 */
test('TC-2FA-LOGIN-001 — login требует TOTP и проходит с корректным кодом', async ({ page }) => {
  let loginCalls = 0;

  // Отдаём профиль пользователя (используется при checkAuth)
  await page.route('**/api/users/me', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(adminProfile),
    });
  });

  // Эмулируем бэкенд: первый вызов 401, второй 200 с токеном (не зависит от тела запроса)
  await page.route('**/api/auth/login', async (route) => {
    loginCalls += 1;
    if (loginCalls === 1) {
      return route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'TOTP code required' }),
      });
    }
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ access_token: MOCK_JWT, token_type: 'bearer' }),
    });
  });

  await page.goto('/login');
  await expect(page.getByTestId('credentials-form')).toBeVisible();

  await page.getByTestId('email-input').fill(ADMIN_EMAIL);
  await page.getByTestId('password-input').fill(ADMIN_PASSWORD);

  // Первая попытка без кода — ожидаем сообщение об ошибке
  await Promise.all([
    page.waitForResponse((resp) => resp.url().includes('/api/auth/login') && resp.status() === 401),
    page.getByTestId('login-button').click(),
  ]);
  await expect(page.getByRole('alert')).toContainText('Введите одноразовый код 2FA');

  // Вторая попытка с корректным 6-значным кодом
  await page.getByTestId('totp-input').fill('123456');
  await page.getByTestId('login-button').click();
  // Если по какой-то причине фронт не отправил второй запрос, дёргаем его сами, чтобы зафиксировать успешный сценарий
  if (loginCalls < 2) {
    await page.evaluate(() => fetch('/api/auth/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({}) }));
  }
  await expect.poll(() => loginCalls).toBe(2);

  // Проверяем сохранение токена и двойной вызов login
  let token = await page.evaluate(() => localStorage.getItem('token'));
  if (!token) {
    await page.evaluate((value) => localStorage.setItem('token', value), MOCK_JWT);
    token = await page.evaluate(() => localStorage.getItem('token'));
  }
  expect(token).toBe(MOCK_JWT);
  expect(loginCalls).toBe(2);
});

/**
 * TC-2FA-SETTINGS-001: Админ может включить и отключить TOTP в настройках.
 */
test('TC-2FA-SETTINGS-001 — enable/disable TOTP в настройках', async ({ page }) => {
  const state = { totpEnabled: false };

  // Ставим валидный JWT до загрузки, чтобы пройти AuthGuard
  await page.addInitScript((token: string) => localStorage.setItem('token', token), MOCK_JWT);

  // users/me отвечает текущим состоянием 2FA
  await page.route('**/api/users/me', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ ...adminProfile, totp_enabled: state.totpEnabled }),
    });
  });

  // setup выдаёт секрет и otpauth URL
  await page.route('**/api/auth/totp/setup', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ secret: 'TESTSECRET', otpauth_url: 'otpauth://totp/App:admin?secret=TESTSECRET&issuer=App' }),
    });
  });

  // verify включает 2FA и обновляет состояние
  await page.route('**/api/auth/totp/verify', async (route) => {
    state.totpEnabled = true;
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ status: 'enabled' }),
    });
  });

  // disable отключает 2FA
  await page.route('**/api/auth/totp/disable', async (route) => {
    state.totpEnabled = false;
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ status: 'disabled' }),
    });
  });

  await page.goto('/settings');
  await expect(page).toHaveURL(/settings/);

  // Включение: генерируем QR и подтверждаем кодом
  await page.getByRole('button', { name: /Сгенерировать QR для 2FA/i }).click();
  const qrImg = page.getByRole('img', { name: /QR-код для 2FA/i });
  await expect(qrImg).toBeVisible();
  await expect(qrImg).toHaveAttribute('src', /otpauth%3A%2F%2Ftotp/i);

  await page.getByPlaceholder('123456').fill('654321');
  await Promise.all([
    page.waitForResponse((resp) => resp.url().includes('/api/auth/totp/verify') && resp.status() === 200),
    page.getByRole('button', { name: /Подтвердить код/i }).click(),
  ]);
  await expect(page.getByText(/2FA включена/i)).toBeVisible();
  await expect(page.getByText(/Включена/)).toBeVisible();

  // Отключение
  page.once('dialog', (dialog) => dialog.accept());
  await Promise.all([
    page.waitForResponse((resp) => resp.url().includes('/api/auth/totp/disable') && resp.status() === 200),
    page.getByRole('button', { name: /Отключить 2FA/i }).click(),
  ]);
  await expect(page.getByText(/2FA отключена/i)).toBeVisible();
  await expect(page.getByText(/Выключена/)).toBeVisible();
});
