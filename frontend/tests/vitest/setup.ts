import '@testing-library/jest-dom/vitest';
import { vi } from 'vitest';
import React from 'react';

// Mock translations dictionary для тестов
const mockTranslations: Record<string, string> = {
  // Schedule
  'schedule.calendar': 'Расписание',
  'schedule.calendarDesc': 'Планирование трансляций',
  'schedule.create': 'Создать',
  'schedule.playlist': 'Плейлист',
  'schedule.addSlot': 'Добавить',
  'schedule.applyTemplate': 'Шаблон',
  'schedule.prevMonth': 'Предыдущий месяц',
  'schedule.nextMonth': 'Следующий месяц',
  'schedule.today': 'Сегодня',
  'schedule.copyDay': 'Копировать',
  'schedule.noSlots': 'Нет запланированных слотов',
  'schedule.clickToAdd': 'Нажмите "Добавить" чтобы создать',
  'schedule.confirmDelete': 'Удалить этот слот?',
  'schedule.copySchedule': 'Копировать расписание',
  'schedule.copyFrom': 'Источник',
  'schedule.selectWeek': 'Вся неделя',
  'schedule.selectMonth': 'Весь месяц',
  'schedule.clearSelection': 'Очистить',
  'schedule.selected': 'Выбрано',
  'schedule.source': 'Источник',
  'schedule.target': 'Цель',
  'schedule.copyTo': 'Копировать на',
  
  // Metrics
  'metrics.system': 'System Metrics',
  'metrics.cpu': 'CPU Usage',
  'metrics.memory': 'Memory Usage',
  'metrics.process': 'Process Metrics',
  'metrics.title': 'Метрики',
  'metrics.systemMetrics': 'System Metrics',
  'metrics.cpuUsage': 'CPU Usage',
  'metrics.memoryUsage': 'Memory Usage',
  'metrics.processMetrics': 'Process Metrics',
  'metrics.streamQuality': 'Stream Quality',
  
  // Admin
  'admin.systemHealth': 'System Health',
  'admin.online': 'ONLINE',
  'admin.offline': 'OFFLINE',
  'admin.cpu': 'CPU',
  'admin.memory': 'Memory',
  
  // Common
  'common.loading': 'Loading...',
  'common.error': 'Error',
  'common.success': 'Success',
  'common.system': 'System',
  'common.usage': 'Usage',
  
  // Auth
  'auth.login': 'Login',
  'auth.logout': 'Logout',
  'auth.invalidCredentials': 'Invalid credentials',
};

// Mock i18next с реальными переводами
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, defaultValue?: string) => {
      // Возвращаем перевод из словаря или default или ключ
      return mockTranslations[key] || defaultValue || key;
    },
    i18n: {
      language: 'ru',
      changeLanguage: vi.fn(),
    },
  }),
  Trans: ({ children }: { children: React.ReactNode }) => children,
  I18nextProvider: ({ children }: { children: React.ReactNode }) => children,
  initReactI18next: {
    type: '3rdParty',
    init: vi.fn(),
  },
}));

class MockResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}

if (typeof window !== 'undefined') {
  if (!window.matchMedia) {
    window.matchMedia = (query: string) => ({
      matches: query.includes('dark') ? false : true,
      media: query,
      onchange: null,
      addListener() {},
      removeListener() {},
      addEventListener() {},
      removeEventListener() {},
      dispatchEvent() {
        return false;
      },
    } as MediaQueryList);
  }

  if (!window.ResizeObserver) {
    window.ResizeObserver = MockResizeObserver as unknown as typeof ResizeObserver;
  }

  if (!window.IntersectionObserver) {
    window.IntersectionObserver = class {
      constructor(_callback: IntersectionObserverCallback) {}
      observe() {}
      unobserve() {}
      disconnect() {}
      takeRecords(): IntersectionObserverEntry[] {
        return [];
      }
    } as typeof IntersectionObserver;
  }

  document.documentElement.dataset.theme = document.documentElement.dataset.theme || 'light';
}
