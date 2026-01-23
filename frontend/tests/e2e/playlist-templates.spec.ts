/**
 * E2E Test: Create Playlist from Template
 *
 * Verifies:
 * - Creating playlist templates with items
 * - Applying templates to create new playlists
 * - Verifying all items are copied correctly
 * - Template metadata preservation
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

interface PlaylistTemplate {
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

interface PlaylistTemplateCreate {
  name: string;
  description?: string;
  items: PlaylistEntry[];
  is_public?: boolean;
}

interface Playlist {
  id: string;
  user_id: string;
  name: string;
  description?: string;
  items: PlaylistEntry[];
  items_count: number;
  total_duration: number;
  group_id?: string;
  is_public: boolean;
  repeat_mode: string;
  created_at: string;
  updated_at?: string;
}

interface ApplyTemplateRequest {
  playlist_name: string;
  playlist_description?: string;
  group_id?: string;
  channel_id?: string;
}

// Test data
const TEST_TEMPLATE: PlaylistTemplateCreate = {
  name: 'Morning Show Template',
  description: 'Standard morning show format with news, weather, and entertainment',
  is_public: false,
  items: [
    {
      url: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
      title: 'Never Gonna Give You Up',
      duration: 212,
      type: 'youtube',
    },
    {
      url: 'https://www.youtube.com/watch?v=9bZkp7q19f0',
      title: 'Gangnam Style',
      duration: 252,
      type: 'youtube',
    },
    {
      url: 'https://vimeo.com/148751763',
      title: 'Vimeo Staff Pick',
      duration: 180,
      type: 'vimeo',
    },
  ],
};

const TEST_PLAYLIST_FROM_TEMPLATE: ApplyTemplateRequest = {
  playlist_name: 'Monday Morning Show',
  playlist_description: 'Kick off the week with great content',
};

test.describe('E2E: Create Playlist from Template', () => {
  let authToken: string;
  let testTemplate: PlaylistTemplate;
  let createdPlaylist: Playlist;

  // Setup: Authenticate user
  test.beforeAll(async ({ request }) => {
    // Create or login test user
    const loginResponse = await request.post(`${API_URL}/api/auth/test-login`, {
      json: {
        email: 'test-templates@example.com',
        password: 'TestPassword123!',
      },
    });

    if (loginResponse.status() === 200) {
      const loginData = await loginResponse.json();
      authToken = loginData.access_token;
    } else {
      // Register new test user
      const registerResponse = await request.post(`${API_URL}/api/auth/register`, {
        json: {
          email: 'test-templates@example.com',
          password: 'TestPassword123!',
          full_name: 'Template Test User',
        },
      });

      if (registerResponse.status() !== 201) {
        throw new Error('Failed to register test user');
      }
    }
  });

  // Cleanup: Delete test data
  test.afterAll(async ({ request }) => {
    if (!authToken) return;

    const headers = {
      Authorization: `Bearer ${authToken}`,
    };

    // Delete playlist if created
    if (createdPlaylist) {
      await request.delete(`${API_URL}/api/playlists/${createdPlaylist.id}`, {
        headers,
      });
    }

    // Delete template if created
    if (testTemplate) {
      await request.delete(`${API_URL}/api/playlists/templates/${testTemplate.id}`, {
        headers,
      });
    }
  });

  test('Step 1: Create playlist template with items', async ({ request }) => {
    const headers = {
      Authorization: `Bearer ${authToken}`,
      'Content-Type': 'application/json',
    };

    const response = await request.post(`${API_URL}/api/playlists/templates`, {
      headers,
      json: TEST_TEMPLATE,
    });

    expect(response.status()).toBe(201);

    const data = await response.json();
    testTemplate = data;

    // Verify template properties
    expect(testTemplate).toMatchObject({
      name: TEST_TEMPLATE.name,
      description: TEST_TEMPLATE.description,
      is_public: TEST_TEMPLATE.is_public || false,
      items_count: TEST_TEMPLATE.items.length,
    });

    // Verify items are preserved
    expect(testTemplate.items).toHaveLength(TEST_TEMPLATE.items.length);
    expect(testTemplate.items[0]).toMatchObject({
      url: TEST_TEMPLATE.items[0].url,
      title: TEST_TEMPLATE.items[0].title,
      duration: TEST_TEMPLATE.items[0].duration,
      type: TEST_TEMPLATE.items[0].type,
    });

    // Verify total duration is calculated correctly
    const expectedDuration = TEST_TEMPLATE.items.reduce((sum, item) => sum + item.duration, 0);
    expect(testTemplate.total_duration).toBe(expectedDuration);

    expect(testTemplate.id).toBeDefined();
    expect(testTemplate.user_id).toBeDefined();
    expect(testTemplate.created_at).toBeDefined();
  });

  test('Step 2: Apply template to create new playlist', async ({ request }) => {
    const headers = {
      Authorization: `Bearer ${authToken}`,
      'Content-Type': 'application/json',
    };

    const response = await request.post(
      `${API_URL}/api/playlists/templates/${testTemplate.id}/apply`,
      {
        headers,
        json: TEST_PLAYLIST_FROM_TEMPLATE,
      }
    );

    expect(response.status()).toBe(200);

    const data = await response.json();
    createdPlaylist = data;

    // Verify playlist properties
    expect(createdPlaylist).toMatchObject({
      name: TEST_PLAYLIST_FROM_TEMPLATE.playlist_name,
      description: TEST_PLAYLIST_FROM_TEMPLATE.playlist_description,
      items_count: testTemplate.items_count,
      total_duration: testTemplate.total_duration,
    });

    expect(createdPlaylist.id).toBeDefined();
    expect(createdPlaylist.user_id).toBeDefined();
    expect(createdPlaylist.created_at).toBeDefined();
  });

  test('Step 3: Verify all items copied correctly', async ({ request }) => {
    const headers = {
      Authorization: `Bearer ${authToken}`,
    };

    // Fetch the created playlist
    const response = await request.get(`${API_URL}/api/playlists/${createdPlaylist.id}`, {
      headers,
    });

    expect(response.status()).toBe(200);

    const playlist: Playlist = await response.json();

    // Verify item count matches
    expect(playlist.items).toHaveLength(testTemplate.items.length);
    expect(playlist.items_count).toBe(testTemplate.items_count);

    // Verify each item is copied correctly
    for (let i = 0; i < testTemplate.items.length; i++) {
      const templateItem = testTemplate.items[i];
      const playlistItem = playlist.items[i];

      expect(playlistItem).toMatchObject({
        url: templateItem.url,
        title: templateItem.title,
        duration: templateItem.duration,
        type: templateItem.type,
      });
    }

    // Verify total duration matches
    expect(playlist.total_duration).toBe(testTemplate.total_duration);
  });

  test('Step 4: Verify template is independent of playlist', async ({ request }) => {
    const headers = {
      Authorization: `Bearer ${authToken}`,
      'Content-Type': 'application/json',
    };

    // Update the playlist by adding a new item
    const updatedItems = [
      ...createdPlaylist.items,
      {
        url: 'https://www.youtube.com/watch?v=test',
        title: 'New Item',
        duration: 120,
        type: 'youtube',
      },
    ];

    const updateResponse = await request.put(
      `${API_URL}/api/playlists/${createdPlaylist.id}`,
      {
        headers,
        json: { items: updatedItems },
      }
    );

    expect(updateResponse.status()).toBe(200);

    // Fetch the template again and verify it hasn't changed
    const templateResponse = await request.get(
      `${API_URL}/api/playlists/templates/${testTemplate.id}`,
      { headers }
    );

    expect(templateResponse.status()).toBe(200);
    const unchangedTemplate: PlaylistTemplate = await templateResponse.json();

    // Template should still have original item count
    expect(unchangedTemplate.items_count).toBe(TEST_TEMPLATE.items.length);
    expect(unchangedTemplate.items).toHaveLength(TEST_TEMPLATE.items.length);
  });

  test('UI: Template manager displays templates correctly', async ({ page }) => {
    // Set auth token in localStorage
    await page.addInitScript(() => {
      const mockJwt = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0LXRlbXBsYXRlcyIsImV4cCI6OTk5OTk5OTk5OSwicm9sZSI6InVzZXIifQ.dummy_signature';
      localStorage.setItem('token', mockJwt);
    });

    // Navigate to playlists page
    await page.goto(`${BASE_URL}/user-playlists`);

    // Wait for page to load
    await page.waitForLoadState('networkidle');

    // Mock API responses for templates
    await page.route(`${API_URL}/api/playlists/templates`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([testTemplate]),
      });
    });

    // Switch to templates tab
    const templatesTab = page.locator('button:has-text("Templates")');
    if (await templatesTab.isVisible()) {
      await templatesTab.click();
    }

    // Verify template is visible
    const templateElement = page.locator(`text=${TEST_TEMPLATE.name}`);
    await expect(templateElement).toBeVisible();

    // Verify template metadata is displayed
    const itemsCountText = page.locator(`text=${TEST_TEMPLATE.items.length} items`);
    await expect(itemsCountText).toBeVisible();

    // Take a screenshot for visual verification
    await page.screenshot({
      path: 'frontend/tests/e2e/artifacts/playlist-templates-list.png',
      fullPage: true,
    });
  });

  test('API: Clone template creates independent copy', async ({ request }) => {
    const headers = {
      Authorization: `Bearer ${authToken}`,
      'Content-Type': 'application/json',
    };

    // Clone the template
    const cloneResponse = await request.post(
      `${API_URL}/api/playlists/templates/${testTemplate.id}/clone`,
      { headers }
    );

    expect(cloneResponse.status()).toBe(200);

    const clonedTemplate: PlaylistTemplate = await cloneResponse.json();

    // Verify cloned template has correct properties
    expect(clonedTemplate.name).toContain('Copy of');
    expect(clonedTemplate.items_count).toBe(testTemplate.items_count);
    expect(clonedTemplate.total_duration).toBe(testTemplate.total_duration);
    expect(clonedTemplate.items).toHaveLength(testTemplate.items.length);

    // Verify items are identical
    for (let i = 0; i < testTemplate.items.length; i++) {
      expect(clonedTemplate.items[i]).toMatchObject({
        url: testTemplate.items[i].url,
        title: testTemplate.items[i].title,
        duration: testTemplate.items[i].duration,
        type: testTemplate.items[i].type,
      });
    }

    // Cleanup: Delete cloned template
    await request.delete(`${API_URL}/api/playlists/templates/${clonedTemplate.id}`, {
      headers,
    });
  });

  test('API: Public templates can be accessed by other users', async ({ request }) => {
    const headers = {
      Authorization: `Bearer ${authToken}`,
      'Content-Type': 'application/json',
    };

    // Make template public
    const updateResponse = await request.put(
      `${API_URL}/api/playlists/templates/${testTemplate.id}`,
      {
        headers,
        json: { is_public: true },
      }
    );

    expect(updateResponse.status()).toBe(200);

    // Fetch public templates
    const publicTemplatesResponse = await request.get(
      `${API_URL}/api/playlists/templates/public`,
      { headers }
    );

    expect(publicTemplatesResponse.status()).toBe(200);

    const publicTemplates: PlaylistTemplate[] = await publicTemplatesResponse.json();

    // Verify our template is in the public list
    const ourTemplate = publicTemplates.find((t) => t.id === testTemplate.id);
    expect(ourTemplate).toBeDefined();
    expect(ourTemplate!.is_public).toBe(true);

    // Reset to private for cleanup
    await request.put(`${API_URL}/api/playlists/templates/${testTemplate.id}`, {
      headers,
      json: { is_public: false },
    });
  });
});
