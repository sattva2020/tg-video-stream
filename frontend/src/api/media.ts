/**
 * Media API - работа с локальными медиафайлами на сервере
 */
import { client } from './client';

export interface MediaFile {
  path: string;           // Относительный путь от MUSIC_ROOT
  filename: string;       // Имя файла
  title?: string;         // Название трека (из тегов)
  artist?: string;        // Исполнитель
  album?: string;         // Альбом
  duration: number;       // Длительность в секундах
  size: number;           // Размер файла в байтах
  mime_type: string;      // MIME тип
}

export interface FolderInfo {
  path: string;
  name: string;
  files_count: number;
  total_size: number;
  total_duration: number;
  audio_count?: number;
  has_subdirs?: boolean;
}

export interface ScanResult {
  folder: string;
  files: MediaFile[];
  total: number;
}

/**
 * Получить список папок с аудиофайлами
 */
export const getFolders = async (): Promise<FolderInfo[]> => {
  const { data } = await client.get<FolderInfo[]>('/api/media/folders');
  return data;
};

/**
 * Просканировать папку и получить метаданные файлов
 */
export const scanFolder = async (
  folder: string,
  recursive = false
): Promise<ScanResult> => {
  const { data } = await client.get<ScanResult>('/api/media/scan', {
    params: { folder, recursive }
  });
  return data;
};

/**
 * Получить информацию о папке
 */
export const getFolderInfo = async (path: string): Promise<FolderInfo> => {
  const { data } = await client.get<FolderInfo>(`/api/media/folders/${encodeURIComponent(path)}/info`);
  return data;
};
