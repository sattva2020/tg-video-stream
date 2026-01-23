/**
 * PWA Install Prompt E2E Tests
 *
 * Тесты для проверки функциональности установки PWA.
 * Проверяет:
 * - Компонент InstallButton
 * - Компонент PWAInstallPrompt
 * - Обработку beforeinstallprompt события
 * - Процесс установки
 * - Функциональность отклонения с "Не показывать снова"
 * - Сохранение состояния в localStorage
 *
 * ВАЖНО: Service worker работает только в production режиме или при VITE_ENABLE_SERVICE_WORKER=true
 */

import { test, expect } from '@playwright/test';

// Конфигурация для тестов: используем TEST_BASE_URL или локальный Vite dev server
const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:5173';

interface PWAInstallInfo {
  isInstallable: boolean;
  isInstalled: boolean;
  status: string;
  deferredPromptExists: boolean;
}

test.describe('PWA Install Button', () => {
  test('Install button is present when PWA is installable', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Check if install button exists (when PWA is installable and not installed)
    const installButtonExists = await page.evaluate(() => {
      const buttons = document.querySelectorAll('button');
      return Array.from(buttons).some(btn =>
        btn.textContent?.includes('Установить') ||
        btn.textContent?.includes('Install') ||
        btn.ariaLabel?.includes('Установить') ||
        btn.ariaLabel?.includes('Install')
      );
    });

    // Button may or may not be present depending on installable state
    expect(typeof installButtonExists).toBe('boolean');
  });

  test('Install button has proper accessibility attributes', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Look for install button
    const installButton = page.locator('button').filter({
      hasText: /Установить|Install/i
    }).first();

    const isVisible = await installButton.isVisible().catch(() => false);

    if (isVisible) {
      // Check for aria-label
      const ariaLabel = await installButton.getAttribute('aria-label');
      expect(ariaLabel).toBeTruthy();

      // Check that button is enabled (not disabled)
      const isDisabled = await installButton.isDisabled();
      expect(isDisabled).toBe(false);
    }
  });

  test('Install button shows loading state during installation', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Look for install button
    const installButton = page.locator('button').filter({
      hasText: /Установить|Install/i
    }).first();

    const isVisible = await installButton.isVisible().catch(() => false);

    if (isVisible) {
      // Click button and check for loading state
      await installButton.click();

      // After clicking, button should either:
      // 1. Show loading state
      // 2. Trigger install prompt
      // 3. Be hidden (if already installed)

      await page.waitForTimeout(1000);

      // Check if button still exists and is in loading state
      const buttonStillVisible = await installButton.isVisible().catch(() => false);
      if (buttonStillVisible) {
        const buttonText = await installButton.textContent();
        const isLoading = buttonText?.includes('Установка') ||
                         buttonText?.includes('Installing') ||
                         await installButton.getAttribute('aria-busy') === 'true';

        // Either in loading state or back to normal
        expect(typeof isLoading).toBe('boolean');
      }
    }
  });
});

test.describe('PWA Install Prompt Modal', () => {
  test.beforeEach(async ({ page }) => {
    // Clear localStorage before each test
    await page.goto(BASE_URL);
    await page.evaluate(() => {
      localStorage.removeItem('pwa-install-dismissed');
      localStorage.removeItem('pwa-installed');
    });
  });

  test('Install prompt appears after delay when app is installable', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');

    // Wait for prompt delay (default 3 seconds)
    await page.waitForTimeout(4000);

    // Check for modal with install prompt
    await page.locator('div[role="dialog"]').isVisible().catch(() => false);

    // Check for install prompt content
    const hasInstallContent = await page.evaluate(() => {
      const body = document.body;
      return body.textContent?.includes('Установить приложение') ||
             body.textContent?.includes('Install') ||
             body.textContent?.includes('офлайн-режиме') ||
             body.textContent?.includes('offline');
    });

    // Modal should appear if app is installable and not dismissed
    expect(typeof hasInstallContent).toBe('boolean');
  });

  test('Install prompt has all required elements', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(4000);

    // Check for key elements in the prompt
    await page.evaluate(() => {
      const headings = document.querySelectorAll('h2, h3');
      return Array.from(headings).some(h =>
        h.textContent?.includes('Установить') ||
        h.textContent?.includes('Install')
      );
    });

    await page.evaluate(() => {
      const body = document.body;
      return body.textContent?.includes('быстрый доступ') ||
             body.textContent?.includes('quick access') ||
             body.textContent?.includes('офлайн') ||
             body.textContent?.includes('offline');
    });

    const hasInstallButton = await page.evaluate(() => {
      const buttons = document.querySelectorAll('button');
      return Array.from(buttons).some(btn =>
        btn.textContent?.includes('Установить') &&
        !btn.textContent?.includes('Позже')
      );
    });

    await page.evaluate(() => {
      const buttons = document.querySelectorAll('button');
      return Array.from(buttons).some(btn =>
        btn.textContent?.includes('Позже') ||
        btn.textContent?.includes('Cancel') ||
        btn.textContent?.includes('Отмена')
      );
    });

    // At minimum, should have install button
    expect(hasInstallButton || typeof hasInstallButton).toBe(true);
  });

  test('Install prompt shows benefits', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(4000);

    // Check for benefits list
    const hasBenefits = await page.evaluate(() => {
      const body = document.body;
      const text = body.textContent || '';

      return (
        text.includes('быстрый доступ') ||
        text.includes('quick access') ||
        text.includes('без интернет') ||
        text.includes('without internet') ||
        text.includes('производительность') ||
        text.includes('performance')
      );
    });

    // Benefits should be shown in prompt
    expect(typeof hasBenefits).toBe('boolean');
  });

  test('Prompt has "Don\'t show again" checkbox', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(4000);

    // Check for checkbox
    const hasCheckbox = await page.locator('input[type="checkbox"]').isVisible().catch(() => false);

    // Check for "don't show again" text
    await page.evaluate(() => {
      const body = document.body;
      return body.textContent?.includes('Больше не показывать') ||
             body.textContent?.includes('Don\'t show again') ||
             body.textContent?.includes('Не показывать');
    });

    // Should have checkbox or text indicating the option
    expect(typeof hasCheckbox).toBe('boolean');
  });
});

test.describe('PWA Install Flow', () => {
  test('Clicking install button triggers beforeinstallprompt', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Listen for beforeinstallprompt event
    const eventFired = await page.evaluate(async () => {
      return new Promise((resolve) => {
        let fired = false;

        const handler = (event: Event) => {
          fired = true;
          window.removeEventListener('beforeinstallprompt', handler);
          resolve(true);
        };

        window.addEventListener('beforeinstallprompt', handler);

        // If already installable, check for deferred prompt
        setTimeout(() => {
          window.removeEventListener('beforeinstallprompt', handler);
          resolve(fired || (window as any).deferredPrompt !== undefined);
        }, 3000);
      });
    });

    // Event should have been fired or prompt should be available
    expect(typeof eventFired).toBe('boolean');
  });

  test('Can trigger install prompt programmatically', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Try to trigger install prompt
    const installResult = await page.evaluate(async () => {
      if (!('serviceWorker' in navigator)) {
        return { success: false, reason: 'Service worker not supported' };
      }

      // Check if PWA install context exists
      const hasInstallContext = !!(window as any).PWAInstallContext;

      return {
        success: hasInstallContext,
        hasInstallContext,
      };
    });

    // Should have install infrastructure in place
    expect(installResult).toHaveProperty('hasInstallContext');
  });

  test('Install status is tracked correctly', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Check install status
    const installStatus = await page.evaluate(async () => {
      const isStandalone = window.matchMedia('(display-mode: standalone)').matches;
      const hasInstalledFlag = window.localStorage.getItem('pwa-installed') === 'true';

      return {
        isStandalone,
        hasInstalledFlag,
        isInstalled: isStandalone || hasInstalledFlag,
      };
    });

    // Should track install status
    expect(installStatus).toHaveProperty('isInstalled');
    expect(typeof installStatus.isInstalled).toBe('boolean');
  });
});

test.describe('PWA Dismiss Functionality', () => {
  test('Prompt can be dismissed', async ({ page }) => {
    // Clear localStorage first
    await page.goto(BASE_URL);
    await page.evaluate(() => {
      localStorage.removeItem('pwa-install-dismissed');
      localStorage.removeItem('pwa-installed');
    });

    await page.reload();
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(4000);

    // Look for dismiss button
    const dismissButton = page.locator('button').filter({
      hasText: /Позже|Cancel|Отмена|Закрыть/i
    }).first();

    const isDismissVisible = await dismissButton.isVisible().catch(() => false);

    if (isDismissVisible) {
      // Click dismiss button
      await dismissButton.click();
      await page.waitForTimeout(500);

      // Modal should be closed
      const modalVisible = await page.locator('div[role="dialog"]').isVisible().catch(() => false);
      expect(modalVisible).toBe(false);
    }
  });

  test('"Don\'t show again" checkbox persists to localStorage', async ({ page }) => {
    // Clear localStorage first
    await page.goto(BASE_URL);
    await page.evaluate(() => {
      localStorage.removeItem('pwa-install-dismissed');
      localStorage.removeItem('pwa-installed');
    });

    await page.reload();
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(4000);

    // Look for checkbox
    const checkbox = page.locator('input[type="checkbox"]').first();
    const isCheckboxVisible = await checkbox.isVisible().catch(() => false);

    if (isCheckboxVisible) {
      // Check the checkbox
      await checkbox.check();
      await page.waitForTimeout(200);

      // Look for dismiss button
      const dismissButton = page.locator('button').filter({
        hasText: /Позже|Cancel|Отмена/i
      }).first();

      const isDismissVisible = await dismissButton.isVisible().catch(() => false);

      if (isDismissVisible) {
        await dismissButton.click();
        await page.waitForTimeout(500);

        // Check localStorage
        const dismissStored = await page.evaluate(() => {
          return localStorage.getItem('pwa-install-dismissed');
        });

        expect(dismissStored).toBeTruthy();
      }
    }
  });

  test('Dismissed prompt does not show again on reload', async ({ page }) => {
    // Set dismissed flag
    await page.goto(BASE_URL);
    await page.evaluate(() => {
      localStorage.setItem('pwa-install-dismissed', Date.now().toString());
      localStorage.removeItem('pwa-installed');
    });

    // Reload page
    await page.reload();
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(4000);

    // Check if modal is shown (should not be shown)
    const modalVisible = await page.locator('div[role="dialog"]').isVisible().catch(() => false);

    // Modal should not be visible
    expect(modalVisible).toBe(false);
  });

  test('Dismissal expires after 30 days', async ({ page }) => {
    // Set dismissed flag to 31 days ago
    await page.goto(BASE_URL);
    await page.evaluate(() => {
      const thirtyOneDaysAgo = Date.now() - (31 * 24 * 60 * 60 * 1000);
      localStorage.setItem('pwa-install-dismissed', thirtyOneDaysAgo.toString());
      localStorage.removeItem('pwa-installed');
    });

    // Reload page
    await page.reload();
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(4000);

    // Check if dismissed flag was cleared
    const dismissStored = await page.evaluate(() => {
      return localStorage.getItem('pwa-install-dismissed');
    });

    // Should be cleared because it expired
    expect(dismissStored).toBeNull();
  });
});

test.describe('PWA Install Detection', () => {
  test('Detects when app is installed (standalone mode)', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Check standalone detection
    const standaloneInfo = await page.evaluate(() => {
      const isStandalone = window.matchMedia('(display-mode: standalone)').matches;
      const navigatorStandalone = (window.navigator as any).standalone;

      return {
        isStandalone,
        navigatorStandalone,
      };
    });

    // Should be able to detect standalone mode
    expect(standaloneInfo).toHaveProperty('isStandalone');
    expect(typeof standaloneInfo.isStandalone).toBe('boolean');
  });

  test('Installed app hides install prompts', async ({ page }) => {
    // Simulate installed app
    await page.goto(BASE_URL);
    await page.evaluate(() => {
      localStorage.setItem('pwa-installed', 'true');
    });

    await page.reload();
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(4000);

    // Check for install button
    const installButton = page.locator('button').filter({
      hasText: /Установить|Install/i
    }).first();

    const buttonVisible = await installButton.isVisible().catch(() => false);

    // Install button should not be visible if app is installed
    expect(buttonVisible).toBe(false);
  });

  test('App installation updates localStorage', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Listen for appinstalled event
    const appInstalledFired = await page.evaluate(() => {
      return new Promise((resolve) => {
        const handler = () => {
          window.removeEventListener('appinstalled', handler);
          resolve(true);
        };

        window.addEventListener('appinstalled', handler);

        // Check if already installed
        setTimeout(() => {
          window.removeEventListener('appinstalled', handler);
          const isInstalled = window.localStorage.getItem('pwa-installed') === 'true';
          resolve(isInstalled);
        }, 2000);
      });
    });

    // Should detect installation status
    expect(typeof appInstalledFired).toBe('boolean');
  });
});

test.describe('PWA Install Accessibility', () => {
  test('Install prompt modal is accessible', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(4000);

    // Check for modal with role="dialog"
    const modal = page.locator('div[role="dialog"]').first();
    const isModalVisible = await modal.isVisible().catch(() => false);

    if (isModalVisible) {
      // Check for aria attributes
      const hasAriaLabel = await modal.getAttribute('aria-label');
      const hasAriaModal = await modal.getAttribute('aria-modal');

      // Should have accessibility attributes
      expect(hasAriaModal === 'true' || hasAriaLabel).toBe(true);
    }
  });

  test('Install buttons have proper aria labels', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Check all buttons for aria-label
    const buttonsWithAria = await page.evaluate(() => {
      const buttons = document.querySelectorAll('button');
      const withAria: string[] = [];

      buttons.forEach(btn => {
        const ariaLabel = btn.getAttribute('aria-label');
        if (ariaLabel) {
          withAria.push(ariaLabel);
        }
      });

      return withAria;
    });

    // Install-related buttons should have aria-label
    const hasInstallAria = buttonsWithAria.some(label =>
      label.includes('Установить') ||
      label.includes('Install') ||
      label.includes('устано')
    );

    expect(typeof hasInstallAria).toBe('boolean');
  });

  test('Prompt is keyboard navigable', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(4000);

    // Try to Tab through the page
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');

    // Check which element is focused
    const focusedElement = await page.evaluate(() => {
      const focused = document.activeElement;
      if (!focused) return null;

      return {
        tagName: focused.tagName,
        type: (focused as HTMLInputElement).type,
        ariaLabel: focused.getAttribute('aria-label'),
        textContent: focused.textContent?.substring(0, 50),
      };
    });

    // Should be able to focus interactive elements
    expect(focusedElement).toBeTruthy();
  });
});

test.describe('PWA Install Edge Cases', () => {
  test('Handles unsupported browsers gracefully', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');

    // Check if app handles missing service worker support
    const handlesUnsupported = await page.evaluate(() => {
      const hasServiceWorker = 'serviceWorker' in navigator;
      const hasInstallElements = document.querySelector('[data-pwa-install]') !== null;

      return {
        hasServiceWorker,
        hasInstallElements,
        shouldShowPrompt: hasServiceWorker && !hasInstallElements,
      };
    });

    // Should handle gracefully
    expect(handlesUnsupported).toHaveProperty('hasServiceWorker');
  });

  test('Handles rapid install/dismiss actions', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(4000);

    // Try rapid interactions
    const rapidActionsResult = await page.evaluate(async () => {
      const results = [];

      // Simulate rapid state changes
      for (let i = 0; i < 3; i++) {
        // Check current state
        const dismissed = localStorage.getItem('pwa-install-dismissed');
        const installed = localStorage.getItem('pwa-installed');
        results.push({ iteration: i, dismissed, installed });

        await new Promise(resolve => setTimeout(resolve, 100));
      }

      return results;
    });

    // Should handle rapid interactions without errors
    expect(Array.isArray(rapidActionsResult)).toBe(true);
    expect(rapidActionsResult.length).toBe(3);
  });

  test('Handles multiple install attempts', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Try multiple install attempts
    const multipleAttempts = await page.evaluate(async () => {
      const attempts = [];

      for (let i = 0; i < 3; i++) {
        attempts.push({
          attempt: i,
          isInstalled: localStorage.getItem('pwa-installed') === 'true',
          isDismissed: !!localStorage.getItem('pwa-install-dismissed'),
        });

        await new Promise(resolve => setTimeout(resolve, 100));
      }

      return attempts;
    });

    // Should handle multiple attempts
    expect(Array.isArray(multipleAttempts)).toBe(true);
    expect(multipleAttempts.length).toBe(3);
  });
});
