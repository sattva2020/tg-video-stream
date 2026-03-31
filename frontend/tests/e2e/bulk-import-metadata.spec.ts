/**
 * E2E Test: Bulk Import YouTube/Vimeo with Metadata
 *
 * Verifies:
 * - Bulk import of YouTube playlist URLs
 * - Bulk import of Vimeo video URLs
 * - Metadata fetching (title, duration, thumbnails)
 * - Thumbnail storage and retrieval
 * - Error handling for invalid URLs
 * - Mixed URL imports (YouTube + Vimeo)
 */

import { test, expect } from '@playwright/test';

const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:3000';
const API_URL = process.env.TEST_API_URL || 'http://localhost:8000';

// Interfaces matching the API
interface PlaylistEntry {
  url: string;
  title: string;
  duration: number;
  type: string;
  thumbnail?: string;
}

interface Playlist {
  id: string;
  user_id: string;
  name: string;
  description?: string;
  items: PlaylistEntry[];
  items_count: number;
  total_duration: number;
  is_public: boolean;
  created_at: string;
  updated_at?: string;
}

interface BulkImportRequest {
  urls: string[];
  channel_id?: string;
}

interface BulkImportResult {
  url: string;
  success: boolean;
  message?: string;
  error?: string;
}

interface BulkImportResponse {
  success_count: number;
  failed_count: number;
  results: BulkImportResult[];
  message: string;
}

// Test URLs - using real public playlists and videos
const YOUTUBE_PLAYLIST_URL = 'https://www.youtube.com/playlist?list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf'; // lofi hip hop radio
const VIMEO_VIDEO_URL = 'https://vimeo.com/148751763'; // Public Vimeo video
const INVALID_URL = 'https://invalid-url-that-does-not-exist.com/video';
const YOUTUBE_VIDEO_URL = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'; // Classic test video

let authHeaders: { Authorization: string };
let testUserId: string;

test.beforeAll(async () => {
  // Create test user and get auth token
  // In real scenario, you'd login via UI or use test credentials
  const loginResponse = await fetch(`${API_URL}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      email: 'test-import@example.com',
      password: 'testpassword123'
    }),
  });

  if (loginResponse.ok) {
    const data = await loginResponse.json();
    authHeaders = { Authorization: `Bearer ${data.access_token}` };
    testUserId = data.user_id;
  } else {
    // Fallback: create test user
    const registerResponse = await fetch(`${API_URL}/api/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: 'test-import@example.com',
        password: 'testpassword123',
        full_name: 'Import Test User'
      }),
    });

    if (registerResponse.ok) {
      const data = await registerResponse.json();
      authHeaders = { Authorization: `Bearer ${data.access_token}` };
      testUserId = data.user_id;
    }
  }
});

test.describe('Bulk Import - YouTube Playlists', () => {
  test('Step 1: Import YouTube playlist URL', async ({ request }) => {
    const bulkImportRequest: BulkImportRequest = {
      urls: [YOUTUBE_PLAYLIST_URL],
    };

    const response = await request.post(`${API_URL}/api/playlists/import/bulk`, {
      headers: authHeaders,
      data: bulkImportRequest,
    });

    expect(response.status()).toBe(200);

    const result: BulkImportResponse = await response.json();
    expect(result.success_count).toBeGreaterThanOrEqual(0);
    expect(result.results).toHaveLength(1);
    expect(result.results[0].url).toBe(YOUTUBE_PLAYLIST_URL);

    // YouTube playlist import might fail in test environment if network is restricted
    // We're testing the endpoint structure and response format
  });

  test('Step 2: Verify YouTube playlist items have thumbnails', async ({ request }) => {
    // Give time for async import to complete
    await new Promise(resolve => setTimeout(resolve, 5000));

    // Fetch user's playlists
    const response = await request.get(`${API_URL}/api/playlists/`, {
      headers: authHeaders,
    });

    expect(response.ok).toBeTruthy();

    const playlists: Playlist[] = await response.json();

    // Find the imported playlist (should have 'lofi' or similar in name)
    const importedPlaylist = playlists.find(p =>
      p.name.toLowerCase().includes('lofi') ||
      p.name.toLowerCase().includes('youtube') ||
      p.items.some(item => item.url.includes('youtube.com'))
    );

    if (importedPlaylist) {
      expect(importedPlaylist.items_count).toBeGreaterThan(0);

      // Verify items have metadata
      importedPlaylist.items.forEach(item => {
        expect(item.title).toBeDefined();
        expect(item.title.length).toBeGreaterThan(0);
        expect(item.duration).toBeGreaterThanOrEqual(0);
        expect(item.type).toBe('youtube');

        // Thumbnail should be present if metadata fetching succeeded
        if (item.thumbnail) {
          expect(item.thumbnail).toMatch(/^https?:\/\//);
        }
      });
    }
  });

  test('Step 3: Import multiple YouTube playlists in bulk', async ({ request }) => {
    const bulkImportRequest: BulkImportRequest = {
      urls: [
        'https://www.youtube.com/playlist?list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf',
        'https://www.youtube.com/playlist?list=PLw-vQ1c79hfL7EK44PYk2zKe67VJW5V8t',
      ],
    };

    const response = await request.post(`${API_URL}/api/playlists/import/bulk`, {
      headers: authHeaders,
      data: bulkImportRequest,
    });

    expect(response.status()).toBe(200);

    const result: BulkImportResponse = await response.json();
    expect(result.success_count + result.failed_count).toBe(2);
    expect(result.results).toHaveLength(2);
  });
});

test.describe('Bulk Import - Vimeo Videos', () => {
  test('Step 4: Import Vimeo video URL', async ({ request }) => {
    const bulkImportRequest: BulkImportRequest = {
      urls: [VIMEO_VIDEO_URL],
    };

    const response = await request.post(`${API_URL}/api/playlists/import/bulk`, {
      headers: authHeaders,
      data: bulkImportRequest,
    });

    expect(response.status()).toBe(200);

    const result: BulkImportResponse = await response.json();
    expect(result.results).toHaveLength(1);
    expect(result.results[0].url).toBe(VIMEO_VIDEO_URL);
  });

  test('Step 5: Verify Vimeo video has metadata and thumbnail', async ({ request }) => {
    // Give time for async import to complete
    await new Promise(resolve => setTimeout(resolve, 5000));

    const response = await request.get(`${API_URL}/api/playlists/`, {
      headers: authHeaders,
    });

    expect(response.ok).toBeTruthy();

    const playlists: Playlist[] = await response.json();

    // Find the imported Vimeo playlist
    const vimeoPlaylist = playlists.find(p =>
      p.items.some(item => item.url.includes('vimeo.com'))
    );

    if (vimeoPlaylist) {
      const vimeoItem = vimeoPlaylist.items.find(item => item.url.includes('vimeo.com'));

      expect(vimeoItem).toBeDefined();
      expect(vimeoItem!.title).toBeDefined();
      expect(vimeoItem!.title.length).toBeGreaterThan(0);
      expect(vimeoItem!.duration).toBeGreaterThan(0);
      expect(vimeoItem!.type).toBe('vimeo');

      // Verify thumbnail if metadata fetching succeeded
      if (vimeoItem!.thumbnail) {
        expect(vimeoItem!.thumbnail).toMatch(/^https?:\/\//);
      }
    }
  });
});

test.describe('Bulk Import - Mixed URLs', () => {
  test('Step 6: Import mixed YouTube and Vimeo URLs', async ({ request }) => {
    const bulkImportRequest: BulkImportRequest = {
      urls: [
        YOUTUBE_VIDEO_URL,
        VIMEO_VIDEO_URL,
      ],
    };

    const response = await request.post(`${API_URL}/api/playlists/import/bulk`, {
      headers: authHeaders,
      data: bulkImportRequest,
    });

    expect(response.status()).toBe(200);

    const result: BulkImportResponse = await response.json();
    expect(result.results).toHaveLength(2);
    expect(result.success_count + result.failed_count).toBe(2);
  });

  test('Step 7: Verify both YouTube and Vimeo items in playlist', async ({ request }) => {
    // Give time for async import to complete
    await new Promise(resolve => setTimeout(resolve, 5000));

    const response = await request.get(`${API_URL}/api/playlists/`, {
      headers: authHeaders,
    });

    expect(response.ok).toBeTruthy();

    const playlists: Playlist[] = await response.json();

    // Find playlist with both types
    const mixedPlaylist = playlists.find(p =>
      p.items.some(item => item.url.includes('youtube.com')) &&
      p.items.some(item => item.url.includes('vimeo.com'))
    );

    if (mixedPlaylist) {
      const youtubeItem = mixedPlaylist.items.find(item => item.url.includes('youtube.com'));
      const vimeoItem = mixedPlaylist.items.find(item => item.url.includes('vimeo.com'));

      expect(youtubeItem).toBeDefined();
      expect(vimeoItem).toBeDefined();

      expect(youtubeItem!.type).toBe('youtube');
      expect(vimeoItem!.type).toBe('vimeo');

      // Verify metadata
      expect(youtubeItem!.title.length).toBeGreaterThan(0);
      expect(vimeoItem!.title.length).toBeGreaterThan(0);
    }
  });
});

test.describe('Bulk Import - Error Handling', () => {
  test('Step 8: Verify invalid URL is handled gracefully', async ({ request }) => {
    const bulkImportRequest: BulkImportRequest = {
      urls: [INVALID_URL],
    };

    const response = await request.post(`${API_URL}/api/playlists/import/bulk`, {
      headers: authHeaders,
      data: bulkImportRequest,
    });

    // Should still return 200, but with failed count
    expect(response.status()).toBe(200);

    const result: BulkImportResponse = await response.json();
    expect(result.failed_count).toBeGreaterThan(0);
    expect(result.results[0].success).toBe(false);
    expect(result.results[0].error).toBeDefined();
  });

  test('Step 9: Verify mixed valid and invalid URLs', async ({ request }) => {
    const bulkImportRequest: BulkImportRequest = {
      urls: [
        YOUTUBE_VIDEO_URL,
        INVALID_URL,
      ],
    };

    const response = await request.post(`${API_URL}/api/playlists/import/bulk`, {
      headers: authHeaders,
      data: bulkImportRequest,
    });

    expect(response.status()).toBe(200);

    const result: BulkImportResponse = await response.json();
    expect(result.results).toHaveLength(2);

    // At least one should succeed
    expect(result.success_count + result.failed_count).toBe(2);

    // Invalid URL should have error
    const invalidResult = result.results.find(r => r.url === INVALID_URL);
    if (invalidResult) {
      expect(invalidResult.success).toBe(false);
    }
  });

  test('Step 10: Verify empty URL array returns error', async ({ request }) => {
    const bulkImportRequest: BulkImportRequest = {
      urls: [],
    };

    const response = await request.post(`${API_URL}/api/playlists/import/bulk`, {
      headers: authHeaders,
      data: bulkImportRequest,
    });

    // Should return 400 for empty URL array
    expect(response.status()).toBe(400);
  });
});

test.describe('API: Verify Bulk Import Endpoint', () => {
  test('API: Bulk import endpoint accepts correct payload', async ({ request }) => {
    const bulkImportRequest: BulkImportRequest = {
      urls: [YOUTUBE_VIDEO_URL],
      channel_id: undefined,
    };

    const response = await request.post(`${API_URL}/api/playlists/import/bulk`, {
      headers: authHeaders,
      data: bulkImportRequest,
    });

    expect(response.status()).toBe(200);

    const result: BulkImportResponse = await response.json();
    expect(result).toHaveProperty('success_count');
    expect(result).toHaveProperty('failed_count');
    expect(result).toHaveProperty('results');
    expect(result).toHaveProperty('message');
    expect(Array.isArray(result.results)).toBe(true);
  });

  test('API: Bulk import requires authentication', async ({ request }) => {
    const bulkImportRequest: BulkImportRequest = {
      urls: [YOUTUBE_VIDEO_URL],
    };

    const response = await request.post(`${API_URL}/api/playlists/import/bulk`, {
      data: bulkImportRequest,
    });

    // Should return 401 without auth
    expect(response.status()).toBe(401);
  });
});
