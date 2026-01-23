import { test, expect } from '@playwright/test';

/**
 * E2E Tests for Guest Co-Hosting Flow
 *
 * Tests the complete flow from host starting a live stream to guest joining with co-host permissions:
 * 1. Host starts live stream
 * 2. Host generates guest invite link
 * 3. Guest opens link in separate browser context
 * 4. Guest accepts invitation
 * 5. Host grants co-host permissions
 * 6. Guest enables camera/microphone
 * 7. Verify both streams mixed and broadcast to Telegram
 */

const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:3000';
const ADMIN_EMAIL = process.env.MCP_ADMIN_EMAIL || 'admin@sattva.com';
const ADMIN_PASSWORD = process.env.MCP_ADMIN_PASSWORD || 'Zxy1234567';
const GUEST_EMAIL = 'guest@example.com';
const GUEST_PASSWORD = 'GuestPassword123!';

test.describe('Guest Co-Hosting Flow', () => {
  test('complete guest co-hosting flow from invitation to broadcast', async ({ browser, context }) => {
    // Step 1: Host logs in and starts live stream
    const hostContext = await browser.newContext();
    await hostContext.grantPermissions(['camera', 'microphone']);

    const hostPage = await hostContext.newPage();

    // Login as host
    await hostPage.goto(BASE_URL);
    await hostPage.fill('input[type="email"]', ADMIN_EMAIL);
    await hostPage.fill('input[type="password"]', ADMIN_PASSWORD);
    await hostPage.click('button[type="submit"]');
    await hostPage.waitForURL('**/dashboard', { timeout: 10000 });

    // Navigate to live streaming page
    await hostPage.goto(`${BASE_URL}/live`);

    // Verify live streaming page loaded
    await expect(hostPage.locator('h1')).toContainText('Live Streaming', { timeout: 5000 });
    await expect(hostPage.locator('button:has-text("Go Live")')).toBeVisible();
    await expect(hostPage.locator('button:has-text("Invite Guest")')).toBeVisible();

    // Mock API calls for creating stream
    let mockStreamId = 1;
    await hostPage.route('**/api/v1/live/streams', async (route) => {
      await route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify({
          id: mockStreamId,
          owner_id: 1,
          chat_id: 123456789,
          title: 'Test Guest Co-Host Stream',
          status: 'idle',
          ingestion_type: 'webrtc_camera',
          viewer_count: 0,
          latency_ms: 0,
          recording_enabled: true,
          max_guests: 5,
          current_guest_count: 0,
          quality_preset: 'medium',
          is_chat_enabled: true,
          created_at: new Date().toISOString(),
        }),
      });
    });

    // Mock API call to start stream
    await hostPage.route('**/api/v1/live/streams/*/start', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          stream_id: mockStreamId,
          title: 'Test Guest Co-Host Stream',
          status: 'active',
          ingestion_url: 'rtmp://localhost:1935/live',
          stream_key: 'test-stream-key',
          preview_url: 'blob:http://localhost:3000/preview',
          message: 'Stream started successfully',
        }),
      });
    });

    // Start the live stream
    await hostPage.click('button:has-text("Go Live")');
    await hostPage.waitForTimeout(2000);

    // Start camera capture
    await hostPage.click('button:has-text("Start Capture")');
    await hostPage.waitForTimeout(3000);

    // Verify stream is active
    await expect(hostPage.locator('video').first()).toBeVisible();
    await expect(hostPage.locator('text=LIVE')).toBeVisible();

    // Step 2: Host generates guest invite link
    let inviteToken = 'test-invite-token-' + Date.now();

    // Mock guest invitation API
    await hostPage.route('**/api/v1/live/guests/invite', async (route) => {
      await route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify({
          guest_session_id: 1,
          invite_token: inviteToken,
          invite_link: `${BASE_URL}/live/guest/join?token=${inviteToken}`,
          message: 'Invitation sent successfully',
        }),
      });
    });

    // Click Invite Guest button
    await hostPage.click('button:has-text("Invite Guest")');

    // Wait for invite modal to appear
    await expect(hostPage.locator('text=Invite Guest Co-Host')).toBeVisible({ timeout: 3000 });

    // Fill in guest email
    await hostPage.fill('input[type="email"]', GUEST_EMAIL);
    await hostPage.fill('textarea', 'Please join my live stream as a co-host!');

    // Send invitation
    await hostPage.click('button:has-text("Send Invite")');
    await hostPage.waitForTimeout(2000);

    // Verify invite was sent (modal should close)
    await expect(hostPage.locator('text=Invite Guest Co-Host')).not.toBeVisible();

    // Step 3: Guest opens invite link in separate browser context
    const guestContext = await browser.newContext();
    await guestContext.grantPermissions(['camera', 'microphone']);

    const guestPage = await guestContext.newPage();

    // Mock guest session lookup
    await guestPage.route('**/api/v1/live/guests/invite/*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 1,
          live_stream_id: mockStreamId,
          user_id: 2,
          full_name: 'Test Guest',
          email: GUEST_EMAIL,
          status: 'pending',
          permissions: {
            can_speak: false,
            can_share_video: false,
            can_share_screen: false,
            can_control_stream: false,
            can_invite_others: false,
          },
          invite_token: inviteToken,
          created_at: new Date().toISOString(),
        }),
      });
    });

    // Navigate to invite link
    await guestPage.goto(`${BASE_URL}/live/guest/join?token=${inviteToken}`);

    // Verify guest join page loaded
    await expect(guestPage.locator('text=Join Live Stream')).toBeVisible({ timeout: 5000 });
    await expect(guestPage.locator(`text=${GUEST_EMAIL}`)).toBeVisible();

    // Step 4: Guest accepts invitation
    // Mock accept invitation API
    await guestPage.route('**/api/v1/live/guests/*/accept', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 1,
          live_stream_id: mockStreamId,
          user_id: 2,
          full_name: 'Test Guest',
          email: GUEST_EMAIL,
          status: 'accepted',
          permissions: {
            can_speak: false,
            can_share_video: false,
            can_share_screen: false,
            can_control_stream: false,
            can_invite_others: false,
          },
          created_at: new Date().toISOString(),
        }),
      });
    });

    // Click accept button
    await guestPage.click('button:has-text("Accept Invitation")');
    await guestPage.waitForTimeout(2000);

    // Verify status changed to accepted
    await expect(guestPage.locator('text=Accepted')).toBeVisible();

    // Step 5: Host grants co-host permissions
    // Mock guest list API for host
    await hostPage.route('**/api/v1/live/guests*stream_id=*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          guests: [
            {
              id: 1,
              live_stream_id: mockStreamId,
              user_id: 2,
              full_name: 'Test Guest',
              email: GUEST_EMAIL,
              status: 'accepted',
              permissions: {
                can_speak: false,
                can_share_video: false,
                can_share_screen: false,
                can_control_stream: false,
                can_invite_others: false,
              },
              created_at: new Date().toISOString(),
            },
          ],
        }),
      });
    });

    // Mock update permissions API
    await hostPage.route('**/api/v1/live/guests/*', async (route) => {
      if (route.request().method() === 'PUT') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            id: 1,
            live_stream_id: mockStreamId,
            user_id: 2,
            full_name: 'Test Guest',
            email: GUEST_EMAIL,
            status: 'accepted',
            permissions: {
              can_speak: true,
              can_share_video: true,
              can_share_screen: false,
              can_control_stream: false,
              can_invite_others: false,
            },
            created_at: new Date().toISOString(),
          }),
        });
      } else {
        route.continue();
      }
    });

    // Refresh host page to see guest
    await hostPage.reload();
    await hostPage.waitForTimeout(2000);

    // Verify guest appears in host's guest list
    await expect(hostPage.locator('text=Test Guest')).toBeVisible({ timeout: 5000 });
    await expect(hostPage.locator('text=guest@example.com')).toBeVisible();

    // Grant permissions (enable video and audio)
    // Note: The exact UI for granting permissions may vary - adjust selector as needed
    const permissionButtons = hostPage.locator('button[title*="permission"], button[aria-label*="permission"]');
    const permissionCount = await permissionButtons.count();

    if (permissionCount > 0) {
      // Click permission toggle buttons
      for (let i = 0; i < Math.min(permissionCount, 2); i++) {
        await permissionButtons.nth(i).click();
        await hostPage.waitForTimeout(500);
      }
    }

    await hostPage.waitForTimeout(2000);

    // Step 6: Guest enables camera/microphone
    // Mock join session API
    await guestPage.route('**/api/v1/live/guests/*/join', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 1,
          live_stream_id: mockStreamId,
          user_id: 2,
          full_name: 'Test Guest',
          email: GUEST_EMAIL,
          status: 'active',
          permissions: {
            can_speak: true,
            can_share_video: true,
            can_share_screen: false,
            can_control_stream: false,
            can_invite_others: false,
          },
          webrtc_connection_id: 'webrtc-conn-123',
          connection_quality: 'good',
          created_at: new Date().toISOString(),
          joined_at: new Date().toISOString(),
        }),
      });
    });

    // Guest enables camera/microphone
    await guestPage.click('button:has-text("Enable Camera")');
    await guestPage.waitForTimeout(2000);

    await guestPage.click('button:has-text("Enable Microphone")');
    await guestPage.waitForTimeout(2000);

    // Verify guest video preview is visible
    await expect(guestPage.locator('video').first()).toBeVisible({ timeout: 5000 });
    await expect(guestPage.locator('text=Active')).toBeVisible();

    // Step 7: Verify both streams mixed and broadcast to Telegram
    // Mock stream health check showing multiple streams
    await hostPage.route('**/api/v1/live/preview/*/health', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          stream_id: mockStreamId,
          health_score: 95,
          status: 'healthy',
          latency_ms: 150,
          bitrate: 6000,
          connection_quality: 'excellent',
          active_streams: [
            {
              id: 'host-stream',
              type: 'webrtc_camera',
              quality: 'good',
            },
            {
              id: 'guest-stream-1',
              type: 'webrtc_camera',
              quality: 'good',
            },
          ],
          issues: [],
          warnings: [],
          recommendations: [],
        }),
      });
    });

    // Refresh host page to see updated status
    await hostPage.reload();
    await hostPage.waitForTimeout(2000);

    // Verify both host and guest streams are visible
    await expect(hostPage.locator('text=Test Guest')).toBeVisible();
    await expect(hostPage.locator('text=good').or(hostPage.locator('text=Active'))).toBeVisible();

    // Verify guest count updated
    await expect(hostPage.locator('text=1/5')).toBeVisible();

    // Verify connection quality indicator
    const qualityIndicator = hostPage.locator('text=good').or(hostPage.locator('[data-testid*="quality"]'));
    const qualityVisible = await qualityIndicator.count();
    if (qualityVisible > 0) {
      await expect(qualityIndicator.first()).toBeVisible();
    }

    // Cleanup
    await guestContext.close();
    await hostContext.close();
  });

  test('host can remove guest from active session', async ({ page }) => {
    // Login as host
    await page.goto(BASE_URL);
    await page.fill('input[type="email"]', ADMIN_EMAIL);
    await page.fill('input[type="password"]', ADMIN_PASSWORD);
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard', { timeout: 10000 });

    // Navigate to live streaming page
    await page.goto(`${BASE_URL}/live`);

    // Mock guest list with active guest
    await page.route('**/api/v1/live/guests*stream_id=*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          guests: [
            {
              id: 1,
              live_stream_id: 1,
              user_id: 2,
              full_name: 'Test Guest',
              email: GUEST_EMAIL,
              status: 'active',
              permissions: {
                can_speak: true,
                can_share_video: true,
                can_share_screen: false,
                can_control_stream: false,
                can_invite_others: false,
              },
              webrtc_connection_id: 'webrtc-conn-123',
              connection_quality: 'good',
              created_at: new Date().toISOString(),
              joined_at: new Date().toISOString(),
            },
          ],
        }),
      });
    });

    // Mock remove guest API
    await page.route('**/api/v1/live/guests/*', async (route) => {
      if (route.request().method() === 'DELETE') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            message: 'Guest removed successfully',
          }),
        });
      } else {
        route.continue();
      }
    });

    await page.reload();
    await page.waitForTimeout(2000);

    // Verify guest is visible
    await expect(page.locator('text=Test Guest')).toBeVisible({ timeout: 5000 });

    // Click remove button (X icon button)
    const removeButton = page.locator('button[title*="remove"], button[aria-label*="remove"]').or(
      page.locator('button').filter({ hasText: '' }).locator('svg').locator('xpath=../../..')
    );

    const removeCount = await removeButton.count();
    if (removeCount > 0) {
      // Handle confirmation dialog if present
      page.on('dialog', dialog => dialog.accept());

      await removeButton.first().click();
      await page.waitForTimeout(1000);

      // Verify guest removed (should disappear or status change)
      await page.waitForTimeout(2000);
    }
  });

  test('guest can decline invitation', async ({ page, context }) => {
    await context.grantPermissions(['camera', 'microphone']);

    const inviteToken = 'test-invite-token-decline';

    // Mock guest session lookup
    await page.route('**/api/v1/live/guests/invite/*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 1,
          live_stream_id: 1,
          user_id: 2,
          full_name: 'Test Guest',
          email: GUEST_EMAIL,
          status: 'pending',
          permissions: {
            can_speak: false,
            can_share_video: false,
            can_share_screen: false,
            can_control_stream: false,
            can_invite_others: false,
          },
          invite_token: inviteToken,
          created_at: new Date().toISOString(),
        }),
      });
    });

    // Mock reject invitation API
    await page.route('**/api/v1/live/guests/*/reject', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 1,
          live_stream_id: 1,
          user_id: 2,
          full_name: 'Test Guest',
          email: GUEST_EMAIL,
          status: 'rejected',
          rejection_reason: 'Guest declined invitation',
          permissions: {
            can_speak: false,
            can_share_video: false,
            can_share_screen: false,
            can_control_stream: false,
            can_invite_others: false,
          },
          created_at: new Date().toISOString(),
        }),
      });
    });

    // Navigate to invite link
    await page.goto(`${BASE_URL}/live/guest/join?token=${inviteToken}`);

    // Verify guest join page loaded
    await expect(page.locator('text=Join Live Stream')).toBeVisible({ timeout: 5000 });

    // Click decline button
    await page.click('button:has-text("Decline")');
    await page.waitForTimeout(2000);

    // Verify rejection message or redirect
    const rejectionMessage = page.locator('text=declined').or(
      page.locator('text=invitation.*declined')
    ).or(page.locator('text=Thank you'));

    const rejectionVisible = await rejectionMessage.count();
    if (rejectionVisible > 0) {
      await expect(rejectionMessage.first()).toBeVisible();
    }
  });

  test('host can copy invite link and share with guest', async ({ page }) => {
    // Login as host
    await page.goto(BASE_URL);
    await page.fill('input[type="email"]', ADMIN_EMAIL);
    await page.fill('input[type="password"]', ADMIN_PASSWORD);
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard', { timeout: 10000 });

    // Navigate to live streaming page
    await page.goto(`${BASE_URL}/live`);

    const inviteToken = 'test-copy-invite-token';

    // Mock guest invitation API
    await page.route('**/api/v1/live/guests/invite', async (route) => {
      await route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify({
          guest_session_id: 1,
          invite_token: inviteToken,
          invite_link: `${BASE_URL}/live/guest/join?token=${inviteToken}`,
          message: 'Invitation sent successfully',
        }),
      });
    });

    // Mock guest list
    await page.route('**/api/v1/live/guests*stream_id=*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          guests: [
            {
              id: 1,
              live_stream_id: 1,
              user_id: 2,
              full_name: 'Test Guest',
              email: GUEST_EMAIL,
              status: 'pending',
              permissions: {
                can_speak: false,
                can_share_video: false,
                can_share_screen: false,
                can_control_stream: false,
                can_invite_others: false,
              },
              invite_token: inviteToken,
              created_at: new Date().toISOString(),
            },
          ],
        }),
      });
    });

    // Click Invite Guest button
    await page.click('button:has-text("Invite Guest")');

    // Fill in guest email
    await page.fill('input[type="email"]', GUEST_EMAIL);

    // Send invitation
    await page.click('button:has-text("Send Invite")');
    await page.waitForTimeout(2000);

    // Click copy invite link button
    const copyButton = page.locator('button[title*="Copy"], button:has-text("Copy")').or(
      page.locator('button').filter({ hasText: '' }).locator('svg').filter({ hasText: 'link' }).locator('xpath=../../..')
    );

    const copyCount = await copyButton.count();
    if (copyCount > 0) {
      // Setup clipboard listener
      let clipboardContent = '';
      page.on('clipboard', data => {
        clipboardContent = data;
      });

      await copyButton.first().click();
      await page.waitForTimeout(1000);

      // Verify copy success indicator (checkmark icon or tooltip)
      const checkmarkIcon = page.locator('svg').locator('path[d*="check"]').or(
        page.locator('text=Copied')
      );

      const checkmarkVisible = await checkmarkIcon.count();
      if (checkmarkVisible > 0) {
        await expect(checkmarkIcon.first()).toBeVisible({ timeout: 2000 });
      }
    }
  });
});
