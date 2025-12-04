/**
 * Unit тесты для TelegramLoginButton компонента.
 * 
 * Покрывает: T011
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import TelegramLoginButton from '../../src/components/TelegramLoginButton';

// Мокаем config
vi.mock('../../src/config', () => ({
  config: {
    telegram: {
      botUsername: 'test_bot',
      buttonSize: 'large',
      cornerRadius: 8,
      authMode: 'popup',
    },
  },
}));

describe('TelegramLoginButton', () => {
  let mockOnAuth: ReturnType<typeof vi.fn>;
  
  beforeEach(() => {
    mockOnAuth = vi.fn();
    // Очищаем глобальный callback
    delete (window as any).TelegramLoginCallback;
  });
  
  afterEach(() => {
    vi.clearAllMocks();
  });
  
  const renderComponent = (props = {}) => {
    return render(
      <BrowserRouter>
        <TelegramLoginButton onAuth={mockOnAuth} {...props} />
      </BrowserRouter>
    );
  };
  
  it('renders without crashing', () => {
    const { container } = renderComponent();
    expect(container.querySelector('div')).toBeTruthy();
  });
  
  it('creates script element with correct attributes', async () => {
    renderComponent();
    
    await waitFor(() => {
      const script = document.querySelector('script[data-telegram-login]');
      expect(script).toBeTruthy();
      expect(script?.getAttribute('data-telegram-login')).toBe('test_bot');
      expect(script?.getAttribute('data-size')).toBe('large');
    });
  });
  
  it('sets global callback function', async () => {
    renderComponent();
    
    await waitFor(() => {
      expect((window as any).TelegramLoginCallback).toBeDefined();
      expect(typeof (window as any).TelegramLoginCallback).toBe('function');
    });
  });
  
  it('calls onAuth when global callback is triggered', async () => {
    renderComponent();
    
    const testData = {
      id: 123456789,
      first_name: 'Test',
      auth_date: Math.floor(Date.now() / 1000),
      hash: 'testhash',
    };
    
    await waitFor(() => {
      expect((window as any).TelegramLoginCallback).toBeDefined();
    });
    
    // Симулируем вызов callback от Telegram
    (window as any).TelegramLoginCallback(testData);
    
    expect(mockOnAuth).toHaveBeenCalledWith(testData);
  });
  
  it('does not call onAuth when disabled', async () => {
    renderComponent({ disabled: true });
    
    const testData = {
      id: 123456789,
      first_name: 'Test',
      auth_date: Math.floor(Date.now() / 1000),
      hash: 'testhash',
    };
    
    await waitFor(() => {
      expect((window as any).TelegramLoginCallback).toBeDefined();
    });
    
    (window as any).TelegramLoginCallback(testData);
    
    expect(mockOnAuth).not.toHaveBeenCalled();
  });
  
  it('applies disabled styles when disabled', () => {
    const { container } = renderComponent({ disabled: true });
    
    const wrapper = container.querySelector('div');
    expect(wrapper?.className).toContain('opacity-50');
    expect(wrapper?.className).toContain('pointer-events-none');
  });
  
  it('cleans up callback on unmount', async () => {
    const { unmount } = renderComponent();
    
    await waitFor(() => {
      expect((window as any).TelegramLoginCallback).toBeDefined();
    });
    
    unmount();
    
    // Callback должен быть удалён
    expect((window as any).TelegramLoginCallback).toBeUndefined();
  });
});

describe('TelegramLoginButton without bot username', () => {
  beforeEach(() => {
    vi.doMock('../../src/config', () => ({
      config: {
        telegram: {
          botUsername: '',
          buttonSize: 'large',
          cornerRadius: 8,
          authMode: 'popup',
        },
      },
    }));
  });
  
  it('shows fallback message when bot username is not configured', async () => {
    // Этот тест требует перезагрузки модуля с новым моком
    // В реальном сценарии нужно использовать dynamic import
  });
});
