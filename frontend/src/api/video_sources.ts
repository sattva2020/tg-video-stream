import { client } from './client';

export interface VideoSourceMetadata {
  video_id?: string;
  playlist_id?: string;
  channel_id?: string;
  file_id?: string;
  extension?: string;
  [key: string]: any;
}

export interface VideoSourceDetectRequest {
  url: string;
}

export interface VideoSourceDetectResponse {
  valid: boolean;
  source_type: string;
  source_type_label: string;
  metadata: VideoSourceMetadata;
  normalized_url: string;
  error?: string;
}

export interface VideoSourceValidateRequest {
  url: string;
  check_availability?: boolean;
}

export interface VideoSourceValidateResponse {
  valid: boolean;
  source_type: string;
  source_type_label: string;
  is_available?: boolean;
  compatibility_issues: string[];
  error?: string;
}

export interface SupportedSource {
  type: string;
  label: string;
  description: string;
  examples: string[];
}

export interface SupportedSourcesResponse {
  sources: SupportedSource[];
  total_count: number;
}

const VIDEO_SOURCES_BASE = '/api/video-sources';

export const videoSourcesApi = {
  detectSource: async (url: string) => {
    const response = await client.post<VideoSourceDetectResponse>(
      `${VIDEO_SOURCES_BASE}/detect`,
      { url }
    );
    return response.data;
  },

  validateSource: async (url: string, checkAvailability = false) => {
    const response = await client.post<VideoSourceValidateResponse>(
      `${VIDEO_SOURCES_BASE}/validate`,
      {
        url,
        check_availability: checkAvailability,
      }
    );
    return response.data;
  },

  getSupportedSources: async () => {
    const response = await client.get<SupportedSourcesResponse>(
      `${VIDEO_SOURCES_BASE}/supported`
    );
    return response.data;
  },
};
