import { client } from './client';

// Live Stream Types
export type LiveStreamStatus = 'idle' | 'active' | 'paused' | 'stopped' | 'error';
export type IngestionType = 'rtmp' | 'srt' | 'webrtc_camera' | 'webrtc_screen';

export interface LiveStream {
  id: number;
  owner_id: number;
  chat_id: number;
  title: string;
  status: LiveStreamStatus;
  ingestion_type: IngestionType;
  ingestion_url?: string;
  stream_key?: string;
  viewer_count: number;
  latency_ms?: number;
  preview_url?: string;
  recording_enabled: boolean;
  active_recording_id?: number;
  max_guests: number;
  current_guest_count: number;
  quality_preset: string;
  is_chat_enabled: boolean;
  last_error?: string;
  error_count: number;
  created_at: string;
  started_at?: string;
  went_live_at?: string;
  stopped_at?: string;
}

export interface CreateLiveStreamData {
  title: string;
  chat_id: number;
  ingestion_type: IngestionType;
  quality_preset?: string;
  max_guests?: number;
  recording_enabled?: boolean;
  is_chat_enabled?: boolean;
}

export interface UpdateLiveStreamData {
  title?: string;
  quality_preset?: string;
  max_guests?: number;
  recording_enabled?: boolean;
  is_chat_enabled?: boolean;
}

export interface LiveStreamListResponse {
  total: number;
  streams: LiveStream[];
  page: number;
  page_size: number;
}

export interface StartLiveStreamResponse {
  stream_id: number;
  title: string;
  status: string;
  ingestion_url?: string;
  stream_key?: string;
  preview_url?: string;
  message: string;
}

export interface StopLiveStreamResponse {
  stream_id: number;
  title: string;
  status: string;
  message: string;
}

export interface SwitchToLiveStreamResponse {
  stream_id: number;
  title: string;
  status: string;
  message: string;
}

// Guest Session Types
export type GuestSessionStatus = 'pending' | 'accepted' | 'active' | 'rejected' | 'left' | 'kicked';

export interface GuestPermissions {
  can_speak: boolean;
  can_share_video: boolean;
  can_share_screen: boolean;
  can_control_stream: boolean;
  can_invite_others: boolean;
}

export interface GuestSession {
  id: number;
  live_stream_id: number;
  user_id: number;
  full_name?: string;
  username?: string;
  email?: string;
  status: GuestSessionStatus;
  permissions: GuestPermissions;
  webrtc_connection_id?: string;
  connection_quality?: string;
  invite_token?: string;
  invite_message?: string;
  rejection_reason?: string;
  leave_reason?: string;
  created_at: string;
  joined_at?: string;
  left_at?: string;
  last_active_at?: string;
}

export interface InviteGuestRequest {
  stream_id: number;
  guest_email: string;
  invite_message?: string;
}

export interface InviteGuestResponse {
  guest_session_id: number;
  invite_token: string;
  invite_link: string;
  message: string;
}

export interface UpdateGuestPermissionsRequest {
  can_speak?: boolean;
  can_share_video?: boolean;
  can_share_screen?: boolean;
  can_control_stream?: boolean;
  can_invite_others?: boolean;
}

export interface RejectInvitationRequest {
  rejection_reason?: string;
}

export interface LeaveSessionRequest {
  leave_reason?: string;
}

// Recording Types
export type RecordingStatus = 'recording' | 'processing' | 'ready' | 'error' | 'deleted';
export type RecordingFormat = 'mp4' | 'webm' | 'mkv' | 'hls';

export interface Recording {
  id: number;
  live_stream_id: number;
  file_path: string;
  file_url?: string;
  duration?: number;
  file_size?: number;
  status: RecordingStatus;
  started_at: string;
  ended_at?: string;
  created_at: string;
  updated_at: string;
  format: RecordingFormat;
  bitrate?: number;
  resolution?: string;
  video_codec?: string;
  audio_codec?: string;
  thumbnail_url?: string;
  preview_url?: string;
  error_message?: string;
}

export interface RecordingListResponse {
  total: number;
  recordings: Recording[];
  page: number;
  page_size: number;
}

// Stream Preview Types
export interface StreamPreviewResponse {
  stream_id: number;
  preview_url?: string;
  thumbnail_url?: string;
  is_available: boolean;
  is_ready: boolean;
  health_score?: number;
  latency_ms?: number;
  bitrate?: number;
  connection_quality?: string;
  issues: string[];
  warnings: string[];
}

export interface GeneratePreviewResponse {
  stream_id: number;
  preview_url: string;
  expires_at: string;
  message: string;
}

export interface StreamHealthResponse {
  stream_id: number;
  health_score: number;
  status: 'healthy' | 'degraded' | 'unhealthy';
  latency_ms?: number;
  bitrate?: number;
  connection_quality?: string;
  issues: string[];
  warnings: string[];
  recommendations: string[];
}

// Live Streams API
export const liveApi = {
  // Live Stream Management
  listStreams: async (page = 1, pageSize = 20, status?: LiveStreamStatus) => {
    const params: Record<string, string | number> = { page, page_size: pageSize };
    if (status) params.status = status;
    const response = await client.get<LiveStreamListResponse>('/api/v1/live/streams', { params });
    return response.data;
  },

  getStream: async (streamId: number) => {
    const response = await client.get<LiveStream>(`/api/v1/live/streams/${streamId}`);
    return response.data;
  },

  createStream: async (data: CreateLiveStreamData) => {
    const response = await client.post<LiveStream>('/api/v1/live/streams', data);
    return response.data;
  },

  updateStream: async (streamId: number, data: UpdateLiveStreamData) => {
    const response = await client.put<LiveStream>(`/api/v1/live/streams/${streamId}`, data);
    return response.data;
  },

  deleteStream: async (streamId: number) => {
    const response = await client.delete<{ message: string }>(`/api/v1/live/streams/${streamId}`);
    return response.data;
  },

  startStream: async (streamId: number) => {
    const response = await client.post<StartLiveStreamResponse>(`/api/v1/live/streams/${streamId}/start`);
    return response.data;
  },

  stopStream: async (streamId: number) => {
    const response = await client.post<StopLiveStreamResponse>(`/api/v1/live/streams/${streamId}/stop`);
    return response.data;
  },

  switchToLive: async (streamId: number) => {
    const response = await client.post<SwitchToLiveStreamResponse>(`/api/v1/live/streams/${streamId}/switch`);
    return response.data;
  },

  // Guest Session Management
  inviteGuest: async (data: InviteGuestRequest) => {
    const response = await client.post<InviteGuestResponse>('/api/v1/live/guests/invite', data);
    return response.data;
  },

  listGuests: async (streamId: number) => {
    const response = await client.get<{ guests: GuestSession[] }>(`/api/v1/live/guests?stream_id=${streamId}`);
    return response.data;
  },

  getGuest: async (guestId: number) => {
    const response = await client.get<GuestSession>(`/api/v1/live/guests/${guestId}`);
    return response.data;
  },

  updateGuestPermissions: async (guestId: number, data: UpdateGuestPermissionsRequest) => {
    const response = await client.put<GuestSession>(`/api/v1/live/guests/${guestId}`, data);
    return response.data;
  },

  removeGuest: async (guestId: number) => {
    const response = await client.delete<{ message: string }>(`/api/v1/live/guests/${guestId}`);
    return response.data;
  },

  acceptInvitation: async (guestId: number) => {
    const response = await client.post<GuestSession>(`/api/v1/live/guests/${guestId}/accept`);
    return response.data;
  },

  rejectInvitation: async (guestId: number, data: RejectInvitationRequest) => {
    const response = await client.post<GuestSession>(`/api/v1/live/guests/${guestId}/reject`, data);
    return response.data;
  },

  joinSession: async (guestId: number) => {
    const response = await client.post<GuestSession>(`/api/v1/live/guests/${guestId}/join`);
    return response.data;
  },

  leaveSession: async (guestId: number, data: LeaveSessionRequest) => {
    const response = await client.post<GuestSession>(`/api/v1/live/guests/${guestId}/leave`, data);
    return response.data;
  },

  // Recording Management
  listRecordings: async (page = 1, pageSize = 20, status?: RecordingStatus, streamId?: number) => {
    const params: Record<string, string | number> = { page, page_size: pageSize };
    if (status) params.status = status;
    if (streamId) params.stream_id = streamId;
    const response = await client.get<RecordingListResponse>('/api/v1/recordings', { params });
    return response.data;
  },

  getStreamRecordings: async (streamId: number) => {
    const response = await client.get<{ recordings: Recording[] }>(`/api/v1/recordings/stream/${streamId}`);
    return response.data;
  },

  getRecording: async (recordingId: number) => {
    const response = await client.get<Recording>(`/api/v1/recordings/${recordingId}`);
    return response.data;
  },

  deleteRecording: async (recordingId: number) => {
    const response = await client.delete<{ message: string }>(`/api/v1/recordings/${recordingId}`);
    return response.data;
  },

  // Stream Preview
  getPreview: async (streamId: number) => {
    const response = await client.get<StreamPreviewResponse>(`/api/v1/live/preview/${streamId}`);
    return response.data;
  },

  generatePreview: async (streamId: number) => {
    const response = await client.post<GeneratePreviewResponse>(`/api/v1/live/preview/${streamId}/generate`);
    return response.data;
  },

  getStreamHealth: async (streamId: number) => {
    const response = await client.get<StreamHealthResponse>(`/api/v1/live/preview/${streamId}/health`);
    return response.data;
  },
};
