/**
 * E2E Test: Shuffle and Repeat Modes
 *
 * Verifies:
 * - Creating playlists with shuffle mode enabled/disabled
 * - Creating playlists with repeat modes (none, one, all)
 * - Updating playlist shuffle mode
 * - Updating playlist repeat mode
 * - Verifying shuffle and repeat modes are persisted correctly
 * - API responses include shuffle and repeat settings
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
}

interface Playlist {
  id: string;
  user_id: string;
  name: string;
  description?: string;
  is_shuffled: boolean;
  repeat_mode: string;
  items: PlaylistEntry[];
  items_count: number;
  total_duration: number;
  is_public: boolean;
  created_at: string;
  updated_at?: string;
}

interface PlaylistCreate {
  name: string;
  description?: string;
  is_shuffled?: boolean;
  repeat_mode?: string;
  items?: PlaylistEntry[];
}

interface PlaylistUpdate {
  is_shuffled?: boolean;
  repeat_mode?: string;
}

// Test data
const SAMPLE_ITEMS: PlaylistEntry[] = [
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
  {
    url: 'https://www.youtube.com/watch?v=jNQXAC9IVRw',
    title: 'Me at the zoo',
    duration: 19,
    type: 'youtube',
  },
];

test.describe('E2E: Shuffle and Repeat Modes', () => {
  let authToken: string;
  let testPlaylist: Playlist;

  test.beforeAll(async () => {
    // Authenticate and get token
    const loginResponse = await fetch(`${API_URL}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: 'test@example.com',
        password: 'testpassword',
      }),
    });

    if (!loginResponse.ok) {
      // Create test user if login fails
      const registerResponse = await fetch(`${API_URL}/api/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: 'test@example.com',
          password: 'testpassword',
          full_name: 'Test User',
        }),
      });

      if (!registerResponse.ok) {
        throw new Error('Failed to create test user');
      }

      const loginResult = await fetch(`${API_URL}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: 'test@example.com',
          password: 'testpassword',
        }),
      });

      if (!loginResult.ok) {
        throw new Error('Failed to login after registration');
      }

      const loginData = await loginResult.json();
      authToken = loginData.access_token;
    } else {
      const loginData = await loginResponse.json();
      authToken = loginData.access_token;
    }
  });

  test.afterAll(async () => {
    // Cleanup test playlist if exists
    if (testPlaylist) {
      await fetch(`${API_URL}/api/schedule/playlists/${testPlaylist.id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${authToken}` },
      });
    }
  });

  test('should create playlist with shuffle enabled', async () => {
    const payload: PlaylistCreate = {
      name: 'Shuffled Playlist',
      description: 'This playlist should play in random order',
      is_shuffled: true,
      items: SAMPLE_ITEMS,
    };

    const response = await fetch(`${API_URL}/api/schedule/playlists`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${authToken}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    expect(response.ok).toBeTruthy();
    const data: Playlist = await response.json();

    expect(data.id).toBeDefined();
    expect(data.name).toBe('Shuffled Playlist');
    expect(data.is_shuffled).toBe(true);
    expect(data.items_count).toBe(4);

    testPlaylist = data;
  });

  test('should create playlist with shuffle disabled', async () => {
    const payload: PlaylistCreate = {
      name: 'Ordered Playlist',
      description: 'This playlist should play in order',
      is_shuffled: false,
      items: SAMPLE_ITEMS,
    };

    const response = await fetch(`${API_URL}/api/schedule/playlists`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${authToken}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    expect(response.ok).toBeTruthy();
    const data: Playlist = await response.json();

    expect(data.id).toBeDefined();
    expect(data.name).toBe('Ordered Playlist');
    expect(data.is_shuffled).toBe(false);
  });

  test('should create playlist with repeat mode NONE', async () => {
    const payload: PlaylistCreate = {
      name: 'No Repeat Playlist',
      repeat_mode: 'none',
      items: SAMPLE_ITEMS,
    };

    const response = await fetch(`${API_URL}/api/schedule/playlists`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${authToken}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    expect(response.ok).toBeTruthy();
    const data: Playlist = await response.json();

    expect(data.repeat_mode).toBe('none');
  });

  test('should create playlist with repeat mode ONE', async () => {
    const payload: PlaylistCreate = {
      name: 'Repeat One Playlist',
      description: 'This playlist should repeat the current item',
      repeat_mode: 'one',
      items: SAMPLE_ITEMS,
    };

    const response = await fetch(`${API_URL}/api/schedule/playlists`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${authToken}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    expect(response.ok).toBeTruthy();
    const data: Playlist = await response.json();

    expect(data.repeat_mode).toBe('one');
  });

  test('should create playlist with repeat mode ALL', async () => {
    const payload: PlaylistCreate = {
      name: 'Repeat All Playlist',
      description: 'This playlist should loop continuously',
      repeat_mode: 'all',
      items: SAMPLE_ITEMS,
    };

    const response = await fetch(`${API_URL}/api/schedule/playlists`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${authToken}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    expect(response.ok).toBeTruthy();
    const data: Playlist = await response.json();

    expect(data.repeat_mode).toBe('all');
  });

  test('should update playlist shuffle mode from false to true', async () => {
    // Create playlist with shuffle disabled
    const createPayload: PlaylistCreate = {
      name: 'Shuffle Update Test',
      is_shuffled: false,
      items: SAMPLE_ITEMS,
    };

    const createResponse = await fetch(`${API_URL}/api/schedule/playlists`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${authToken}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(createPayload),
    });

    const created: Playlist = await createResponse.json();

    // Update shuffle to true
    const updatePayload: PlaylistUpdate = {
      is_shuffled: true,
    };

    const updateResponse = await fetch(
      `${API_URL}/api/schedule/playlists/${created.id}`,
      {
        method: 'PUT',
        headers: {
          Authorization: `Bearer ${authToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(updatePayload),
      }
    );

    expect(updateResponse.ok).toBeTruthy();
    const updated: Playlist = await updateResponse.json();

    expect(updated.is_shuffled).toBe(true);

    // Cleanup
    await fetch(`${API_URL}/api/schedule/playlists/${created.id}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${authToken}` },
    });
  });

  test('should update playlist shuffle mode from true to false', async () => {
    // Create playlist with shuffle enabled
    const createPayload: PlaylistCreate = {
      name: 'Shuffle Disable Test',
      is_shuffled: true,
      items: SAMPLE_ITEMS,
    };

    const createResponse = await fetch(`${API_URL}/api/schedule/playlists`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${authToken}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(createPayload),
    });

    const created: Playlist = await createResponse.json();

    // Update shuffle to false
    const updatePayload: PlaylistUpdate = {
      is_shuffled: false,
    };

    const updateResponse = await fetch(
      `${API_URL}/api/schedule/playlists/${created.id}`,
      {
        method: 'PUT',
        headers: {
          Authorization: `Bearer ${authToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(updatePayload),
      }
    );

    expect(updateResponse.ok).toBeTruthy();
    const updated: Playlist = await updateResponse.json();

    expect(updated.is_shuffled).toBe(false);

    // Cleanup
    await fetch(`${API_URL}/api/schedule/playlists/${created.id}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${authToken}` },
    });
  });

  test('should update playlist repeat mode to ONE', async () => {
    // Create playlist with repeat none
    const createPayload: PlaylistCreate = {
      name: 'Repeat Update Test',
      repeat_mode: 'none',
      items: SAMPLE_ITEMS,
    };

    const createResponse = await fetch(`${API_URL}/api/schedule/playlists`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${authToken}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(createPayload),
    });

    const created: Playlist = await createResponse.json();

    // Update repeat to one
    const updatePayload: PlaylistUpdate = {
      repeat_mode: 'one',
    };

    const updateResponse = await fetch(
      `${API_URL}/api/schedule/playlists/${created.id}`,
      {
        method: 'PUT',
        headers: {
          Authorization: `Bearer ${authToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(updatePayload),
      }
    );

    expect(updateResponse.ok).toBeTruthy();
    const updated: Playlist = await updateResponse.json();

    expect(updated.repeat_mode).toBe('one');

    // Cleanup
    await fetch(`${API_URL}/api/schedule/playlists/${created.id}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${authToken}` },
    });
  });

  test('should update playlist repeat mode to ALL', async () => {
    // Create playlist with repeat none
    const createPayload: PlaylistCreate = {
      name: 'Repeat All Update Test',
      repeat_mode: 'none',
      items: SAMPLE_ITEMS,
    };

    const createResponse = await fetch(`${API_URL}/api/schedule/playlists`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${authToken}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(createPayload),
    });

    const created: Playlist = await createResponse.json();

    // Update repeat to all
    const updatePayload: PlaylistUpdate = {
      repeat_mode: 'all',
    };

    const updateResponse = await fetch(
      `${API_URL}/api/schedule/playlists/${created.id}`,
      {
        method: 'PUT',
        headers: {
          Authorization: `Bearer ${authToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(updatePayload),
      }
    );

    expect(updateResponse.ok).toBeTruthy();
    const updated: Playlist = await updateResponse.json();

    expect(updated.repeat_mode).toBe('all');

    // Cleanup
    await fetch(`${API_URL}/api/schedule/playlists/${created.id}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${authToken}` },
    });
  });

  test('should update both shuffle and repeat mode together', async () => {
    // Create playlist with defaults
    const createPayload: PlaylistCreate = {
      name: 'Combined Update Test',
      is_shuffled: false,
      repeat_mode: 'none',
      items: SAMPLE_ITEMS,
    };

    const createResponse = await fetch(`${API_URL}/api/schedule/playlists`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${authToken}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(createPayload),
    });

    const created: Playlist = await createResponse.json();

    // Update both shuffle and repeat
    const updatePayload: PlaylistUpdate = {
      is_shuffled: true,
      repeat_mode: 'all',
    };

    const updateResponse = await fetch(
      `${API_URL}/api/schedule/playlists/${created.id}`,
      {
        method: 'PUT',
        headers: {
          Authorization: `Bearer ${authToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(updatePayload),
      }
    );

    expect(updateResponse.ok).toBeTruthy();
    const updated: Playlist = await updateResponse.json();

    expect(updated.is_shuffled).toBe(true);
    expect(updated.repeat_mode).toBe('all');

    // Cleanup
    await fetch(`${API_URL}/api/schedule/playlists/${created.id}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${authToken}` },
    });
  });

  test('should get playlist with shuffle and repeat settings', async () => {
    // Create playlist
    const createPayload: PlaylistCreate = {
      name: 'Get Test Playlist',
      is_shuffled: true,
      repeat_mode: 'all',
      items: SAMPLE_ITEMS,
    };

    const createResponse = await fetch(`${API_URL}/api/schedule/playlists`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${authToken}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(createPayload),
    });

    const created: Playlist = await createResponse.json();

    // Get playlist
    const getResponse = await fetch(
      `${API_URL}/api/schedule/playlists/${created.id}`,
      {
        headers: { Authorization: `Bearer ${authToken}` },
      }
    );

    expect(getResponse.ok).toBeTruthy();
    const data: Playlist = await getResponse.json();

    expect(data.is_shuffled).toBe(true);
    expect(data.repeat_mode).toBe('all');
    expect(data.items_count).toBe(4);

    // Cleanup
    await fetch(`${API_URL}/api/schedule/playlists/${created.id}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${authToken}` },
    });
  });

  test('should list playlists with shuffle and repeat settings', async () => {
    // Create multiple playlists
    const playlists = [
      {
        name: 'List Test 1',
        is_shuffled: true,
        repeat_mode: 'none',
        items: SAMPLE_ITEMS,
      },
      {
        name: 'List Test 2',
        is_shuffled: false,
        repeat_mode: 'one',
        items: SAMPLE_ITEMS,
      },
      {
        name: 'List Test 3',
        is_shuffled: true,
        repeat_mode: 'all',
        items: SAMPLE_ITEMS,
      },
    ];

    const createdIds: string[] = [];

    for (const playlist of playlists) {
      const response = await fetch(`${API_URL}/api/schedule/playlists`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${authToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(playlist),
      });

      const data: Playlist = await response.json();
      createdIds.push(data.id);
    }

    // List playlists
    const listResponse = await fetch(`${API_URL}/api/schedule/playlists`, {
      headers: { Authorization: `Bearer ${authToken}` },
    });

    expect(listResponse.ok).toBeTruthy();
    const data: Playlist[] = await listResponse.json();

    expect(data.length).toBeGreaterThanOrEqual(3);

    // Verify shuffle and repeat are in response
    for (const playlist of data.slice(0, 3)) {
      expect(playlist).toHaveProperty('is_shuffled');
      expect(playlist).toHaveProperty('repeat_mode');
    }

    // Cleanup
    for (const id of createdIds) {
      await fetch(`${API_URL}/api/schedule/playlists/${id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${authToken}` },
      });
    }
  });

  test('should reject invalid repeat mode', async () => {
    const payload = {
      name: 'Invalid Playlist',
      repeat_mode: 'invalid_mode',
      items: SAMPLE_ITEMS,
    };

    const response = await fetch(`${API_URL}/api/schedule/playlists`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${authToken}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    // Should return 422 validation error
    expect(response.status).toBe(422);
  });

  test('should use default values for shuffle and repeat', async () => {
    const payload: PlaylistCreate = {
      name: 'Default Values Test',
      items: SAMPLE_ITEMS,
    };

    const response = await fetch(`${API_URL}/api/schedule/playlists`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${authToken}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    expect(response.ok).toBeTruthy();
    const data: Playlist = await response.json();

    expect(data.is_shuffled).toBe(false); // Default should be false
    expect(data.repeat_mode).toBe('none'); // Default should be none
  });

  test('should require authentication for creating playlists', async () => {
    const payload: PlaylistCreate = {
      name: 'Auth Test',
      is_shuffled: true,
      items: SAMPLE_ITEMS,
    };

    const response = await fetch(`${API_URL}/api/schedule/playlists`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    expect(response.status).toBe(401);
  });

  test('should require authentication for updating playlists', async () => {
    const updatePayload: PlaylistUpdate = {
      is_shuffled: true,
    };

    const response = await fetch(
      `${API_URL}/api/schedule/playlists/some-uuid`,
      {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updatePayload),
      }
    );

    expect(response.status).toBe(401);
  });
});
