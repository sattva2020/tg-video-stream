/**
 * (migrated to .tsx to support JSX in wrapper)
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactNode } from 'react';

import {
  useScheduleSlots,
  useScheduleCalendar,
  usePlaylists,
  useScheduleTemplates,
} from '@/hooks/useScheduleQuery';
import { scheduleApi } from '@/api/schedule';
import type { ScheduleSlot, Playlist, ScheduleTemplate, CalendarDay } from '@/api/schedule';

// Mock API
vi.mock('@/api/schedule', () => ({
  scheduleApi: {
    getSlots: vi.fn(),
    getCalendar: vi.fn(),
    createSlot: vi.fn(),
    updateSlot: vi.fn(),
    deleteSlot: vi.fn(),
    getPlaylists: vi.fn(),
    createPlaylist: vi.fn(),
    updatePlaylist: vi.fn(),
    deletePlaylist: vi.fn(),
    getTemplates: vi.fn(),
    createTemplate: vi.fn(),
    deleteTemplate: vi.fn(),
    copySchedule: vi.fn(),
    applyTemplate: vi.fn(),
    expandSchedule: vi.fn(),
  },
}));

// Mock toast
vi.mock('@/hooks/useToast', () => ({
  useToast: () => ({
    success: vi.fn(),
    error: vi.fn(),
  }),
}));

// ==================== Test Fixtures ====================

const mockSlot: ScheduleSlot = {
  id: 'slot-1',
  channel_id: 'channel-1',
  playlist_id: 'playlist-1',
  user_id: 'user-1',
  date: '2025-11-27',
  start_time: '10:00:00',
  end_time: '12:00:00',
  title: 'Morning Show',
  description: null,
  color: '#3B82F6',
  repeat_type: 'none',
  repeat_until: null,
  repeat_days: null,
  is_active: true,
  created_at: '2025-11-27T00:00:00Z',
  updated_at: '2025-11-27T00:00:00Z',
};

const mockPlaylist: Playlist = {
  id: 'playlist-1',
  name: 'Test Playlist',
  description: 'Test description',
  user_id: 'user-1',
  channel_id: null,
  items: [
    { url: 'https://youtube.com/watch?v=123', title: 'Video 1', duration: 180 },
  ],
  created_at: '2025-11-27T00:00:00Z',
  updated_at: '2025-11-27T00:00:00Z',
};

const mockTemplate: ScheduleTemplate = {
  id: 'template-1',
  name: 'Weekend Template',
  description: 'Template for weekends',
  user_id: 'user-1',
  slots: [
    { day_of_week: 6, start_time: '10:00', end_time: '12:00', title: 'Saturday Show' },
  ],
  created_at: '2025-11-27T00:00:00Z',
  updated_at: '2025-11-27T00:00:00Z',
};

const mockCalendarDay: CalendarDay = {
  date: '2025-11-27',
  slots: [mockSlot],
  total_duration: 7200,
};

// ==================== Test Wrapper ====================

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    );
  };
}

// ==================== Tests ====================

describe('useScheduleSlots', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches slots successfully', async () => {
    vi.mocked(scheduleApi.getSlots).mockResolvedValue([mockSlot]);

    const { result } = renderHook(
      () => useScheduleSlots('channel-1', '2025-11-27', '2025-11-28'),
      { wrapper: createWrapper() }
    );

    expect(result.current.isLoading).toBe(true);

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual([mockSlot]);
    expect(scheduleApi.getSlots).toHaveBeenCalledWith('channel-1', '2025-11-27', '2025-11-28');
  });

  it('handles fetch error', async () => {
    vi.mocked(scheduleApi.getSlots).mockRejectedValue(new Error('Network error'));

    const { result } = renderHook(
      () => useScheduleSlots('channel-1', '2025-11-27', '2025-11-28'),
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error).toBeDefined();
  });

  it('does not fetch when disabled', () => {
    const { result } = renderHook(
      () => useScheduleSlots('', '2025-11-27', '2025-11-28'),
      { wrapper: createWrapper() }
    );

    expect(result.current.isLoading).toBe(false);
    expect(scheduleApi.getSlots).not.toHaveBeenCalled();
  });
});

describe('useScheduleCalendar', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches calendar data', async () => {
    vi.mocked(scheduleApi.getCalendar).mockResolvedValue([mockCalendarDay]);

    const { result } = renderHook(
      () => useScheduleCalendar('channel-1', 2025, 11),
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual([mockCalendarDay]);
  });
});

describe('usePlaylists', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches playlists successfully', async () => {
    vi.mocked(scheduleApi.getPlaylists).mockResolvedValue([mockPlaylist]);

    const { result } = renderHook(
      () => usePlaylists(),
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual([mockPlaylist]);
  });

  it('fetches playlists for specific channel', async () => {
    vi.mocked(scheduleApi.getPlaylists).mockResolvedValue([mockPlaylist]);

    renderHook(
      () => usePlaylists('channel-1'),
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(scheduleApi.getPlaylists).toHaveBeenCalledWith('channel-1');
    });
  });
});

describe('useScheduleTemplates', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches templates successfully', async () => {
    vi.mocked(scheduleApi.getTemplates).mockResolvedValue([mockTemplate]);

    const { result } = renderHook(
      () => useScheduleTemplates(),
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual([mockTemplate]);
  });
});
