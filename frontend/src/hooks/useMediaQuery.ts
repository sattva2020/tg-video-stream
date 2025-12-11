/**
 * React Query хуки для работы с медиафайлами
 */
import { useQuery } from '@tanstack/react-query';
import { getFolders, scanFolder, getFolderInfo } from '../api/media';

/**
 * Получить список папок с музыкой
 */
export const useMediaFolders = () => {
  return useQuery({
    queryKey: ['media', 'folders'],
    queryFn: getFolders,
    staleTime: 5 * 60 * 1000, // 5 минут
  });
};

/**
 * Просканировать папку
 */
export const useScanFolder = (folder: string, recursive = false, enabled = false) => {
  return useQuery({
    queryKey: ['media', 'scan', folder, recursive],
    queryFn: () => scanFolder(folder, recursive),
    enabled: enabled && !!folder,
    staleTime: 30 * 1000, // 30 секунд
  });
};

/**
 * Получить информацию о папке
 */
export const useFolderInfo = (path: string, enabled = false) => {
  return useQuery({
    queryKey: ['media', 'folder-info', path],
    queryFn: () => getFolderInfo(path),
    enabled: enabled && !!path,
  });
};
