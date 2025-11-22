import fs from 'node:fs';
import path from 'node:path';

type TestStatus = 'passed' | 'failed';

interface TestResult {
  id: string;
  title: string;
  status: TestStatus;
  details: string;
  evidence?: string;
}

const BASE_URL = process.env.MCP_BASE_URL ?? 'http://localhost:3000';
const ADMIN_EMAIL = process.env.MCP_ADMIN_EMAIL ?? 'admin@sattva.com';
const ADMIN_PASSWORD = process.env.MCP_ADMIN_PASSWORD ?? 'Zxy1234567';
const POSITIVE_REGISTER_EMAIL = 'newuser@sattva.com';
const DUPLICATE_EMAIL = 'duplicate@sattva.com';
const DOUBLE_SUBMIT_EMAIL = 'doubleclick@sattva.com';
const SUITE_ID = new Date().toISOString().replace(/[:.]/g, '-');
const SUITE_DIR = path.join(process.cwd(), '.internal', 'playwright-mcp', `auth-suite-${SUITE_ID}`);

fs.mkdirSync(SUITE_DIR, { recursive: true });

export default async ({ page }: { page: any }) => {
  const results: TestResult[] = [];

  const saveResults = async () => {
    const resultsPath = path.join(SUITE_DIR, 'results.json');
    await fs.promises.writeFile(resultsPath, JSON.stringify(results, null, 2), 'utf-8');
    console.log(`[mcp] results saved to ${resultsPath}`);
  };

  const capture = async (id: string) => {
    const screenshotPath = path.join(SUITE_DIR, `${id}.png`);
    await page.screenshot({ path: screenshotPath, fullPage: true });
    return screenshotPath;
  };

  const resetState = async () => {
    await page.goto('about:blank');
    await page.context().clearCookies();
    await page.context().clearPermissions();
    await page.evaluate(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
  };

  const gotoPath = async (subPath: string) => {
    await page.goto(`${BASE_URL}${subPath}`, { waitUntil: 'networkidle' });
  };

  const waitForText = async (text: string) => {
    await page.waitForSelector(`text=${text}`, { timeout: 5000 });
  };

  const performLogin = async (email: string, password: string) => {
    await gotoPath('/login');
    await page.fill('#username', email);
    await page.fill('#password', password);
    const [response] = await Promise.all([
      page.waitForResponse((resp: any) => resp.url().includes('/api/auth/login'), { timeout: 10000 }),
      page.click('button[type="submit"]'),
    ]);
    return response;
  };

  const performRegister = async (email: string, password: string, fullName?: string) => {
    await gotoPath('/register');
    await page.fill('#email', email);
    if (fullName) {
      await page.fill('#full_name', fullName);
    }
    await page.fill('#password', password);
    const [response] = await Promise.all([
      page.waitForResponse((resp: any) => resp.url().includes('/api/auth/register'), { timeout: 10000 }),
      page.click('button[type="submit"]'),
    ]);
    return response;
  };

  const runCase = async (id: string, title: string, fn: () => Promise<void>) => {
    const started = Date.now();
    try {
      await resetState();
      await fn();
      const duration = Date.now() - started;
      results.push({ id, title, status: 'passed', details: `Пасс (${duration} мс)` });
      console.log(`[PASS] ${id} ${title}`);
    } catch (error: any) {
      const screenshotPath = await capture(id);
      const message = error?.message ?? String(error);
      results.push({ id, title, status: 'failed', details: message, evidence: screenshotPath });
      console.error(`[FAIL] ${id} ${title}: ${message}`);
    }
  };

  await runCase('TC-AUTH-001', 'Позитивный вход admin', async () => {
    const response = await performLogin(ADMIN_EMAIL, ADMIN_PASSWORD);
    if (response.status() !== 200) {
      const body = await response.text();
      throw new Error(`Ожидали 200, получили ${response.status()} (${body})`);
    }
    await page.waitForURL('**/dashboard', { timeout: 7000 });
    const token = await page.evaluate(() => localStorage.getItem('token'));
    if (!token) {
      throw new Error('JWT токен не сохранён в localStorage');
    }
  });

  await runCase('TC-AUTH-002', 'Неверный пароль', async () => {
    const response = await performLogin(ADMIN_EMAIL, 'Wrong123!');
    if (response.status() !== 401) {
      throw new Error(`Ожидали 401, получили ${response.status()}`);
    }
    await waitForText('Invalid email or password.');
    const token = await page.evaluate(() => localStorage.getItem('token'));
    if (token) {
      throw new Error('JWT токен создан при неверном пароле');
    }
  });

  await runCase('TC-AUTH-003', 'Рейт-лимит', async () => {
    const statuses: number[] = [];
    await gotoPath('/login');
    for (let attempt = 0; attempt < 6; attempt += 1) {
      await page.fill('#username', ADMIN_EMAIL);
      await page.fill('#password', `Wrong${attempt}123!`);
      try {
        const [response] = await Promise.all([
          page.waitForResponse((resp: any) => resp.url().includes('/api/auth/login'), { timeout: 10000 }),
          page.click('button[type="submit"]'),
        ]);
        statuses.push(response.status());
        if (response.status() === 429) {
          break;
        }
      } catch (error) {
        throw new Error(`Ошибка при попытке ${attempt + 1}: ${error}`);
      }
    }

    if (!statuses.includes(429)) {
      throw new Error(`429 не получен, статусы: ${statuses.join(', ')}`);
    }
    await waitForText('Login failed');
  });

  await runCase('TC-AUTH-004', 'Валидация пустой формы', async () => {
    await gotoPath('/login');
    let networkHit = false;
    const handler = (request: any) => {
      if (request.url().includes('/api/auth/login')) {
        networkHit = true;
      }
    };
    page.on('request', handler);
    await page.click('button[type="submit"]');
    await page.waitForTimeout(500);
    page.off('request', handler);
    if (networkHit) {
      throw new Error('Форма отправила запрос при пустых полях');
    }
    await waitForText('Invalid email');
    await waitForText('Password is required');
  });

  await runCase('TC-AUTH-005', 'Бэкенд недоступен', async () => {
    await gotoPath('/login');
    await page.route('**/api/auth/login', (route: any) => route.abort());
    await page.fill('#username', ADMIN_EMAIL);
    await page.fill('#password', ADMIN_PASSWORD);
    await page.click('button[type="submit"]');
    await waitForText('Login failed. Please try again later.');
    await page.unroute('**/api/auth/login');
    const token = await page.evaluate(() => localStorage.getItem('token'));
    if (token) {
      throw new Error('Токен создан несмотря на отсутствие ответа бэкенда');
    }
  });

  await runCase('TC-REG-001', 'Регистрация нового пользователя', async () => {
    const response = await performRegister(POSITIVE_REGISTER_EMAIL, ADMIN_PASSWORD, 'QA New User');
    if (response.status() !== 200 && response.status() !== 201) {
      const body = await response.text();
      throw new Error(`Ожидали 200/201, получили ${response.status()} (${body})`);
    }
    await page.waitForTimeout(2000);
    await page.waitForURL('**/dashboard', { timeout: 7000 });
    const token = await page.evaluate(() => localStorage.getItem('token'));
    if (!token) {
      throw new Error('JWT токен не создан после регистрации');
    }
  });

  await runCase('TC-REG-002', 'Дубликат email', async () => {
    const response = await performRegister(DUPLICATE_EMAIL, ADMIN_PASSWORD);
    if (response.status() !== 409) {
      throw new Error(`Ожидали 409, получили ${response.status()}`);
    }
    await waitForText('Email already exists. Please use a different email.');
  });

  await runCase('TC-REG-003', 'Слабый пароль', async () => {
    await gotoPath('/register');
    let requested = false;
    const handler = (request: any) => {
      if (request.url().includes('/api/auth/register')) {
        requested = true;
      }
    };
    page.on('request', handler);
    await page.fill('#email', 'weakpass@sattva.com');
    await page.fill('#password', 'Weakpass1');
    await page.click('button[type="submit"]');
    await page.waitForTimeout(500);
    page.off('request', handler);
    if (requested) {
      throw new Error('Слабый пароль ушёл на сервер');
    }
    await waitForText('Password must be at least 12 characters');
  });

  await runCase('TC-REG-004', 'Пустой email', async () => {
    await gotoPath('/register');
    await page.fill('#password', ADMIN_PASSWORD);
    await page.click('button[type="submit"]');
    await waitForText('Invalid email address');
  });

  await runCase('TC-REG-005', 'Неверный формат email', async () => {
    await gotoPath('/register');
    await page.fill('#email', 'user@@sattva.com');
    await page.fill('#password', ADMIN_PASSWORD);
    await page.click('button[type="submit"]');
    await waitForText('Invalid email address');
  });

  await runCase('TC-REG-006', 'Двойное нажатие сабмита', async () => {
    await gotoPath('/register');
    await page.fill('#email', DOUBLE_SUBMIT_EMAIL);
    await page.fill('#password', ADMIN_PASSWORD);
    const requests: number[] = [];
    const handler = (request: any) => {
      if (request.url().includes('/api/auth/register')) {
        requests.push(Date.now());
      }
    };
    page.on('request', handler);
    await page.locator('button[type="submit"]').dblclick();
    const response = await page.waitForResponse((resp: any) => resp.url().includes('/api/auth/register'), { timeout: 10000 });
    page.off('request', handler);
    if (requests.length !== 1) {
      throw new Error(`Ожидали 1 запрос, отправлено ${requests.length}`);
    }
    if (response.status() !== 200 && response.status() !== 201) {
      throw new Error(`Регистрация завершилась статусом ${response.status()}`);
    }
  });

  await saveResults();
};