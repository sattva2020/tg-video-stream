import { test, expect } from '@playwright/test';

test.describe('User approval flow (frontend)', () => {
  test('Signup shows pending message', async ({ page }) => {
    await page.route('**/api/auth/register', async route => {
      await route.fulfill({ json: { status: 'pending', message: 'Account created and awaiting administrator approval' } });
    });

    await page.goto('/register');
    // Fill form
    await page.fill('input[placeholder="Email"]', 'pending.test@example.com');
    await page.fill('input[placeholder="Password"]', 'GoodPassword123!');
    await page.fill('input[placeholder="Confirm password"]', 'GoodPassword123!');
    await page.click('button[type="submit"]');

    // Expect pending message
    await expect(page.getByText('Account created and awaiting administrator approval')).toBeVisible();
  });

  test('Admin approves user and user can login afterwards (mocked)', async ({ page }) => {
    // Simulate successful register
    await page.route('**/api/auth/register', async route => {
      await route.fulfill({ json: { status: 'pending', message: 'Account created and awaiting administrator approval' } });
    });

    // Mock admin endpoints
    await page.route('**/api/admin/users?status=pending', async route => {
      await route.fulfill({ json: [{ id: 'u-1', email: 'pending.test@example.com', status: 'pending' }] });
    });
    await page.route('**/api/admin/users/u-1/approve', async route => {
      await route.fulfill({ json: { status: 'ok', id: 'u-1', new_status: 'approved' } });
    });

    // Mock login endpoint to succeed after approval
    await page.route('**/api/auth/login', async route => {
      await route.fulfill({ json: { access_token: 'fake-token', token_type: 'bearer' } });
    });

    // Register
    await page.goto('/register');
    await page.fill('input[placeholder="Email"]', 'pending.test@example.com');
    await page.fill('input[placeholder="Password"]', 'GoodPassword123!');
    await page.fill('input[placeholder="Confirm password"]', 'GoodPassword123!');
    await page.click('button[type="submit"]');

    // Go to admin pending page
    await page.goto('/admin/pending');

    // Approve
    await page.click('text=Утвердить');

    // Now attempt login
    await page.goto('/login');
    await page.fill('input[type="email"]', 'pending.test@example.com');
    await page.fill('input[type="password"]', 'GoodPassword123!');
    await page.click('button[type="submit"]');

    // Should navigate to dashboard (mocked token leads to dashboard content)
    await page.waitForURL('/dashboard');
  });
});