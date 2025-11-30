/**
 * Unit тесты для хука useTelegramAuth.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { useTelegramAuth } from '../../src/hooks/useTelegramAuth';

// Мокаем navigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Мокаем API
vi.mock('../../src/services/telegramAuth', () => ({
  telegramAuthApi: {
    auth: vi.fn(),
  },
}));

import { telegramAuthApi } from '../../src/services/telegramAuth';

describe('useTelegramAuth', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });
  
  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <BrowserRouter>{children}</BrowserRouter>
  );
  
  const testData = {
    id: 123456789,
    first_name: 'Test',
    auth_date: Math.floor(Date.now() / 1000),
    hash: 'testhash',
  };
  
  it('returns initial state', () => {
    const { result } = renderHook(() => useTelegramAuth(), { wrapper });
    
    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBeNull();
    expect(typeof result.current.handleTelegramAuth).toBe('function');
    expect(typeof result.current.clearError).toBe('function');
  });
  
  it('handles successful auth and navigates to dashboard', async () => {
    const mockResponse = {
      success: true,
      user: {
        id: 'uuid',
        status: 'approved',
        role: 'user',
      },
      is_new_user: false,
      message: 'Success',
    };
    
    (telegramAuthApi.auth as any).mockResolvedValue(mockResponse);
    
    const { result } = renderHook(() => useTelegramAuth(), { wrapper });
    
    await act(async () => {
      await result.current.handleTelegramAuth(testData);
    });
    
    expect(mockNavigate).toHaveBeenCalledWith('/dashboard');
    expect(result.current.error).toBeNull();
  });
  
  it('navigates to pending-approval for pending users', async () => {
    const mockResponse = {
      success: true,
      user: {
        id: 'uuid',
        status: 'pending',
        role: 'user',
      },
      is_new_user: true,
      message: 'Success',
    };
    
    (telegramAuthApi.auth as any).mockResolvedValue(mockResponse);
    
    const { result } = renderHook(() => useTelegramAuth(), { wrapper });
    
    await act(async () => {
      await result.current.handleTelegramAuth(testData);
    });
    
    expect(mockNavigate).toHaveBeenCalledWith('/pending-approval');
  });
  
  it('sets error on 400 response', async () => {
    const error = {
      response: {
        status: 400,
        data: { detail: 'Invalid signature' },
      },
    };
    
    (telegramAuthApi.auth as any).mockRejectedValue(error);
    
    const { result } = renderHook(() => useTelegramAuth(), { wrapper });
    
    await act(async () => {
      await result.current.handleTelegramAuth(testData);
    });
    
    expect(result.current.error).toBe('Invalid signature');
    expect(mockNavigate).not.toHaveBeenCalled();
  });
  
  it('sets error on 409 response', async () => {
    const error = {
      response: {
        status: 409,
      },
    };
    
    (telegramAuthApi.auth as any).mockRejectedValue(error);
    
    const { result } = renderHook(() => useTelegramAuth(), { wrapper });
    
    await act(async () => {
      await result.current.handleTelegramAuth(testData);
    });
    
    expect(result.current.error).toContain('привязан');
  });
  
  it('clears error when clearError is called', async () => {
    const error = { response: { status: 400 } };
    (telegramAuthApi.auth as any).mockRejectedValue(error);
    
    const { result } = renderHook(() => useTelegramAuth(), { wrapper });
    
    await act(async () => {
      await result.current.handleTelegramAuth(testData);
    });
    
    expect(result.current.error).not.toBeNull();
    
    act(() => {
      result.current.clearError();
    });
    
    expect(result.current.error).toBeNull();
  });
  
  it('calls onSuccess callback when provided', async () => {
    const mockOnSuccess = vi.fn();
    const mockResponse = {
      success: true,
      user: { id: 'uuid', status: 'approved', role: 'user' },
      is_new_user: false,
      message: 'Success',
    };
    
    (telegramAuthApi.auth as any).mockResolvedValue(mockResponse);
    
    const { result } = renderHook(() => useTelegramAuth(mockOnSuccess), { wrapper });
    
    await act(async () => {
      await result.current.handleTelegramAuth(testData);
    });
    
    expect(mockOnSuccess).toHaveBeenCalledWith(mockResponse);
  });
});
