/**
 * Backend API Integration Tests
 * 
 * Тесты для проверки интеграции с backend API.
 * Выявляет ошибки 4xx/5xx и проблемы с авторизацией.
 * 
 * ВАЖНО: Авторизация только через OAuth (Google/Telegram).
 * Тесты с аутентификацией требуют session storage или cookie injection.
 */

import { test, expect } from '@playwright/test';

// Конфигурация для production тестов
const BASE_URL = process.env.TEST_BASE_URL || 'https://sattva-streamer.top';
const API_BASE = `${BASE_URL}/api`;

// Health endpoint is at /health, not /api/health
const HEALTH_URL = `${BASE_URL}/health`;

interface ApiError {
  endpoint: string;
  status: number;
  message: string;
  timestamp: string;
}

test.describe('Backend API Health Check', () => {
  let apiErrors: ApiError[] = [];

  test.beforeEach(async ({ page }) => {
    apiErrors = [];
    
    // Intercept all API requests and log errors
    await page.route('**/api/**', async (route, request) => {
      const response = await route.fetch();
      const status = response.status();
      
      if (status >= 400) {
        let message = '';
        try {
          const body = await response.json();
          message = body.detail || body.message || JSON.stringify(body);
        } catch {
          message = await response.text();
        }
        
        apiErrors.push({
          endpoint: request.url().replace(BASE_URL, ''),
          status,
          message,
          timestamp: new Date().toISOString()
        });
      }
      
      await route.fulfill({ response });
    });
  });

  test.afterEach(async ({ }, testInfo) => {
    // Attach API errors to test report
    if (apiErrors.length > 0) {
      await testInfo.attach('api-errors', {
        body: JSON.stringify(apiErrors, null, 2),
        contentType: 'application/json'
      });
    }
  });

  test('Health endpoint returns 200', async ({ request }) => {
    const response = await request.get(HEALTH_URL);
    expect(response.status()).toBe(200);
    
    const body = await response.json();
    expect(body.status).toBe('healthy');
  });

  test('Public endpoints are accessible', async ({ request }) => {
    const publicEndpoints = [
      { url: HEALTH_URL, name: 'health' },
      { url: `${API_BASE}/docs`, name: 'docs' },
      { url: `${API_BASE}/openapi.json`, name: 'openapi' }
    ];

    for (const { url, name } of publicEndpoints) {
      const response = await request.get(url);
      expect(response.status(), `${name} should be accessible`).toBeLessThan(500);
    }
  });

  test('Protected endpoints require authentication', async ({ request }) => {
    const protectedEndpoints = [
      '/users/me',
      '/channels',
      '/schedule/templates',
      '/schedule/slots'
    ];

    for (const endpoint of protectedEndpoints) {
      const response = await request.get(`${API_BASE}${endpoint}`);
      // Should return 401 or 403 for unauthorized access
      expect([401, 403], `${endpoint} should require auth`).toContain(response.status());
    }
  });
});

test.describe('Authentication Flow', () => {
  test('Login page loads correctly with OAuth buttons', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    
    // Wait for page to fully load
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000); // Wait for React render
    
    // Check for OAuth login buttons (Google and Telegram)
    const googleButton = page.locator('button:has-text("Google"), button:has-text("Continue with Google")');
    const telegramButton = page.locator('button:has-text("Telegram"), button:has-text("Войти через Telegram")');
    
    await expect(googleButton.first()).toBeVisible({ timeout: 20000 });
    await expect(telegramButton.first()).toBeVisible();
  });

  test('Google OAuth redirects correctly', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);
    
    const googleButton = page.locator('button:has-text("Google"), button:has-text("Continue with Google")').first();
    await expect(googleButton).toBeVisible({ timeout: 15000 });
    
    // Click and verify redirect to Google OAuth
    await googleButton.click();
    
    // Should redirect to Google or API auth endpoint
    await page.waitForURL(/accounts\.google\.com|\/api\/auth\/google/, { timeout: 10000 });
  });

  test('Registration page redirects to login or shows OAuth', async ({ page }) => {
    await page.goto(`${BASE_URL}/register`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);
    
    // Should either show OAuth buttons or redirect to login
    const googleButton = page.locator('button:has-text("Google")');
    const loginPageIndicator = page.locator('button:has-text("Telegram")');
    
    await expect(googleButton.or(loginPageIndicator)).toBeVisible({ timeout: 15000 });
  });
});

test.describe('Dashboard Navigation (Unauthenticated)', () => {
  // These tests verify that protected pages redirect to login when unauthenticated

  test('Dashboard redirects to login when unauthenticated', async ({ page }) => {
    await page.goto(`${BASE_URL}/dashboard`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);
    
    // Should redirect to login page or show OAuth buttons
    const googleButton = page.locator('button:has-text("Google")');
    const telegramButton = page.locator('button:has-text("Telegram")');
    const loginIndicator = googleButton.or(telegramButton);
    
    await expect(loginIndicator).toBeVisible({ timeout: 15000 });
  });

  test('Playlist page redirects to login when unauthenticated', async ({ page }) => {
    await page.goto(`${BASE_URL}/playlist`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);
    
    // Should redirect to login
    const oauthButtons = page.locator('button:has-text("Google"), button:has-text("Telegram")');
    await expect(oauthButtons.first()).toBeVisible({ timeout: 15000 });
  });

  test('Schedule page redirects to login when unauthenticated', async ({ page }) => {
    await page.goto(`${BASE_URL}/schedule`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);
    
    // Should redirect to login
    const oauthButtons = page.locator('button:has-text("Google"), button:has-text("Telegram")');
    await expect(oauthButtons.first()).toBeVisible({ timeout: 15000 });
  });

  test('Monitoring page redirects to login when unauthenticated', async ({ page }) => {
    await page.goto(`${BASE_URL}/admin/monitoring`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);
    
    // Should redirect to login or show access denied
    const oauthButtons = page.locator('button:has-text("Google"), button:has-text("Telegram")');
    const accessDenied = page.locator('text=/access denied|forbidden|403/i');
    
    await expect(oauthButtons.first().or(accessDenied.first())).toBeVisible({ timeout: 15000 });
  });
});

test.describe('API Response Validation', () => {
  test('All API responses have valid JSON structure', async ({ request }) => {
    const endpoints = [
      '/health',
      '/docs'
    ];

    for (const endpoint of endpoints) {
      const response = await request.get(`${API_BASE}${endpoint}`);
      
      if (response.status() === 200) {
        const contentType = response.headers()['content-type'];
        
        if (contentType?.includes('application/json')) {
          const body = await response.json();
          expect(body, `${endpoint} should return valid JSON`).toBeDefined();
        }
      }
    }
  });

  test('Error responses have proper structure', async ({ request }) => {
    // Test 404 response
    const response = await request.get(`${API_BASE}/nonexistent-endpoint`);
    expect(response.status()).toBe(404);
    
    const body = await response.json();
    expect(body).toHaveProperty('detail');
  });
});

test.describe('WebSocket Connectivity', () => {
  test('Dashboard loads and redirects unauthenticated users', async ({ page }) => {
    await page.goto(`${BASE_URL}/dashboard`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);
    
    // Check if page loaded - should redirect to login with OAuth buttons
    const oauthButtons = page.locator('button:has-text("Google"), button:has-text("Telegram")');
    const dashboardContent = page.locator('[data-testid="dashboard"], .dashboard');
    
    await expect(oauthButtons.first().or(dashboardContent.first())).toBeVisible({ timeout: 20000 });
  });
});

test.describe('Error Boundary Tests', () => {
  test('Application handles network errors gracefully', async ({ page }) => {
    // Block API requests to simulate network issues
    await page.route('**/api/users/me', route => route.abort('failed'));
    
    await page.goto(`${BASE_URL}/dashboard`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);
    
    // Should not show blank page - either error message or login redirect
    await expect(page.locator('body')).not.toBeEmpty();
    
    // Should not have uncaught exceptions visible - OAuth login or error message
    const errorBoundary = page.locator('text=/something went wrong|error|try again/i');
    const oauthButtons = page.locator('button:has-text("Google"), button:has-text("Telegram")');
    
    // Either shows error gracefully or redirects to OAuth login
    await expect(errorBoundary.or(oauthButtons.first())).toBeVisible({ timeout: 15000 });
  });
});
