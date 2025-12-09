/**
 * API клиент для работы с расписанием и плейлистами.
 */

import { client } from './client';

// ==================== Types ====================

export type RepeatType = 'none' | 'daily' | 'weekly' | 'weekdays' | 'weekends' | 'custom';

export interface ScheduleSlot {
  id: string;
  channel_id: string;
  playlist_id: string | null;
  playlist_name: string | null;
  start_date: string;
  start_time: string;
  end_time: string;
  repeat_type: RepeatType;
  repeat_days: number[] | null;
  repeat_until: string | null;
  title: string | null;
  description: string | null;
  color: string;
  is_active: boolean;
  priority: number;
  created_at?: string;
}

export interface ScheduleSlotCreate {
  channel_id: string;
  playlist_id?: string;
  start_date: string;
  start_time: string;
  end_time: string;
  repeat_type?: RepeatType;
  repeat_days?: number[];
  repeat_until?: string;
  title?: string;
  description?: string;
  color?: string;
  priority?: number;
}

export interface ScheduleSlotUpdate {
  playlist_id?: string;
  start_date?: string;
  start_time?: string;
  end_time?: string;
  repeat_type?: RepeatType;
  repeat_days?: number[];
  repeat_until?: string;
  title?: string;
  description?: string;
  color?: string;
  is_active?: boolean;
  priority?: number;
}

export interface TimeSlot {
  start_time: string;
  end_time: string;
  playlist_id?: string;
  title?: string;
  color?: string;
}

export interface ScheduleTemplate {
  id: string;
  name: string;
  description: string | null;
  channel_id: string | null;
  slots: TimeSlot[];
  is_public: boolean;
  created_at: string;
}

export interface ScheduleTemplateCreate {
  name: string;
  description?: string;
  channel_id?: string;
  slots: TimeSlot[];
  is_public?: boolean;
}

export interface Playlist {
  id: string;
  name: string;
  description: string | null;
  channel_id: string | null;
  group_id: string | null;
  group_name?: string | null;
  position: number;
  color: string;
  source_type: string;
  source_url: string | null;
  items: PlaylistItem[];
  items_count: number;
  total_duration: number;
  is_active: boolean;
  is_shuffled: boolean;
  created_at: string;
}

export interface PlaylistItem {
  url: string;
  title: string;
  duration?: number;
  type?: string;
}

export interface PlaylistCreate {
  name: string;
  description?: string;
  channel_id?: string;
  group_id?: string;
  color?: string;
  source_type?: string;
  source_url?: string;
  items?: PlaylistItem[];
  is_shuffled?: boolean;
}

export interface PlaylistUpdate {
  name?: string;
  description?: string;
  color?: string;
  group_id?: string;
  position?: number;
  items?: PlaylistItem[];
  is_active?: boolean;
  is_shuffled?: boolean;
}

// ==================== Playlist Groups ====================

export interface PlaylistGroup {
  id: string;
  name: string;
  description: string | null;
  channel_id: string | null;
  color: string;
  icon: string;
  position: number;
  is_expanded: boolean;
  is_active: boolean;
  playlists_count: number;
  created_at: string;
}

export interface PlaylistGroupWithPlaylists extends PlaylistGroup {
  playlists: Playlist[];
}

export interface PlaylistGroupCreate {
  name: string;
  description?: string;
  channel_id?: string;
  color?: string;
  icon?: string;
}

export interface PlaylistGroupUpdate {
  name?: string;
  description?: string;
  color?: string;
  icon?: string;
  position?: number;
  is_expanded?: boolean;
  is_active?: boolean;
}

export interface CalendarDay {
  date: string;
  slots: ScheduleSlot[];
  has_conflicts: boolean;
}

export interface BulkCopyRequest {
  source_date: string;
  target_dates: string[];
  channel_id: string;
}

export interface ApplyTemplateRequest {
  template_id: string;
  channel_id: string;
  target_dates: string[];
}

// ==================== API Functions ====================

export const scheduleApi = {
  // Schedule Slots
  getSlots: async (channelId: string, startDate: string, endDate: string): Promise<ScheduleSlot[]> => {
    const response = await client.get('/api/schedule/slots', {
      params: { channel_id: channelId, start_date: startDate, end_date: endDate }
    });
    return response.data;
  },

  getCalendar: async (channelId: string, year: number, month: number): Promise<CalendarDay[]> => {
    const response = await client.get('/api/schedule/calendar', {
      params: { channel_id: channelId, year, month }
    });
    return response.data;
  },

  createSlot: async (data: ScheduleSlotCreate): Promise<ScheduleSlot> => {
    const response = await client.post('/api/schedule/slots', data);
    return response.data;
  },

  updateSlot: async (slotId: string, data: ScheduleSlotUpdate): Promise<ScheduleSlot> => {
    const response = await client.put(`/api/schedule/slots/${slotId}`, data);
    return response.data;
  },

  deleteSlot: async (slotId: string): Promise<void> => {
    await client.delete(`/api/schedule/slots/${slotId}`);
  },

  copySchedule: async (data: BulkCopyRequest): Promise<{ created: number; skipped: number }> => {
    const response = await client.post('/api/schedule/copy', data);
    return response.data;
  },

  // Templates
  getTemplates: async (channelId?: string): Promise<ScheduleTemplate[]> => {
    const response = await client.get('/api/schedule/templates', {
      params: channelId ? { channel_id: channelId } : {}
    });
    return response.data;
  },

  createTemplate: async (data: ScheduleTemplateCreate): Promise<ScheduleTemplate> => {
    const response = await client.post('/api/schedule/templates', data);
    return response.data;
  },

  applyTemplate: async (data: ApplyTemplateRequest): Promise<{ created: number; skipped: number }> => {
    const response = await client.post('/api/schedule/templates/apply', data);
    return response.data;
  },

  deleteTemplate: async (templateId: string): Promise<void> => {
    await client.delete(`/api/schedule/templates/${templateId}`);
  },

  // Playlists
  getPlaylists: async (channelId?: string): Promise<Playlist[]> => {
    const response = await client.get('/api/schedule/playlists', {
      params: channelId ? { channel_id: channelId } : {}
    });
    return response.data;
  },

  createPlaylist: async (data: PlaylistCreate): Promise<Playlist> => {
    const response = await client.post('/api/schedule/playlists', data);
    return response.data;
  },

  updatePlaylist: async (playlistId: string, data: PlaylistUpdate): Promise<Playlist> => {
    const response = await client.put(`/api/schedule/playlists/${playlistId}`, data);
    return response.data;
  },

  deletePlaylist: async (playlistId: string): Promise<void> => {
    await client.delete(`/api/schedule/playlists/${playlistId}`);
  },

  movePlaylistToGroup: async (playlistId: string, groupId?: string, position?: number): Promise<Playlist> => {
    const response = await client.post(`/api/schedule/playlists/${playlistId}/move-to-group`, null, {
      params: { group_id: groupId, position }
    });
    return response.data;
  },

  // Playlist Groups
  getGroups: async (channelId?: string): Promise<PlaylistGroup[]> => {
    const response = await client.get('/api/schedule/groups', {
      params: channelId ? { channel_id: channelId } : {}
    });
    return response.data;
  },

  getGroupsWithPlaylists: async (channelId?: string): Promise<PlaylistGroupWithPlaylists[]> => {
    const response = await client.get('/api/schedule/groups/with-playlists', {
      params: channelId ? { channel_id: channelId } : {}
    });
    return response.data;
  },

  createGroup: async (data: PlaylistGroupCreate): Promise<PlaylistGroup> => {
    const response = await client.post('/api/schedule/groups', data);
    return response.data;
  },

  updateGroup: async (groupId: string, data: PlaylistGroupUpdate): Promise<PlaylistGroup> => {
    const response = await client.put(`/api/schedule/groups/${groupId}`, data);
    return response.data;
  },

  deleteGroup: async (groupId: string): Promise<void> => {
    await client.delete(`/api/schedule/groups/${groupId}`);
  },
};

export default scheduleApi;
