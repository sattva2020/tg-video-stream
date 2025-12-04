import { test, expect } from '@playwright/test';

test.describe('Playlist Status UI', () => {
  test.beforeEach(async ({ page }) => {
    // Mock Auth
    await page.route('**/api/users/me', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'user_123',
          email: 'admin@sattva.studio',
          full_name: 'Admin User',
          role: 'admin',
          status: 'approved'
        })
      });
    });

    // Mock Login if redirected
    await page.route('**/api/auth/login', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ access_token: 'mock_token', token_type: 'bearer' })
      });
    });
  });

  test('TC-PLAYLIST-001 — UI updates when status changes to playing', async ({ page }) => {
    // 1. Setup initial playlist state (queued)
    let playlistData = [
      {
        id: '1',
        url: 'https://example.com/song.mp3',
        title: 'Test Song',
        type: 'audio',
        status: 'queued',
        duration: 120,
        created_at: new Date().toISOString()
      }
    ];

    // Mock playlist endpoint
    // Use regex to match any request containing /api/playlist
    await page.route(/\/api\/playlist/, async route => {
      console.log('Mocking playlist request:', route.request().url());
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(playlistData)
      });
    });

    page.on('console', msg => console.log('PAGE LOG:', msg.text()));
    page.on('requestfailed', request => console.log('REQUEST FAILED:', request.url(), request.failure()?.errorText));
    page.on('request', request => console.log('REQUEST:', request.url()));

    // 2. Navigate to playlist page
    // We might need to set localStorage token manually if the app checks it before /me
    await page.addInitScript(() => {
      const mockJwt = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjMiLCJleHAiOjk5OTk5OTk5OTksInJvbGUiOiJhZG1pbiJ9.dummy_signature';
      localStorage.setItem('token', mockJwt);
    });
    
    await page.goto('/playlist');
    
    // Debug: Check if we are on the right page
    await expect(page).toHaveURL(/playlist/);

    // 3. Verify initial state
    // Wait for loading to finish if it exists
    await expect(page.getByText('Loading…')).not.toBeVisible();

    const item = page.locator('li').filter({ hasText: 'Test Song' });
    await expect(item).toBeVisible();
    await expect(item).toContainText('queued');
    await expect(item).not.toHaveClass(/bg-blue-50/); // Should not be highlighted

    // 4. Update mock data to "playing"
    playlistData = [
      {
        id: '1',
        url: 'https://example.com/song.mp3',
        title: 'Test Song',
        type: 'audio',
        status: 'playing',
        duration: 120,
        created_at: new Date().toISOString()
      }
    ];

    // 5. Wait for polling (POLL_INTERVAL_MS is 3000ms in PlaylistQueue.tsx)
    // We can wait for the response to happen again
    await page.waitForResponse(resp => resp.url().includes('/api/playlist') && resp.status() === 200);
    // Wait for one more poll to be sure, or just wait for the UI update
    await expect(item).toContainText('playing');
    await expect(item).toHaveClass(/bg-blue-50/); // Should be highlighted now

    // 6. Update mock data to "played"
    playlistData = [
      {
        id: '1',
        url: 'https://example.com/song.mp3',
        title: 'Test Song',
        type: 'audio',
        status: 'played',
        duration: 120,
        created_at: new Date().toISOString()
      }
    ];

    await page.waitForResponse(resp => resp.url().includes('/api/playlist') && resp.status() === 200);
    await expect(item).toContainText('played');
    await expect(item).not.toHaveClass(/bg-blue-50/);
  });
});
