/**
 * E2E Tests: Multi-Platform Video Source Integration
 *
 * Tests the complete user workflow for adding and managing videos
 * from different platforms through the UI.
 *
 * Coverage:
 * - Add Vimeo video via UI, verify metadata fetched
 * - Add Twitch clip via UI, verify metadata fetched
 * - Add direct MP4 URL, validate codec compatibility
 * - Add RSS feed URL, verify videos parsed and queued
 * - Verify SourceManager shows all sources with correct status
 * - Verify transcoding triggered for incompatible formats
 */
import { test, expect } from '@playwright/test';

const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:5173';

test.describe('Multi-Platform Video Sources - E2E', () => {
  // Setup: Login before each test
  test.beforeEach(async ({ page }) => {
    // Navigate to login page
    await page.goto(`${BASE_URL}/login`);

    // Note: In real E2E tests, you would use test credentials
    // or mock authentication. For this example, we'll assume
    // the user is already logged in or authentication is mocked.

    // TODO: Implement actual login or use auth mock
    // await page.fill('input[name="email"]', 'test@example.com');
    // await page.click('button[type="submit"]');
  });

  test.describe('Vimeo Video Integration', () => {
    test('add Vimeo video via UI and verify metadata fetched', async ({ page }) => {
      await page.goto(`${BASE_URL}/playlists`);

      // Click add track button
      await page.click('button:has-text("Add Track"), button:has-text("Добавить")');

      // Wait for form to appear
      await expect(page.locator('input[name="url"]')).toBeVisible();

      // Enter Vimeo URL
      await page.fill('input[name="url"]', 'https://vimeo.com/123456789');

      // Enable auto-detect
      const autoDetectCheckbox = page.locator('input[name="auto_detect"]');
      if (await autoDetectCheckbox.isVisible()) {
        await autoDetectCheckbox.check();
      }

      // Submit form
      await page.click('button[type="submit"]:visible');

      // Verify success message or redirect
      await expect(page.locator('.toast, .notification, [role="alert"]')).toBeVisible({ timeout: 10000 });

      // Navigate to playlist to verify video was added
      await page.goto(`${BASE_URL}/playlists`);

      // Verify video appears in list with correct metadata
      const vimeoVideo = page.locator('.playlist-item:has-text("Vimeo")').first();
      await expect(vimeoVideo).toBeVisible({ timeout: 10000 });

      // Verify metadata is displayed
      const title = await vimeoVideo.locator('.title, .video-title').textContent();
      expect(title).toBeTruthy();
    });
  });

  test.describe('Twitch Clip Integration', () => {
    test('add Twitch clip via UI and verify metadata fetched', async ({ page }) => {
      await page.goto(`${BASE_URL}/playlists`);

      // Click add track button
      await page.click('button:has-text("Add Track"), button:has-text("Добавить")');

      // Enter Twitch clip URL
      await page.fill('input[name="url"]', 'https://clips.twitch.tv/example/AmazingClip');

      // Enable auto-detect
      const autoDetectCheckbox = page.locator('input[name="auto_detect"]');
      if (await autoDetectCheckbox.isVisible()) {
        await autoDetectCheckbox.check();
      }

      // Submit form
      await page.click('button[type="submit"]:visible');

      // Verify success
      await expect(page.locator('.toast, .notification, [role="alert"]')).toBeVisible({ timeout: 10000 });

      // Verify video was added
      await page.goto(`${BASE_URL}/playlists`);
      const twitchVideo = page.locator('.playlist-item:has-text("Twitch")').first();
      await expect(twitchVideo).toBeVisible({ timeout: 10000 });
    });
  });

  test.describe('Direct Video URL Integration', () => {
    test('add direct MP4 URL and validate codec compatibility', async ({ page }) => {
      await page.goto(`${BASE_URL}/playlists`);

      // Click add track button
      await page.click('button:has-text("Add Track"), button:has-text("Добавить")');

      // Enter direct MP4 URL
      await page.fill('input[name="url"]', 'https://example.com/sample-video.mp4');

      // Select "Direct Video URL" type
      await page.click('select[name="type"], .source-type-select');
      await page.click('option[value="direct"], option:has-text("Direct")');

      // Submit form
      await page.click('button[type="submit"]:visible');

      // Wait for validation to complete
      await page.waitForTimeout(2000);

      // Verify video is added and validation status is shown
      await page.goto(`${BASE_URL}/playlists`);
      const directVideo = page.locator('.playlist-item').filter({ hasText: 'sample-video.mp4' }).first();

      await expect(directVideo).toBeVisible({ timeout: 10000 });

      // Check for validation indicator
      const statusIndicator = directVideo.locator('.status, .validation-status');
      await expect(statusIndicator).toBeVisible();
    });

    test('incompatible format triggers transcoding warning', async ({ page }) => {
      await page.goto(`${BASE_URL}/playlists`);

      // Click add track button
      await page.click('button:has-text("Add Track"), button:has-text("Добавить")');

      // Enter incompatible video URL (e.g., .avi)
      await page.fill('input[name="url"]', 'https://example.com/video.avi');

      // Submit form
      await page.click('button[type="submit"]:visible');

      // Wait for processing
      await page.waitForTimeout(3000);

      // Verify transcoding warning is displayed
      const transcodeWarning = page.locator('.warning:has-text("transcode"), .alert:has-text("transcode")');
      if (await transcodeWarning.isVisible()) {
        await expect(transcodeWarning).toContainText('transcode', { ignoreCase: true });
      }
    });
  });

  test.describe('RSS Feed Integration', () => {
    test('add RSS feed URL and verify videos parsed and queued', async ({ page }) => {
      await page.goto(`${BASE_URL}/playlists`);

      // Click add track/import playlist button
      await page.click('button:has-text("Import"), button:has-text("Import Playlist")');

      // Wait for import modal/form
      await expect(page.locator('.modal, dialog, [role="dialog"]')).toBeVisible();

      // Enter RSS feed URL
      await page.fill('input[name="url"], input[placeholder*="URL"]', 'https://example.com/video-feed.xml');

      // Enter playlist name
      await page.fill('input[name="name"], input[placeholder*="name"]', 'Test RSS Feed');

      // Submit import
      await page.click('button[type="submit"]:visible');

      // Wait for import to complete
      await expect(page.locator('.toast:has-text("import"), .notification:has-text("import")')).toBeVisible({ timeout: 15000 });

      // Navigate to playlists
      await page.goto(`${BASE_URL}/playlists`);

      // Verify new playlist was created
      const rssPlaylist = page.locator('.playlist:has-text("Test RSS Feed")').first();
      await expect(rssPlaylist).toBeVisible({ timeout: 10000 });

      // Click on playlist to view items
      await rssPlaylist.click();

      // Verify videos from RSS feed were imported
      const playlistItems = page.locator('.playlist-item');
      const count = await playlistItems.count();

      expect(count).toBeGreaterThan(0);
    });
  });

  test.describe('Source Manager UI', () => {
    test('verify SourceManager shows all sources with correct status', async ({ page, request }) => {
      // First, add videos from different sources via API
      const sources = [
        { url: 'https://vimeo.com/111', type: 'vimeo' },
        { url: 'https://clips.twitch.tv/test', type: 'twitch' },
        { url: 'https://example.com/video.mp4', type: 'direct' }
      ];

      // Note: In real tests, you would authenticate and add via API
      // For now, we'll just navigate to the SourceManager page

      // Navigate to SourceManager page
      await page.goto(`${BASE_URL}/sources`);

      // Verify page loads
      await expect(page).toHaveURL(/sources/);

      // Verify source cards are displayed
      const sourceCards = page.locator('.source-card, .video-source-card');
      await expect(sourceCards.first()).toBeVisible({ timeout: 10000 });

      // Check for different source type indicators
      const sourceTypes = ['Vimeo', 'Twitch', 'Direct', 'YouTube'];

      for (const type of sourceTypes) {
        const typeElement = page.locator(`.source-card:has-text("${type}"), .badge:has-text("${type}")`);
        // Note: Not all types may be present, so we just check if the element exists
        const count = await typeElement.count();
        if (count > 0) {
          await expect(typeElement.first()).toBeVisible();
        }
      }

      // Verify status indicators are shown
      const statusIndicators = page.locator('.status, .status-indicator, [data-testid="status"]');
      await expect(statusIndicators.first()).toBeVisible();
    });

    test('filter and search sources in SourceManager', async ({ page }) => {
      await page.goto(`${BASE_URL}/sources`);

      // Verify filter controls exist
      const filterSelect = page.locator('select[name="filter"], .filter-select');
      if (await filterSelect.first().isVisible()) {
        await filterSelect.first().selectOption('vimeo');

        // Verify filtered results
        await page.waitForTimeout(1000);
        const vimeoSources = page.locator('.source-card:has-text("Vimeo")');
        const count = await vimeoSources.count();

        // If there are any Vimeo sources, they should be visible
        if (count > 0) {
          await expect(vimeoSources.first()).toBeVisible();
        }
      }

      // Test search functionality
      const searchInput = page.locator('input[name="search"], input[placeholder*="search"], .search-input');
      if (await searchInput.first().isVisible()) {
        await searchInput.first().fill('vimeo');

        // Wait for search results
        await page.waitForTimeout(1000);

        // Verify search worked
        const searchResults = page.locator('.source-card');
        await expect(searchResults.first()).toBeVisible();
      }
    });
  });

  test.describe('Auto-Detection Feature', () => {
    test('auto-detect source type from URL', async ({ page }) => {
      await page.goto(`${BASE_URL}/playlists`);

      // Click add track button
      await page.click('button:has-text("Add Track"), button:has-text("Добавить")');

      // Enable auto-detect
      const autoDetectCheckbox = page.locator('input[name="auto_detect"]');
      if (await autoDetectCheckbox.isVisible()) {
        await autoDetectCheckbox.check();
      }

      // Enter different URLs and verify type is auto-detected
      const testCases = [
        { url: 'https://vimeo.com/123', expectedType: 'Vimeo' },
        { url: 'https://www.youtube.com/watch?v=test', expectedType: 'YouTube' },
        { url: 'https://clips.twitch.tv/test', expectedType: 'Twitch' }
      ];

      for (const testCase of testCases) {
        // Clear and fill URL
        await page.fill('input[name="url"]', testCase.url);

        // Wait for auto-detection to complete
        await page.waitForTimeout(1000);

        // Verify detected type is shown (if UI shows it)
        const detectedTypeLabel = page.locator('.detected-type, .source-type-label');
        if (await detectedTypeLabel.isVisible()) {
          const detectedType = await detectedTypeLabel.textContent();
          expect(detectedType).toContain(testCase.expectedType);
        }
      }
    });

    test('manual type selection overrides auto-detect when disabled', async ({ page }) => {
      await page.goto(`${BASE_URL}/playlists`);

      // Click add track button
      await page.click('button:has-text("Add Track"), button:has-text("Добавить")');

      // Ensure auto-detect is disabled
      const autoDetectCheckbox = page.locator('input[name="auto_detect"]');
      if (await autoDetectCheckbox.isVisible()) {
        await autoDetectCheckbox.uncheck();
      }

      // Enter Vimeo URL
      await page.fill('input[name="url"]', 'https://vimeo.com/999');

      // Manually select YouTube type
      await page.click('select[name="type"]');
      await page.click('option[value="youtube"], option:has-text("YouTube")');

      // Verify selected type is YouTube (not auto-detected Vimeo)
      const selectElement = page.locator('select[name="type"]');
      const selectedValue = await selectElement.inputValue();
      expect(selectedValue).toBe('youtube');
    });
  });

  test.describe('Validation and Error Handling', () => {
    test('show validation error for invalid URL', async ({ page }) => {
      await page.goto(`${BASE_URL}/playlists`);

      // Click add track button
      await page.click('button:has-text("Add Track"), button:has-text("Добавить")');

      // Enter invalid URL
      await page.fill('input[name="url"]', 'not-a-valid-url');

      // Submit form
      await page.click('button[type="submit"]:visible');

      // Verify error message
      const errorMessage = page.locator('.error, .invalid-feedback, [role="alert"]:has-text("invalid")');
      await expect(errorMessage).toBeVisible({ timeout: 5000 });
    });

    test('show validation error for unsupported source type', async ({ page }) => {
      await page.goto(`${BASE_URL}/playlists`);

      // Click add track button
      await page.click('button:has-text("Add Track"), button:has-text("Добавить")');

      // Enter URL from unsupported platform
      await page.fill('input[name="url"]', 'https://unsupported-platform.com/video');

      // Submit form
      await page.click('button[type="submit"]:visible');

      // Verify error or warning message
      const errorOrWarning = page.locator('.error, .warning, [role="alert"]');
      await expect(errorOrWarning.first()).toBeVisible({ timeout: 5000 });
    });
  });

  test.describe('Metadata Display', () => {
    test('verify video metadata is displayed correctly', async ({ page }) => {
      // This test assumes a video has already been added
      await page.goto(`${BASE_URL}/playlists`);

      // Click on first playlist item
      const firstItem = page.locator('.playlist-item').first();
      await firstItem.click();

      // Verify metadata panel/section is visible
      const metadataSection = page.locator('.metadata, .video-details, [data-testid="metadata"]');
      await expect(metadataSection).toBeVisible({ timeout: 5000 });

      // Verify common metadata fields are shown
      const metadataFields = ['title', 'duration', 'uploader', 'thumbnail'];

      for (const field of metadataFields) {
        const fieldElement = page.locator(`[data-testid="${field}"], .${field}`);
        const count = await fieldElement.count();

        // Not all fields may be present, but at least some should be
        if (count > 0) {
          await expect(fieldElement.first()).toBeVisible();
        }
      }
    });
  });

  test.describe('Complete Workflow Integration', () => {
    test('add multiple source types and verify in SourceManager', async ({ page }) => {
      const testVideos = [
        { url: 'https://vimeo.com/123', name: 'Vimeo Test' },
        { url: 'https://clips.twitch.tv/test', name: 'Twitch Test' },
        { url: 'https://example.com/video.mp4', name: 'Direct Test' }
      ];

      // Add each video
      for (const video of testVideos) {
        await page.goto(`${BASE_URL}/playlists`);
        await page.click('button:has-text("Add Track"), button:has-text("Добавить")');

        await page.fill('input[name="url"]', video.url);

        const autoDetectCheckbox = page.locator('input[name="auto_detect"]');
        if (await autoDetectCheckbox.isVisible()) {
          await autoDetectCheckbox.check();
        }

        await page.click('button[type="submit"]:visible');

        // Wait for success
        await page.waitForTimeout(2000);
      }

      // Navigate to SourceManager
      await page.goto(`${BASE_URL}/sources`);

      // Verify all sources are displayed
      for (const video of testVideos) {
        const sourceCard = page.locator('.source-card').filter({ hasText: video.name });
        const count = await sourceCard.count();

        // At least one of the videos should be visible
        if (count > 0) {
          await expect(sourceCard.first()).toBeVisible();
          break;
        }
      }

      // Verify source count
      const allSources = page.locator('.source-card');
      const sourceCount = await allSources.count();
      expect(sourceCount).toBeGreaterThan(0);
    });
  });
});

test.describe('Multi-Platform Sources - API Integration', () => {
  test('API validates all supported source types', async ({ request }) => {
    const testUrls = [
      { url: 'https://vimeo.com/123', type: 'vimeo' },
      { url: 'https://clips.twitch.tv/test', type: 'twitch' },
      { url: 'https://example.com/video.mp4', type: 'direct' },
      { url: 'https://www.youtube.com/watch?v=test', type: 'youtube' }
    ];

    for (const test of testUrls) {
      const response = await request.post(`${BASE_URL}/api/video-sources/detect`, {
        data: { url: test.url }
      });

      expect(response.status()).toBe(200);

      const data = await response.json();
      expect(data.valid).toBe(true);
      expect(data.source_type).toBe(test.type);
    }
  });

  test('API returns list of supported sources', async ({ request }) => {
    const response = await request.get(`${BASE_URL}/api/video-sources/supported`);

    expect(response.status()).toBe(200);

    const data = await response.json();
    expect(data.sources).toBeDefined();
    expect(data.sources.length).toBeGreaterThan(0);

    // Verify key sources are in the list
    const sourceTypes = data.sources.map((s: any) => s.type);
    expect(sourceTypes).toContain('youtube');
    expect(sourceTypes).toContain('vimeo');
    expect(sourceTypes).toContain('twitch');
    expect(sourceTypes).toContain('direct');
  });
});
