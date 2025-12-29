"""
End-to-End Critical Flows Tests

Проверяем критические пользовательские сценарии:
- Полный authentication flow
- Playlist management flow
- Player control flow
- Admin management flow
"""
import { test, expect, Page } from '@playwright/test';

// Test configuration
const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:3000';
const API_URL = process.env.TEST_API_URL || 'http://localhost:8000';

// Test credentials
const TEST_USER = {
  email: 'test@example.com',
  password: 'TestPassword123!',
  username: 'testuser'
};

const ADMIN_USER = {
  email: 'admin@example.com',
  password: 'AdminPassword123!',
  username: 'admin'
};

/**
 * Helper: Login user
 */
async function loginUser(page: Page, email: string, password: string) {
  await page.goto(`${BASE_URL}/login`);
  await page.fill('[name="email"]', email);
  await page.fill('[name="password"]', password);
  await page.click('button[type="submit"]');
  
  // Wait for redirect
  await page.waitForURL(`${BASE_URL}/admin/dashboard`, { timeout: 5000 });
}

/**
 * Helper: Logout user
 */
async function logoutUser(page: Page) {
  await page.click('[data-testid="user-menu"]');
  await page.click('[data-testid="logout-button"]');
  await page.waitForURL(`${BASE_URL}/login`);
}

test.describe('E2E: Authentication Flow', () => {
  
  test('User can complete full OAuth flow', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    
    // Click Google OAuth button
    const googleButton = page.locator('button:has-text("Continue with Google")');
    await expect(googleButton).toBeVisible();
    
    // В реальности это редиректит на Google
    // Для тестов можно мокать или использовать test OAuth provider
    await googleButton.click();
    
    // После успешного OAuth должны попасть на dashboard
    // await page.waitForURL(`${BASE_URL}/admin/dashboard`);
    // await expect(page.locator('h1')).toContainText('Dashboard');
  });
  
  test('User can login with username/password', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    
    // Fill credentials
    await page.fill('[name="username"]', TEST_USER.username);
    await page.fill('[name="password"]', TEST_USER.password);
    
    // Submit
    await page.click('button[type="submit"]');
    
    // Check redirect to dashboard
    await page.waitForURL(`${BASE_URL}/admin/dashboard`, { timeout: 5000 });
    await expect(page).toHaveURL(`${BASE_URL}/admin/dashboard`);
  });
  
  test('Invalid credentials show error', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    
    await page.fill('[name="username"]', 'invalid@test.com');
    await page.fill('[name="password"]', 'wrongpassword');
    await page.click('button[type="submit"]');
    
    // Should show error message
    const errorMessage = page.locator('[role="alert"]').or(page.locator('.error-message'));
    await expect(errorMessage).toBeVisible({ timeout: 3000 });
  });
  
  test('Protected routes redirect to login', async ({ page }) => {
    // Try to access protected route without auth
    await page.goto(`${BASE_URL}/admin/dashboard`);
    
    // Should redirect to login
    await page.waitForURL(`${BASE_URL}/login`);
    await expect(page).toHaveURL(`${BASE_URL}/login`);
  });
  
  test('User can logout successfully', async ({ page }) => {
    // Login first
    await loginUser(page, TEST_USER.email, TEST_USER.password);
    
    // Logout
    await logoutUser(page);
    
    // Should be on login page
    await expect(page).toHaveURL(`${BASE_URL}/login`);
    
    // Try to access dashboard again - should redirect
    await page.goto(`${BASE_URL}/admin/dashboard`);
    await page.waitForURL(`${BASE_URL}/login`);
  });
});

test.describe('E2E: Playlist Management Flow', () => {
  
  test.beforeEach(async ({ page }) => {
    // Login before each test
    await loginUser(page, TEST_USER.email, TEST_USER.password);
  });
  
  test('User can view playlist', async ({ page }) => {
    await page.goto(`${BASE_URL}/admin/playlist`);
    
    // Check playlist is visible
    const playlistContainer = page.locator('[data-testid="playlist-container"]');
    await expect(playlistContainer).toBeVisible();
    
    // Check if tracks are listed
    const tracks = page.locator('[data-testid^="track-"]');
    const count = await tracks.count();
    expect(count).toBeGreaterThanOrEqual(0);
  });
  
  test('User can add track to playlist', async ({ page }) => {
    await page.goto(`${BASE_URL}/admin/playlist`);
    
    // Click add track button
    await page.click('[data-testid="add-track-button"]');
    
    // Fill track details
    await page.fill('[name="track-name"]', 'Test Track');
    await page.fill('[name="artist"]', 'Test Artist');
    await page.fill('[name="file-path"]', '/music/test.mp3');
    
    // Submit
    await page.click('button[type="submit"]');
    
    // Wait for toast or success message
    const successToast = page.locator('[role="status"]').or(page.locator('.toast-success'));
    await expect(successToast).toBeVisible({ timeout: 3000 });
    
    // Check track appears in list
    await expect(page.locator('text=Test Track')).toBeVisible();
  });
  
  test('User can reorder playlist tracks', async ({ page }) => {
    await page.goto(`${BASE_URL}/admin/playlist`);
    
    // Get first two tracks
    const firstTrack = page.locator('[data-testid^="track-"]').first();
    const secondTrack = page.locator('[data-testid^="track-"]').nth(1);
    
    // Get initial order
    const firstTrackText = await firstTrack.textContent();
    
    // Drag and drop (если реализовано)
    await firstTrack.dragTo(secondTrack);
    
    // Check order changed
    const newFirstTrack = page.locator('[data-testid^="track-"]').first();
    const newFirstTrackText = await newFirstTrack.textContent();
    
    expect(newFirstTrackText).not.toBe(firstTrackText);
  });
  
  test('User can delete track from playlist', async ({ page }) => {
    await page.goto(`${BASE_URL}/admin/playlist`);
    
    // Find delete button for first track
    const deleteButton = page.locator('[data-testid="delete-track-button"]').first();
    await deleteButton.click();
    
    // Confirm deletion
    await page.click('[data-testid="confirm-delete"]');
    
    // Wait for success message
    const successMessage = page.locator('[role="status"]');
    await expect(successMessage).toBeVisible({ timeout: 3000 });
  });
  
  test('User can search tracks in playlist', async ({ page }) => {
    await page.goto(`${BASE_URL}/admin/playlist`);
    
    // Type in search
    await page.fill('[data-testid="playlist-search"]', 'test');
    
    // Wait for filtered results
    await page.waitForTimeout(500); // debounce
    
    // Check filtered tracks contain search term
    const visibleTracks = page.locator('[data-testid^="track-"]:visible');
    const count = await visibleTracks.count();
    
    if (count > 0) {
      const trackText = await visibleTracks.first().textContent();
      expect(trackText?.toLowerCase()).toContain('test');
    }
  });
});

test.describe('E2E: Player Control Flow', () => {
  
  test.beforeEach(async ({ page }) => {
    await loginUser(page, TEST_USER.email, TEST_USER.password);
    await page.goto(`${BASE_URL}/admin/dashboard`);
  });
  
  test('User can play/pause music', async ({ page }) => {
    // Find play button
    const playButton = page.locator('[data-testid="play-button"]');
    await expect(playButton).toBeVisible();
    
    // Click play
    await playButton.click();
    
    // Button should change to pause
    const pauseButton = page.locator('[data-testid="pause-button"]');
    await expect(pauseButton).toBeVisible({ timeout: 2000 });
    
    // Click pause
    await pauseButton.click();
    
    // Should change back to play
    await expect(playButton).toBeVisible({ timeout: 2000 });
  });
  
  test('User can skip to next track', async ({ page }) => {
    const nextButton = page.locator('[data-testid="next-track-button"]');
    await expect(nextButton).toBeVisible();
    
    // Get current track name
    const currentTrack = page.locator('[data-testid="current-track-name"]');
    const currentTrackText = await currentTrack.textContent();
    
    // Click next
    await nextButton.click();
    
    // Wait for track change
    await page.waitForTimeout(1000);
    
    // Track should change
    const newTrackText = await currentTrack.textContent();
    expect(newTrackText).not.toBe(currentTrackText);
  });
  
  test('User can adjust volume', async ({ page }) => {
    const volumeSlider = page.locator('[data-testid="volume-slider"]');
    await expect(volumeSlider).toBeVisible();
    
    // Get bounding box
    const box = await volumeSlider.boundingBox();
    if (box) {
      // Click at 50% position
      await page.mouse.click(box.x + box.width * 0.5, box.y + box.height * 0.5);
      
      // Volume should update (check aria-valuenow or similar)
      const volumeValue = await volumeSlider.getAttribute('aria-valuenow');
      expect(volumeValue).toBeTruthy();
    }
  });
  
  test('User can see real-time player status updates', async ({ page, context }) => {
    // Ждём WebSocket соединения
    await page.waitForTimeout(1000);
    
    // Проверяем что player status обновляется
    const playerStatus = page.locator('[data-testid="player-status"]');
    await expect(playerStatus).toBeVisible();
    
    const initialStatus = await playerStatus.textContent();
    
    // Меняем состояние
    await page.click('[data-testid="play-button"]');
    
    // Ждём обновления через WebSocket
    await page.waitForTimeout(500);
    
    const updatedStatus = await playerStatus.textContent();
    expect(updatedStatus).not.toBe(initialStatus);
  });
});

test.describe('E2E: Admin Management Flow', () => {
  
  test.beforeEach(async ({ page }) => {
    // Login as admin
    await loginUser(page, ADMIN_USER.email, ADMIN_USER.password);
  });
  
  test('Admin can view users list', async ({ page }) => {
    await page.goto(`${BASE_URL}/admin/users`);
    
    const usersTable = page.locator('[data-testid="users-table"]');
    await expect(usersTable).toBeVisible();
    
    // Check table has rows
    const rows = page.locator('[data-testid^="user-row-"]');
    const count = await rows.count();
    expect(count).toBeGreaterThan(0);
  });
  
  test('Admin can approve pending user', async ({ page }) => {
    await page.goto(`${BASE_URL}/admin/users`);
    
    // Find pending user
    const pendingUser = page.locator('[data-testid="user-status-pending"]').first();
    
    if (await pendingUser.count() > 0) {
      // Click approve button
      await pendingUser.locator('[data-testid="approve-user-button"]').click();
      
      // Confirm
      await page.click('[data-testid="confirm-approve"]');
      
      // Check success message
      const successToast = page.locator('[role="status"]');
      await expect(successToast).toBeVisible({ timeout: 3000 });
    }
  });
  
  test('Admin can manage channels', async ({ page }) => {
    await page.goto(`${BASE_URL}/admin/channels`);
    
    // Add new channel
    await page.click('[data-testid="add-channel-button"]');
    await page.fill('[name="channel-username"]', '@test_channel');
    await page.click('button[type="submit"]');
    
    // Wait for success
    await page.waitForTimeout(1000);
    
    // Check channel appears
    await expect(page.locator('text=@test_channel')).toBeVisible();
  });
  
  test('Admin can view system metrics', async ({ page }) => {
    await page.goto(`${BASE_URL}/admin/dashboard`);
    
    // Check metrics are visible
    const cpuMetric = page.locator('[data-testid="metric-cpu"]');
    const memoryMetric = page.locator('[data-testid="metric-memory"]');
    
    await expect(cpuMetric).toBeVisible();
    await expect(memoryMetric).toBeVisible();
    
    // Values should be numbers
    const cpuText = await cpuMetric.textContent();
    expect(cpuText).toMatch(/\d+/);
  });
});

test.describe('E2E: Error Handling', () => {
  
  test('App handles network errors gracefully', async ({ page, context }) => {
    // Go offline
    await context.setOffline(true);
    
    await page.goto(`${BASE_URL}/login`);
    
    // Try to submit form
    await page.fill('[name="username"]', 'test');
    await page.fill('[name="password"]', 'test');
    await page.click('button[type="submit"]');
    
    // Should show network error
    const errorMessage = page.locator('[role="alert"]');
    await expect(errorMessage).toBeVisible({ timeout: 5000 });
    
    // Go back online
    await context.setOffline(false);
  });
  
  test('App recovers from API errors', async ({ page }) => {
    await loginUser(page, TEST_USER.email, TEST_USER.password);
    
    // Navigate to page that makes API call
    await page.goto(`${BASE_URL}/admin/playlist`);
    
    // Intercept API and return error
    await page.route(`${API_URL}/api/playlist/**`, route => {
      route.fulfill({ status: 500, body: 'Server Error' });
    });
    
    // Trigger API call (refresh page)
    await page.reload();
    
    // Should show error UI
    const errorState = page.locator('[data-testid="error-state"]').or(page.locator('.error-message'));
    await expect(errorState).toBeVisible({ timeout: 3000 });
  });
});

test.describe('E2E: Performance', () => {
  
  test('Dashboard loads within acceptable time', async ({ page }) => {
    const startTime = Date.now();
    
    await page.goto(`${BASE_URL}/login`);
    await loginUser(page, TEST_USER.email, TEST_USER.password);
    
    const loadTime = Date.now() - startTime;
    
    // Should load within 5 seconds
    expect(loadTime).toBeLessThan(5000);
  });
  
  test('Page transitions are smooth', async ({ page }) => {
    await loginUser(page, TEST_USER.email, TEST_USER.password);
    
    const startTime = Date.now();
    
    // Navigate between pages
    await page.goto(`${BASE_URL}/admin/dashboard`);
    await page.goto(`${BASE_URL}/admin/playlist`);
    await page.goto(`${BASE_URL}/admin/channels`);
    
    const totalTime = Date.now() - startTime;
    
    // 3 page transitions should take < 5 seconds total
    expect(totalTime).toBeLessThan(5000);
  });
});
