/**
 * E2E тесты для страницы расписания.
 * 
 * Покрывает полный пользовательский сценарий:
 * - Навигация на страницу расписания
 * - Создание слотов
 * - Редактирование слотов
 * - Удаление слотов
 * - Управление плейлистами
 * - Копирование расписания
 * - Применение шаблонов
 */

import { test, expect, Page } from '@playwright/test';

// ==================== Test Fixtures ====================

const TEST_USER = {
  email: 'admin@test.com',
  password: 'testpassword123',
};

// ==================== Helper Functions ====================

async function login(page: Page) {
  await page.goto('/login');
  await page.fill('[data-testid="email-input"]', TEST_USER.email);
  await page.fill('[data-testid="password-input"]', TEST_USER.password);
  await page.click('[data-testid="login-button"]');
  await page.waitForURL('/dashboard');
}

async function navigateToSchedule(page: Page) {
  await page.click('[data-testid="nav-schedule"]');
  await page.waitForURL('/schedule');
  await expect(page.locator('h1')).toContainText(/расписание|schedule/i);
}

// ==================== Schedule Page Navigation ====================

test.describe('Schedule Page Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('navigates to schedule page from dashboard', async ({ page }) => {
    await navigateToSchedule(page);
    await expect(page).toHaveURL('/schedule');
  });

  test('schedule link visible in navigation', async ({ page }) => {
    const scheduleLink = page.locator('[data-testid="nav-schedule"]');
    await expect(scheduleLink).toBeVisible();
  });

  test('shows correct tabs on schedule page', async ({ page }) => {
    await navigateToSchedule(page);
    
    await expect(page.getByRole('tab', { name: /календарь|calendar/i })).toBeVisible();
    await expect(page.getByRole('tab', { name: /плейлисты|playlists/i })).toBeVisible();
    await expect(page.getByRole('tab', { name: /шаблоны|templates/i })).toBeVisible();
  });
});

// ==================== Calendar View Tests ====================

test.describe('Calendar View', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await navigateToSchedule(page);
  });

  test('displays current month calendar', async ({ page }) => {
    const today = new Date();
    const monthName = today.toLocaleDateString('ru-RU', { month: 'long' });
    
    await expect(page.locator('[data-testid="calendar-header"]')).toContainText(new RegExp(monthName, 'i'));
  });

  test('can navigate to next month', async ({ page }) => {
    const nextButton = page.locator('[data-testid="calendar-next"]');
    await nextButton.click();
    
    const nextMonth = new Date();
    nextMonth.setMonth(nextMonth.getMonth() + 1);
    const expectedMonth = nextMonth.toLocaleDateString('ru-RU', { month: 'long' });
    
    await expect(page.locator('[data-testid="calendar-header"]')).toContainText(new RegExp(expectedMonth, 'i'));
  });

  test('can navigate to previous month', async ({ page }) => {
    const prevButton = page.locator('[data-testid="calendar-prev"]');
    await prevButton.click();
    
    const prevMonth = new Date();
    prevMonth.setMonth(prevMonth.getMonth() - 1);
    const expectedMonth = prevMonth.toLocaleDateString('ru-RU', { month: 'long' });
    
    await expect(page.locator('[data-testid="calendar-header"]')).toContainText(new RegExp(expectedMonth, 'i'));
  });

  test('can switch to week view', async ({ page }) => {
    const weekViewButton = page.getByRole('button', { name: /неделя|week/i });
    await weekViewButton.click();
    
    await expect(page.locator('[data-testid="week-view"]')).toBeVisible();
  });

  test('today is highlighted', async ({ page }) => {
    const today = new Date().getDate().toString();
    const todayCell = page.locator(`[data-testid="calendar-day-${today}"]`);
    
    await expect(todayCell).toHaveClass(/today/);
  });

  test('can click on day to create slot', async ({ page }) => {
    const futureDay = page.locator('[data-testid^="calendar-day-"]').nth(15);
    await futureDay.click();
    
    // Должно открыться модальное окно создания слота
    await expect(page.locator('[data-testid="slot-modal"]')).toBeVisible();
  });
});

// ==================== Slot Creation Tests ====================

test.describe('Slot Creation', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await navigateToSchedule(page);
  });

  test('opens slot creation modal on day click', async ({ page }) => {
    const dayCell = page.locator('[data-testid^="calendar-day-"]').nth(10);
    await dayCell.click();
    
    await expect(page.locator('[data-testid="slot-modal"]')).toBeVisible();
    await expect(page.locator('[data-testid="slot-modal-title"]')).toContainText(/новый слот|new slot/i);
  });

  test('can fill and submit slot form', async ({ page }) => {
    // Открываем модальное окно
    const dayCell = page.locator('[data-testid^="calendar-day-"]').nth(10);
    await dayCell.click();
    
    // Заполняем форму
    await page.fill('[data-testid="slot-title-input"]', 'Test Morning Show');
    await page.fill('[data-testid="slot-start-time"]', '10:00');
    await page.fill('[data-testid="slot-end-time"]', '12:00');
    
    // Выбираем плейлист
    await page.click('[data-testid="slot-playlist-select"]');
    await page.click('[data-testid="playlist-option"]');
    
    // Сохраняем
    await page.click('[data-testid="slot-save-button"]');
    
    // Проверяем, что слот появился в календаре
    await expect(page.locator('text=Test Morning Show')).toBeVisible();
  });

  test('validates required fields', async ({ page }) => {
    const dayCell = page.locator('[data-testid^="calendar-day-"]').nth(10);
    await dayCell.click();
    
    // Пытаемся сохранить без заполнения
    await page.click('[data-testid="slot-save-button"]');
    
    // Должны появиться ошибки валидации
    await expect(page.locator('[data-testid="title-error"]')).toBeVisible();
  });

  test('can set repeat options', async ({ page }) => {
    const dayCell = page.locator('[data-testid^="calendar-day-"]').nth(10);
    await dayCell.click();
    
    // Заполняем базовые поля
    await page.fill('[data-testid="slot-title-input"]', 'Daily Show');
    await page.fill('[data-testid="slot-start-time"]', '09:00');
    await page.fill('[data-testid="slot-end-time"]', '10:00');
    
    // Выбираем повторение
    await page.click('[data-testid="slot-repeat-select"]');
    await page.click('[data-testid="repeat-daily"]');
    
    // Устанавливаем дату окончания повторения
    await page.fill('[data-testid="repeat-until"]', '2025-12-31');
    
    await page.click('[data-testid="slot-save-button"]');
    
    // Проверяем, что слот создан с иконкой повторения
    await expect(page.locator('[data-testid="repeat-icon"]')).toBeVisible();
  });

  test('can choose custom color for slot', async ({ page }) => {
    const dayCell = page.locator('[data-testid^="calendar-day-"]').nth(10);
    await dayCell.click();
    
    await page.fill('[data-testid="slot-title-input"]', 'Colored Show');
    await page.fill('[data-testid="slot-start-time"]', '14:00');
    await page.fill('[data-testid="slot-end-time"]', '15:00');
    
    // Выбираем цвет
    await page.click('[data-testid="color-picker"]');
    await page.click('[data-testid="color-red"]');
    
    await page.click('[data-testid="slot-save-button"]');
    
    // Проверяем, что слот отображается красным цветом
    const slot = page.locator('text=Colored Show');
    await expect(slot).toHaveCSS('background-color', /rgb\(239, 68, 68\)/);
  });
});

// ==================== Slot Editing Tests ====================

test.describe('Slot Editing', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await navigateToSchedule(page);
    
    // Создаём тестовый слот
    const dayCell = page.locator('[data-testid^="calendar-day-"]').nth(10);
    await dayCell.click();
    await page.fill('[data-testid="slot-title-input"]', 'Slot to Edit');
    await page.fill('[data-testid="slot-start-time"]', '11:00');
    await page.fill('[data-testid="slot-end-time"]', '12:00');
    await page.click('[data-testid="slot-playlist-select"]');
    await page.click('[data-testid="playlist-option"]');
    await page.click('[data-testid="slot-save-button"]');
    await page.waitForSelector('text=Slot to Edit');
  });

  test('can edit existing slot', async ({ page }) => {
    await page.click('text=Slot to Edit');
    
    await expect(page.locator('[data-testid="slot-modal-title"]')).toContainText(/редактировать|edit/i);
    
    await page.fill('[data-testid="slot-title-input"]', 'Updated Slot Title');
    await page.click('[data-testid="slot-save-button"]');
    
    await expect(page.locator('text=Updated Slot Title')).toBeVisible();
    await expect(page.locator('text=Slot to Edit')).not.toBeVisible();
  });

  test('can delete slot', async ({ page }) => {
    await page.click('text=Slot to Edit');
    await page.click('[data-testid="slot-delete-button"]');
    
    // Подтверждаем удаление
    await page.click('[data-testid="confirm-delete"]');
    
    await expect(page.locator('text=Slot to Edit')).not.toBeVisible();
  });

  test('shows confirmation before delete', async ({ page }) => {
    await page.click('text=Slot to Edit');
    await page.click('[data-testid="slot-delete-button"]');
    
    await expect(page.locator('[data-testid="confirm-dialog"]')).toBeVisible();
    await expect(page.locator('[data-testid="confirm-dialog"]')).toContainText(/удалить|delete/i);
  });
});

// ==================== Playlist Management Tests ====================

test.describe('Playlist Management', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await navigateToSchedule(page);
    await page.click('[role="tab"][name*="плейлист" i], [role="tab"][name*="playlist" i]');
  });

  test('displays playlists tab', async ({ page }) => {
    await expect(page.locator('[data-testid="playlists-section"]')).toBeVisible();
  });

  test('can create new playlist', async ({ page }) => {
    await page.click('[data-testid="create-playlist-button"]');
    
    await page.fill('[data-testid="playlist-name-input"]', 'New Test Playlist');
    await page.fill('[data-testid="playlist-description-input"]', 'Description for test');
    
    // Добавляем трек
    await page.fill('[data-testid="track-url-input"]', 'https://youtube.com/watch?v=test123');
    await page.click('[data-testid="add-track-button"]');
    
    await page.click('[data-testid="playlist-save-button"]');
    
    await expect(page.locator('text=New Test Playlist')).toBeVisible();
  });

  test('can edit playlist', async ({ page }) => {
    // Предполагаем, что есть существующий плейлист
    await page.click('[data-testid="playlist-menu-button"]');
    await page.click('[data-testid="edit-playlist"]');
    
    await page.fill('[data-testid="playlist-name-input"]', 'Renamed Playlist');
    await page.click('[data-testid="playlist-save-button"]');
    
    await expect(page.locator('text=Renamed Playlist')).toBeVisible();
  });

  test('can delete playlist', async ({ page }) => {
    const playlistName = await page.locator('[data-testid="playlist-name"]').first().textContent();
    
    await page.click('[data-testid="playlist-menu-button"]');
    await page.click('[data-testid="delete-playlist"]');
    await page.click('[data-testid="confirm-delete"]');
    
    await expect(page.locator(`text=${playlistName}`)).not.toBeVisible();
  });

  test('can add tracks to playlist', async ({ page }) => {
    await page.click('[data-testid="playlist-card"]');
    await page.click('[data-testid="add-track-button"]');
    
    await page.fill('[data-testid="track-url-input"]', 'https://youtube.com/watch?v=newtrack');
    await page.click('[data-testid="confirm-add-track"]');
    
    await expect(page.locator('[data-testid="track-item"]')).toHaveCount(await page.locator('[data-testid="track-item"]').count() + 1);
  });

  test('can remove tracks from playlist', async ({ page }) => {
    await page.click('[data-testid="playlist-card"]');
    
    const initialCount = await page.locator('[data-testid="track-item"]').count();
    
    await page.click('[data-testid="remove-track-button"]');
    await page.click('[data-testid="confirm-delete"]');
    
    await expect(page.locator('[data-testid="track-item"]')).toHaveCount(initialCount - 1);
  });

  test('can reorder tracks via drag and drop', async ({ page }) => {
    await page.click('[data-testid="playlist-card"]');
    
    const firstTrack = page.locator('[data-testid="track-item"]').first();
    const secondTrack = page.locator('[data-testid="track-item"]').nth(1);
    
    const firstTrackName = await firstTrack.textContent();
    
    // Drag and drop
    await firstTrack.dragTo(secondTrack);
    
    // Проверяем, что порядок изменился
    const newSecondTrack = page.locator('[data-testid="track-item"]').nth(1);
    await expect(newSecondTrack).toContainText(firstTrackName!);
  });
});

// ==================== Schedule Copy Tests ====================

test.describe('Schedule Copy', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await navigateToSchedule(page);
  });

  test('can open copy modal from day context menu', async ({ page }) => {
    const dayCell = page.locator('[data-testid^="calendar-day-"]').nth(10);
    await dayCell.click({ button: 'right' });
    
    await page.click('[data-testid="copy-schedule-option"]');
    
    await expect(page.locator('[data-testid="copy-modal"]')).toBeVisible();
  });

  test('can select target dates for copy', async ({ page }) => {
    const dayCell = page.locator('[data-testid^="calendar-day-"]').nth(10);
    await dayCell.click({ button: 'right' });
    await page.click('[data-testid="copy-schedule-option"]');
    
    // Выбираем даты
    await page.click('[data-testid="target-date-15"]');
    await page.click('[data-testid="target-date-16"]');
    await page.click('[data-testid="target-date-17"]');
    
    await expect(page.locator('[data-testid="selected-dates-count"]')).toContainText('3');
  });

  test('can copy schedule to selected dates', async ({ page }) => {
    // Сначала создаём слот
    const dayCell = page.locator('[data-testid^="calendar-day-"]').nth(10);
    await dayCell.click();
    await page.fill('[data-testid="slot-title-input"]', 'Slot to Copy');
    await page.fill('[data-testid="slot-start-time"]', '10:00');
    await page.fill('[data-testid="slot-end-time"]', '11:00');
    await page.click('[data-testid="slot-playlist-select"]');
    await page.click('[data-testid="playlist-option"]');
    await page.click('[data-testid="slot-save-button"]');
    
    // Копируем
    await dayCell.click({ button: 'right' });
    await page.click('[data-testid="copy-schedule-option"]');
    await page.click('[data-testid="target-date-15"]');
    await page.click('[data-testid="copy-confirm-button"]');
    
    // Проверяем, что слот скопирован
    const targetDay = page.locator('[data-testid="calendar-day-15"]');
    await expect(targetDay.locator('text=Slot to Copy')).toBeVisible();
  });

  test('shows quick copy options', async ({ page }) => {
    const dayCell = page.locator('[data-testid^="calendar-day-"]').nth(10);
    await dayCell.click({ button: 'right' });
    await page.click('[data-testid="copy-schedule-option"]');
    
    await expect(page.locator('[data-testid="copy-next-week"]')).toBeVisible();
    await expect(page.locator('[data-testid="copy-next-month"]')).toBeVisible();
  });
});

// ==================== Template Tests ====================

test.describe('Schedule Templates', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await navigateToSchedule(page);
    await page.click('[role="tab"][name*="шаблон" i], [role="tab"][name*="template" i]');
  });

  test('displays templates section', async ({ page }) => {
    await expect(page.locator('[data-testid="templates-section"]')).toBeVisible();
  });

  test('can create new template', async ({ page }) => {
    await page.click('[data-testid="create-template-button"]');
    
    await page.fill('[data-testid="template-name-input"]', 'Weekend Template');
    
    // Добавляем слот в шаблон
    await page.click('[data-testid="add-template-slot"]');
    await page.click('[data-testid="template-day-saturday"]');
    await page.fill('[data-testid="template-slot-start"]', '10:00');
    await page.fill('[data-testid="template-slot-end"]', '12:00');
    
    await page.click('[data-testid="template-save-button"]');
    
    await expect(page.locator('text=Weekend Template')).toBeVisible();
  });

  test('can apply template', async ({ page }) => {
    // Предполагаем, что есть шаблон
    await page.click('[data-testid="template-card"]');
    await page.click('[data-testid="apply-template-button"]');
    
    // Выбираем даты
    await page.click('[data-testid="apply-next-week"]');
    await page.click('[data-testid="confirm-apply-button"]');
    
    // Проверяем успешное применение
    await expect(page.locator('[data-testid="success-toast"]')).toBeVisible();
  });

  test('can delete template', async ({ page }) => {
    const templateName = await page.locator('[data-testid="template-name"]').first().textContent();
    
    await page.click('[data-testid="template-menu-button"]');
    await page.click('[data-testid="delete-template"]');
    await page.click('[data-testid="confirm-delete"]');
    
    await expect(page.locator(`text=${templateName}`)).not.toBeVisible();
  });
});

// ==================== Error Handling Tests ====================

test.describe('Error Handling', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await navigateToSchedule(page);
  });

  test('shows error when slot creation fails', async ({ page, context }) => {
    // Мокаем API для возврата ошибки
    await context.route('**/api/schedule/slots', route => {
      route.fulfill({ status: 500, body: 'Internal Server Error' });
    });
    
    const dayCell = page.locator('[data-testid^="calendar-day-"]').nth(10);
    await dayCell.click();
    await page.fill('[data-testid="slot-title-input"]', 'Test Slot');
    await page.fill('[data-testid="slot-start-time"]', '10:00');
    await page.fill('[data-testid="slot-end-time"]', '11:00');
    await page.click('[data-testid="slot-playlist-select"]');
    await page.click('[data-testid="playlist-option"]');
    await page.click('[data-testid="slot-save-button"]');
    
    await expect(page.locator('[data-testid="error-toast"]')).toBeVisible();
  });

  test('shows overlap error for conflicting slots', async ({ page }) => {
    // Создаём первый слот
    const dayCell = page.locator('[data-testid^="calendar-day-"]').nth(10);
    await dayCell.click();
    await page.fill('[data-testid="slot-title-input"]', 'First Slot');
    await page.fill('[data-testid="slot-start-time"]', '10:00');
    await page.fill('[data-testid="slot-end-time"]', '12:00');
    await page.click('[data-testid="slot-playlist-select"]');
    await page.click('[data-testid="playlist-option"]');
    await page.click('[data-testid="slot-save-button"]');
    
    // Пытаемся создать пересекающийся слот
    await dayCell.click();
    await page.fill('[data-testid="slot-title-input"]', 'Overlapping Slot');
    await page.fill('[data-testid="slot-start-time"]', '11:00');
    await page.fill('[data-testid="slot-end-time"]', '13:00');
    await page.click('[data-testid="slot-playlist-select"]');
    await page.click('[data-testid="playlist-option"]');
    await page.click('[data-testid="slot-save-button"]');
    
    await expect(page.locator('[data-testid="error-toast"]')).toContainText(/пересечение|overlap/i);
  });

  test('handles network error gracefully', async ({ page, context }) => {
    await context.route('**/api/schedule/**', route => {
      route.abort('connectionfailed');
    });
    
    await page.reload();
    
    await expect(page.locator('[data-testid="error-state"]')).toBeVisible();
    await expect(page.locator('[data-testid="retry-button"]')).toBeVisible();
  });
});

// ==================== Mobile Responsiveness Tests ====================

test.describe('Mobile Responsiveness', () => {
  test.use({ viewport: { width: 375, height: 667 } });

  test.beforeEach(async ({ page }) => {
    await login(page);
    await navigateToSchedule(page);
  });

  test('calendar displays in compact mode on mobile', async ({ page }) => {
    await expect(page.locator('[data-testid="calendar-compact"]')).toBeVisible();
  });

  test('slot modal is full screen on mobile', async ({ page }) => {
    const dayCell = page.locator('[data-testid^="calendar-day-"]').first();
    await dayCell.click();
    
    const modal = page.locator('[data-testid="slot-modal"]');
    await expect(modal).toBeVisible();
    
    const box = await modal.boundingBox();
    expect(box?.width).toBeCloseTo(375, 10);
  });

  test('tabs are scrollable on mobile', async ({ page }) => {
    const tabs = page.locator('[data-testid="schedule-tabs"]');
    await expect(tabs).toHaveCSS('overflow-x', 'auto');
  });
});

// ==================== Keyboard Navigation Tests ====================

test.describe('Keyboard Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await navigateToSchedule(page);
  });

  test('can navigate calendar with arrow keys', async ({ page }) => {
    await page.locator('[data-testid^="calendar-day-"]').first().focus();
    
    await page.keyboard.press('ArrowRight');
    await page.keyboard.press('ArrowRight');
    await page.keyboard.press('Enter');
    
    await expect(page.locator('[data-testid="slot-modal"]')).toBeVisible();
  });

  test('can close modal with Escape', async ({ page }) => {
    const dayCell = page.locator('[data-testid^="calendar-day-"]').first();
    await dayCell.click();
    
    await expect(page.locator('[data-testid="slot-modal"]')).toBeVisible();
    
    await page.keyboard.press('Escape');
    
    await expect(page.locator('[data-testid="slot-modal"]')).not.toBeVisible();
  });

  test('Tab moves focus through form fields', async ({ page }) => {
    const dayCell = page.locator('[data-testid^="calendar-day-"]').first();
    await dayCell.click();
    
    await page.keyboard.press('Tab');
    await expect(page.locator('[data-testid="slot-title-input"]')).toBeFocused();
    
    await page.keyboard.press('Tab');
    await expect(page.locator('[data-testid="slot-start-time"]')).toBeFocused();
  });
});
