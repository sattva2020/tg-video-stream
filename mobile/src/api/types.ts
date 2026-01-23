/**
 * Common API types for mobile app
 * Shared across all API modules
 */

// Base API response wrapper
export interface ApiResponse<T> {
  data: T;
  message?: string;
  error?: string;
}

// Pagination params
export interface PaginationParams {
  page?: number;
  limit?: number;
  offset?: number;
}

// Paginated response
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  limit: number;
  hasMore: boolean;
}

// Sort params
export interface SortParams {
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
}

// Common filter params
export interface FilterParams {
  search?: string;
  status?: string;
  from?: string;
  to?: string;
}

// Auth types
export interface LoginCredentials {
  email: string;
  password: string;
  totp_code?: string;
}

export interface OAuthParams {
  provider: 'google' | 'telegram' | 'github';
  code: string;
  state?: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
}

export enum UserRole {
  USER = 'user',
  ADMIN = 'admin',
  SUPERADMIN = 'superadmin',
  MODERATOR = 'moderator',
  OPERATOR = 'operator',
}

export interface User {
  id: string;
  email?: string;
  full_name?: string;
  profile_picture_url?: string;
  role: UserRole;
  status?: string;
  last_login?: string;
  email_verified?: boolean;
  google_id?: string;
  telegram_id?: number;
  telegram_username?: string;
  totp_enabled?: boolean;
}

// Channel types
export type ChannelStatus = 'online' | 'offline' | 'error';

export interface Channel {
  id: number;
  username: string;
  chat_id: number;
  status: ChannelStatus;
  title?: string;
  description?: string;
  is_default: boolean;
  created_at: string;
  updated_at?: string;
}

// Stream types
export interface Stream {
  id: number;
  channel_id: number;
  status: 'live' | 'stopped' | 'error';
  start_time?: string;
  listener_count: number;
  error_message?: string;
}

// Playlist types
export interface Track {
  id: number;
  title: string;
  artist?: string;
  duration?: number;
  url?: string;
  order: number;
}

export interface Playlist {
  id: number;
  name: string;
  tracks: Track[];
  created_at: string;
  updated_at?: string;
}

// Notification types
export interface NotificationRule {
  id: number;
  name: string;
  event_type: string;
  enabled: boolean;
  channels: number[];
  created_at: string;
}

export interface NotificationLog {
  id: number;
  rule_id: number;
  event_type: string;
  message: string;
  sent_at: string;
  success: boolean;
}

// Analytics types
export interface AnalyticsData {
  date: string;
  listeners: number;
  streams: number;
}

export interface Stats {
  total_listeners: number;
  total_streams: number;
  active_channels: number;
}

// Device registration for push notifications
export interface DeviceRegistration {
  device_id: string;
  platform: 'ios' | 'android';
  push_token: string;
  app_version?: string;
  os_version?: string;
}

// Error types
export interface ApiError {
  detail: string;
  status: number;
  code?: string;
}
