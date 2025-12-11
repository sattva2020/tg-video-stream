/**
 * Media API - работа с локальными медиафайлами на сервере
 */
import apiClient from './client';

export interface AudioMetadata {
  file_path: string;
  title?: string;
  artist?: string;
  album?: string;
  duration?: number;
}

export interface FolderInfo {
  path: string;
  audio_count: number;
  has_subdirs: boolean;
}

export interface ScanResult {
  folder: string;
  files: AudioMetadata[];
  total: number;
}

/**
 * Получить список папок с аудиофайлами
 */
export const getFolders = async (): Promise<FolderInfo[]> => {
  const { data } = await apiClient.get<FolderInfo[]>('/media/folders');
  return data;
};

/**
 * Просканировать папку и получить метаданные файлов
 */
export const scanFolder = async (
  folder: string,
  recursive = false
): Promise<ScanResult> => {
  const { data } = await apiClient.get<ScanResult>('/media/scan', {
    params: { folder, recursive }
  });
  return data;
};

/**
 * Получить информацию о папке
 */
export const getFolderInfo = async (path: string): Promise<FolderInfo> => {
  const { data } = await apiClient.get<FolderInfo>(`/media/folders/${encodeURIComponent(path)}/info`);
  return data;
};
