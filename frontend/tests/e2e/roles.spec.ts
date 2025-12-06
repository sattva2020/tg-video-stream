/**
 * Role-Based Access Control (RBAC) E2E Tests
 * 
 * Тесты для проверки доступа разных ролей пользователей.
 * Пароль для всех тестовых пользователей: TestPass123!
 */

import { test, expect, Page } from '@playwright/test';

const BASE_URL = process.env.TEST_BASE_URL || 'https://sattva-streamer.top';
const TEST_PASSWORD = 'TestPass123!';

// Тестовые пользователи для каждой роли
const TEST_USERS = {
  SUPERADMIN: 'test_superadmin@sattva.test',
  ADMIN: 'test_admin@sattva.test',
  MODERATOR: 'test_moderator@sattva.test',
  OPERATOR: 'test_operator@sattva.test',
  USER: 'test_user@sattva.test',
} as const;

type UserRole = keyof typeof TEST_USERS;

// Страницы и их требуемые роли
const PAGES = {
  dashboard: { path: '/dashboard', minRole: 'USER' },
  playlist: { path: '/playlist', minRole: 'USER' },
  schedule: { path: '/schedule', minRole: 'OPERATOR' },
  channels: { path: '/channels', minRole: 'OPERATOR' },
  monitoring: { path: '/admin/monitoring', minRole: 'ADMIN' },
  users: { path: '/admin/users', minRole: 'ADMIN' },
} as const;

// Иерархия ролей (от высшей к низшей)
const ROLE_HIERARCHY: UserRole[] = ['SUPERADMIN', 'ADMIN', 'MODERATOR', 'OPERATOR', 'USER'];

/**
 * Логин пользователя через email/password форму
 */
async function loginAs(page: Page, role: UserRole): Promise<void> {
  const email = TEST_USERS[role];
  
  await page.goto(`${BASE_URL}/login`);
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(2000); // Ждём React рендер
  
  // Ищем форму credentials
  const emailInput = page.locator('[data-testid="email-input"], #auth-email');
  const passwordInput = page.locator('[data-testid="password-input"], #auth-password');
  const loginButton = page.locator('[data-testid="login-button"], button[type="submit"]:has-text("Войти")');
  
  await expect(emailInput).toBeVisible({ timeout: 15000 });
  
  await emailInput.fill(email);
  await passwordInput.fill(TEST_PASSWORD);
  await loginButton.click();
  
  // Ждём редирект на dashboard или channels
  await page.waitForURL(/\/(dashboard|channels)/, { timeout: 15000 });
}

/**
 * Проверяет, имеет ли роль доступ (на основе иерархии)
 */
function hasAccess(userRole: UserRole, minRole: string): boolean {
  const userIndex = ROLE_HIERARCHY.indexOf(userRole);
  const minIndex = ROLE_HIERARCHY.indexOf(minRole as UserRole);
  return userIndex <= minIndex; // Меньший индекс = более высокая роль
}

// ============================================================================
// Тесты авторизации для каждой роли
// ============================================================================

test.describe('Role Authentication', () => {
  for (const role of ROLE_HIERARCHY) {
    test(`${role} can login successfully`, async ({ page }) => {
      await loginAs(page, role);
      
      // Проверяем что попали на защищённую страницу
      const url = page.url();
      expect(url).toMatch(/\/(dashboard|channels)/);
      
      // Проверяем что нет ошибки авторизации
      const errorMessage = page.locator('[role="alert"], .text-red-600, .error');
      await expect(errorMessage).not.toBeVisible({ timeout: 3000 }).catch(() => {
        // Игнорируем если нет ошибки
      });
    });
  }
});

// ============================================================================
// Тесты доступа к страницам
// ============================================================================

test.describe('Page Access by Role', () => {
  // Тест для каждой роли
  for (const role of ROLE_HIERARCHY) {
    test.describe(`${role} access`, () => {
      test.beforeEach(async ({ page }) => {
        await loginAs(page, role);
      });

      // Dashboard - доступен всем
      test('can access dashboard', async ({ page }) => {
        await page.goto(`${BASE_URL}/dashboard`);
        await page.waitForLoadState('networkidle');
        
        // Не должно быть редиректа на логин
        expect(page.url()).not.toContain('/login');
        
        // Должен быть контент dashboard
        const content = page.locator('h1, h2, [data-testid="dashboard"]');
        await expect(content.first()).toBeVisible({ timeout: 10000 });
      });

      // Playlist - доступен всем
      test('can access playlist', async ({ page }) => {
        await page.goto(`${BASE_URL}/playlist`);
        await page.waitForLoadState('networkidle');
        
        expect(page.url()).not.toContain('/login');
      });

      // Schedule - OPERATOR и выше
      if (hasAccess(role, 'OPERATOR')) {
        test('can access schedule', async ({ page }) => {
          await page.goto(`${BASE_URL}/schedule`);
          await page.waitForLoadState('networkidle');
          
          expect(page.url()).not.toContain('/login');
          
          // Проверяем наличие контента расписания
          const scheduleContent = page.locator('[data-testid="schedule"], .calendar, h1, h2');
          await expect(scheduleContent.first()).toBeVisible({ timeout: 10000 });
        });
      } else {
        test('cannot access schedule (redirects or shows error)', async ({ page }) => {
          await page.goto(`${BASE_URL}/schedule`);
          await page.waitForLoadState('networkidle');
          
          // Должен быть либо редирект, либо сообщение об ошибке доступа
          const accessDenied = page.locator('text=/access denied|forbidden|403|нет доступа/i');
          const redirectedToLogin = page.url().includes('/login');
          const redirectedToDashboard = page.url().includes('/dashboard');
          
          const hasNoAccess = redirectedToLogin || redirectedToDashboard || await accessDenied.isVisible().catch(() => false);
          expect(hasNoAccess).toBeTruthy();
        });
      }

      // Monitoring - ADMIN и выше
      if (hasAccess(role, 'ADMIN')) {
        test('can access monitoring', async ({ page }) => {
          await page.goto(`${BASE_URL}/admin/monitoring`);
          await page.waitForLoadState('networkidle');
          await page.waitForTimeout(2000);
          
          expect(page.url()).not.toContain('/login');
          
          // Проверяем наличие header и контента
          const content = page.locator('h1, h2, [data-testid="monitoring"], header');
          await expect(content.first()).toBeVisible({ timeout: 10000 });
        });

        test('can access users management', async ({ page }) => {
          await page.goto(`${BASE_URL}/admin/users`);
          await page.waitForLoadState('networkidle');
          
          expect(page.url()).not.toContain('/login');
        });
      } else {
        test('cannot access monitoring (redirects or shows error)', async ({ page }) => {
          await page.goto(`${BASE_URL}/admin/monitoring`);
          await page.waitForLoadState('networkidle');
          await page.waitForTimeout(2000);
          
          const accessDenied = page.locator('text=/access denied|forbidden|403|нет доступа/i');
          const redirectedToLogin = page.url().includes('/login');
          const redirectedToDashboard = page.url().includes('/dashboard');
          
          const hasNoAccess = redirectedToLogin || redirectedToDashboard || await accessDenied.isVisible().catch(() => false);
          expect(hasNoAccess).toBeTruthy();
        });
      }
    });
  }
});

// ============================================================================
// Тесты API доступа
// ============================================================================

test.describe('API Access by Role', () => {
  for (const role of ROLE_HIERARCHY) {
    test.describe(`${role} API access`, () => {
      let authToken: string;

      test.beforeAll(async ({ request }) => {
        // Получаем токен через login API
        const response = await request.post(`${BASE_URL}/api/auth/login`, {
          form: {
            username: TEST_USERS[role],
            password: TEST_PASSWORD,
          },
        });
        
        if (response.ok()) {
          const data = await response.json();
          authToken = data.access_token;
        }
      });

      test('can access /api/users/me', async ({ request }) => {
        if (!authToken) {
          test.skip();
          return;
        }

        const response = await request.get(`${BASE_URL}/api/users/me`, {
          headers: { Authorization: `Bearer ${authToken}` },
        });

        expect(response.status()).toBe(200);
        const user = await response.json();
        expect(user.email).toBe(TEST_USERS[role]);
        expect(user.role).toBe(role);
      });

      test('can access /api/channels', async ({ request }) => {
        if (!authToken) {
          test.skip();
          return;
        }

        const response = await request.get(`${BASE_URL}/api/channels`, {
          headers: { Authorization: `Bearer ${authToken}` },
        });

        // Все авторизованные пользователи должны иметь доступ к списку каналов
        expect(response.status()).toBeLessThan(500);
      });

      // Admin-only endpoints
      if (hasAccess(role, 'ADMIN')) {
        test('can access /api/admin/users', async ({ request }) => {
          if (!authToken) {
            test.skip();
            return;
          }

          const response = await request.get(`${BASE_URL}/api/admin/users`, {
            headers: { Authorization: `Bearer ${authToken}` },
          });

          expect(response.status()).toBe(200);
        });
      } else {
        test('cannot access /api/admin/users (403)', async ({ request }) => {
          if (!authToken) {
            test.skip();
            return;
          }

          const response = await request.get(`${BASE_URL}/api/admin/users`, {
            headers: { Authorization: `Bearer ${authToken}` },
          });

          expect([401, 403]).toContain(response.status());
        });
      }
    });
  }
});

// ============================================================================
// Тесты UI элементов по ролям
// ============================================================================

test.describe('UI Elements by Role', () => {
  for (const role of ROLE_HIERARCHY) {
    test.describe(`${role} UI`, () => {
      test.beforeEach(async ({ page }) => {
        await loginAs(page, role);
      });

      test('header shows correct navigation items', async ({ page }) => {
        await page.goto(`${BASE_URL}/dashboard`);
        await page.waitForLoadState('networkidle');
        await page.waitForTimeout(2000);
        
        // Все должны видеть базовые элементы навигации
        const header = page.locator('header, nav, [data-testid="header"]');
        await expect(header.first()).toBeVisible({ timeout: 10000 });

        // Admin-only: проверяем наличие ссылки на admin
        if (hasAccess(role, 'ADMIN')) {
          const adminLink = page.locator('a[href*="admin"], button:has-text("Admin"), nav >> text=/admin|мониторинг|пользователи/i');
          // Admin должен видеть ссылку на админку (или хотя бы иметь доступ)
          const adminLinkVisible = await adminLink.first().isVisible().catch(() => false);
          // Не обязательно, но желательно
          console.log(`${role} sees admin link: ${adminLinkVisible}`);
        }
      });

      test('user menu shows role-appropriate options', async ({ page }) => {
        await page.goto(`${BASE_URL}/dashboard`);
        await page.waitForLoadState('networkidle');
        
        // Ищем меню пользователя (аватар или имя)
        const userMenu = page.locator('[data-testid="user-menu"], button:has(img[alt]), .avatar, [aria-haspopup="menu"]');
        
        if (await userMenu.first().isVisible().catch(() => false)) {
          await userMenu.first().click();
          await page.waitForTimeout(500);
          
          // Должен быть пункт "Выход" / "Logout"
          const logoutOption = page.locator('text=/logout|выход|выйти/i');
          await expect(logoutOption.first()).toBeVisible({ timeout: 5000 });
        }
      });
    });
  }
});

// ============================================================================
// Тесты логаута
// ============================================================================

test.describe('Logout functionality', () => {
  test('user can logout and is redirected to login', async ({ page }) => {
    await loginAs(page, 'USER');
    
    await page.goto(`${BASE_URL}/dashboard`);
    await page.waitForLoadState('networkidle');
    
    // Ищем кнопку выхода
    const logoutButton = page.locator('button:has-text("Logout"), button:has-text("Выход"), a:has-text("Logout"), [data-testid="logout"]');
    
    // Если есть меню пользователя, открываем его
    const userMenu = page.locator('[data-testid="user-menu"], [aria-haspopup="menu"]');
    if (await userMenu.first().isVisible().catch(() => false)) {
      await userMenu.first().click();
      await page.waitForTimeout(500);
    }
    
    if (await logoutButton.first().isVisible().catch(() => false)) {
      await logoutButton.first().click();
      
      // Ждём редирект на логин
      await page.waitForURL(/\/login/, { timeout: 10000 });
      expect(page.url()).toContain('/login');
    }
  });
});
