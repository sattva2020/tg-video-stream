import { test, expect } from '@playwright/test';

test.describe('RBAC Access Control', () => {
  test.beforeEach(async ({ page }) => {
    page.on('console', msg => console.log(`BROWSER LOG: ${msg.text()}`));
  });

  test('Admin user should see admin controls', async ({ page }) => {
    // Mock login as admin
    // We need to simulate the auth flow or manually set the token
    // For simplicity, we'll mock the API responses that the AuthContext uses
    
    // Mock /me endpoint to return admin role
    await page.route('**/api/users/me', async route => {
      await route.fulfill({
        json: {
          id: '1',
          email: 'admin@example.com',
          role: 'admin'
        }
      });
    });

    // We also need to mock the login response if we go through the login page
    // Or we can inject the token into localStorage
    
    await page.goto('/login');
    
    // Mock login API
    await page.route('**/api/auth/login', async route => {
      await route.fulfill({
        json: {
          // Valid dummy JWT
          access_token: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwicm9sZSI6ImFkbWluIiwiZXhwIjo5OTk5OTk5OTk5fQ.signature',
          token_type: 'bearer'
        }
      });
    });

    // Fill login form (assuming standard selectors)
    await page.fill('input[type="email"]', 'admin@example.com');
    await page.fill('input[type="password"]', 'password123');
    await page.click('button[type="submit"]');

    // Wait for navigation to dashboard
    await page.waitForURL('/dashboard');
    
    // Wait for user data to load
    await expect(page.getByText('Welcome, admin@example.com!')).toBeVisible();

    // Expect to see "Restart Stream" button
    // This will fail until T021 is implemented
    await expect(page.getByText('Restart Stream')).toBeVisible();
  });

  test('Regular user should NOT see admin controls', async ({ page }) => {
    // Mock /me endpoint to return user role
    await page.route('**/api/users/me', async route => {
      await route.fulfill({
        json: {
          id: '2',
          email: 'user@example.com',
          role: 'user'
        }
      });
    });

    await page.goto('/login');
    
    // Mock login API
    await page.route('**/api/auth/login', async route => {
      await route.fulfill({
        json: {
          // Valid dummy JWT
          access_token: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIyIiwicm9zZSI6InVzZXIiLCJleHAiOjk5OTk5OTk5OTl9.signature',
          token_type: 'bearer'
        }
      });
    });

    // Fill login form
    await page.fill('input[type="email"]', 'user@example.com');
    await page.fill('input[type="password"]', 'password123');
    await page.click('button[type="submit"]');

    // Wait for navigation to dashboard
    await page.waitForURL('/dashboard');
    
    // Expect NOT to see "Restart Stream" button
    await expect(page.getByText('Restart Stream')).not.toBeVisible();
  });
});
