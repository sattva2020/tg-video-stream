/**
 * Video source types for multi-platform video source integration
 * Feature: 007-multi-platform-video-source-integration
 */

/** Supported video source types */
export type SourceType =
  | 'youtube'
  | 'vimeo'
  | 'dailymotion'
  | 'twitch'
  | 'direct'
  | 'hls'
  | 'dash'
  | 'google_drive'
  | 'dropbox'
  | 'onedrive'
  | 'rss_feed'
  | 'unknown';

/** Playback status for a video source */
export type VideoSourceStatus = 'playing' | 'queued' | 'error' | 'completed';

/** Request to detect video source type from URL */
export interface VideoSourceDetectRequest {
  /** URL to detect */
  url: string;
}

/** Response from video source detection */
export interface VideoSourceDetectResponse {
  /** Whether the URL is valid */
  valid: boolean;
  /** Detected source type */
  source_type: SourceType;
  /** Human-readable source type label */
  source_type_label: string;
  /** Extracted metadata (video IDs, file IDs, etc.) */
  metadata: Record<string, unknown>;
  /** Normalized URL */
  normalized_url: string;
  /** Error message if detection failed */
  error?: string;
}

/** Request to validate video source URL */
export interface VideoSourceValidateRequest {
  /** URL to validate */
  url: string;
  /** Whether to check availability (makes HTTP requests) */
  check_availability?: boolean;
}

/** Response from video source validation */
export interface VideoSourceValidateResponse {
  /** Whether the URL is valid */
  valid: boolean;
  /** Detected source type */
  source_type: SourceType;
  /** Human-readable source type label */
  source_type_label: string;
  /** Whether the video is available (if check_availability was true) */
  is_available?: boolean;
  /** List of compatibility issues (e.g., codec incompatibility) */
  compatibility_issues: string[];
  /** Error message if validation failed */
  error?: string;
}

/** Information about a supported video source */
export interface SupportedSourceInfo {
  /** Source type identifier */
  type: SourceType;
  /** Human-readable label */
  label: string;
  /** Description of the source type */
  description: string;
  /** Example URLs */
  examples: string[];
}

/** Response listing all supported video sources */
export interface SupportedSourcesResponse {
  /** List of supported sources */
  sources: SupportedSourceInfo[];
  /** Total count of supported sources */
  total_count: number;
}

/** Video source item (playlist entry or standalone video) */
export interface VideoSource {
  /** Unique identifier */
  id: string;
  /** Channel ID (if assigned to a channel) */
  channel_id?: string;
  /** Stream ID (Clean Architecture) */
  stream_id?: string;
  /** Video URL */
  url: string;
  /** Video title */
  title?: string;
  /** Source type */
  type: SourceType;
  /** Playback status */
  status?: VideoSourceStatus;
  /** Duration in seconds (null if unknown) */
  duration?: number | null;
  /** URL to video thumbnail image */
  thumbnail_url?: string;
  /** Platform-specific metadata (video IDs, channel info, etc.) */
  source_metadata?: Record<string, unknown> | null;
  /** Whether this is a live stream (HLS/DASH) */
  is_live?: boolean;
  /** Whether authentication is needed for cloud storage */
  requires_auth?: boolean;
  /** Encrypted token for cloud storage access */
  auth_token?: string;
  /** Preferred video quality (e.g., '1080p', '720p') */
  quality?: string;
  /** Position in queue */
  position?: number;
  /** ID of user who created this entry */
  created_by?: string;
  /** Creation timestamp */
  created_at: string;
  /** File ID (for local files) */
  file_id?: string;
}

/** Request to create a video source */
export interface VideoSourceCreate {
  /** Video URL */
  url: string;
  /** Video title (optional, will be fetched if not provided) */
  title?: string;
  /** Source type (optional, will be auto-detected if not provided) */
  type?: SourceType;
  /** Preferred video quality */
  quality?: string;
  /** Position in queue */
  position?: number;
}

/** Request to update a video source */
export interface VideoSourceUpdate {
  /** Video URL */
  url?: string;
  /** Video title */
  title?: string;
  /** Source type */
  type?: SourceType;
  /** Playback status */
  status?: VideoSourceStatus;
  /** Duration in seconds */
  duration?: number;
  /** Thumbnail URL */
  thumbnail_url?: string;
  /** Platform-specific metadata */
  source_metadata?: Record<string, unknown>;
  /** Whether this is a live stream */
  is_live?: boolean;
  /** Whether authentication is needed */
  requires_auth?: boolean;
  /** Auth token for cloud storage */
  auth_token?: string;
  /** Preferred video quality */
  quality?: string;
  /** Position in queue */
  position?: number;
}

/** Metadata extracted from video source */
export interface VideoSourceMetadata {
  /** Video ID (platform-specific) */
  video_id?: string;
  /** Playlist ID (for playlists) */
  playlist_id?: string;
  /** Channel ID (for channels) */
  channel_id?: string;
  /** File extension (for direct URLs) */
  extension?: string;
  /** MIME type */
  mime_type?: string;
  /** File size in bytes (for direct URLs) */
  file_size?: number;
  /** Additional platform-specific data */
  additional_data?: Record<string, unknown>;
}

/** Cloud storage authentication info */
export interface CloudStorageAuth {
  /** Type of cloud storage */
  provider: 'google_drive' | 'dropbox' | 'onedrive';
  /** Access token */
  access_token: string;
  /** Refresh token (if available) */
  refresh_token?: string;
  /** Token expiration timestamp */
  expires_at?: string;
}
