import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { streamingPlatformsApi, StreamingPlatform, PlatformType } from '../../api/streaming_platforms';
import { Loader2, Search, Check, AlertCircle, Plus, Youtube, Twitch } from 'lucide-react';
import { useTranslation } from 'react-i18next';

interface PlatformConfig {
  type: PlatformType;
  name: string;
  icon: React.ReactNode;
  color: string;
  description: string;
}

const PLATFORM_CONFIGS: PlatformConfig[] = [
  {
    type: 'youtube',
    name: 'YouTube',
    icon: <Youtube className="w-5 h-5" />,
    color: 'text-red-500',
    description: 'Stream to YouTube Live',
  },
  {
    type: 'twitch',
    name: 'Twitch',
    icon: <Twitch className="w-5 h-5" />,
    color: 'text-purple-500',
    description: 'Stream to Twitch',
  },
];

interface MultiPlatformSelectorProps {
  channelId: string;
  onSelect: (platform: StreamingPlatform) => void;
  onCancel: () => void;
  excludePlatformIds?: string[];
}

export const MultiPlatformSelector: React.FC<MultiPlatformSelectorProps> = ({
  channelId,
  onSelect,
  onCancel,
  excludePlatformIds = [],
}) => {
  const { t } = useTranslation();
  const [search, setSearch] = useState('');
  const [platformType, setPlatformType] = useState<PlatformType | 'all'>('all');

  const { data: platformsData, isLoading, error } = useQuery({
    queryKey: ['streaming', 'platforms'],
    queryFn: () => streamingPlatformsApi.listPlatforms(),
    staleTime: 30 * 1000, // 30 seconds
    retry: 1,
  });

  const platforms = platformsData?.platforms || [];

  // Filter out already added platforms and by search
  const filteredPlatforms = platforms.filter(
    (platform) =>
      !excludePlatformIds.includes(platform.id) &&
      (platformType === 'all' || platform.platform_type === platformType) &&
      (platform.platform_name.toLowerCase().includes(search.toLowerCase()) ||
        platform.platform_type.toLowerCase().includes(search.toLowerCase()))
  );

  const getPlatformConfig = (type: PlatformType): PlatformConfig | undefined => {
    return PLATFORM_CONFIGS.find((config) => config.type === type);
  };

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'active':
        return t('streaming.platformStatusActive', 'Активен');
      case 'inactive':
        return t('streaming.platformStatusInactive', 'Неактивен');
      case 'error':
        return t('streaming.platformStatusError', 'Ошибка');
      default:
        return status;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400';
      case 'inactive':
        return 'bg-gray-100 dark:bg-gray-900/30 text-gray-700 dark:text-gray-400';
      case 'error':
        return 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400';
      default:
        return 'bg-gray-100 dark:bg-gray-900/30 text-gray-700 dark:text-gray-400';
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row gap-3">
        {/* Search */}
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[color:var(--color-text-muted)]" />
          <input
            type="text"
            placeholder={t('streaming.searchPlaceholder', 'Поиск по названию...')}
            className="w-full pl-9 pr-3 py-2 border border-[color:var(--color-border)] bg-[color:var(--color-surface)] text-[color:var(--color-text)] rounded-lg text-sm"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        {/* Filter by platform type */}
        <select
          title={t('streaming.filterPlatform', 'Платформа')}
          className="px-3 py-2 border border-[color:var(--color-border)] bg-[color:var(--color-surface)] text-[color:var(--color-text)] rounded-lg text-sm"
          value={platformType}
          onChange={(e) => setPlatformType(e.target.value as PlatformType | 'all')}
        >
          <option value="all">{t('streaming.filterAll', 'Все платформы')}</option>
          {PLATFORM_CONFIGS.map((config) => (
            <option key={config.type} value={config.type}>
              {config.name}
            </option>
          ))}
        </select>
      </div>

      {/* Platform list */}
      <div className="max-h-[300px] overflow-y-auto border border-[color:var(--color-border)] rounded-lg">
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-6 h-6 animate-spin text-[color:var(--color-accent)]" />
            <span className="ml-2 text-[color:var(--color-text-muted)]">
              {t('streaming.loadingPlatforms', 'Загрузка платформ...')}
            </span>
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center py-8 px-4 text-center">
            <AlertCircle className="w-8 h-8 text-red-500 mb-2" />
            <p className="text-red-500 text-sm">
              {t('streaming.errorLoading', 'Не удалось загрузить платформы')}
            </p>
            <p className="text-xs text-[color:var(--color-text-muted)] mt-1">
              {(error as Error).message}
            </p>
          </div>
        ) : filteredPlatforms.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-[color:var(--color-text-muted)]">
            <Plus className="w-8 h-8 mb-2" />
            <p className="text-sm font-medium">
              {search || platformType !== 'all'
                ? t('streaming.noResults', 'Ничего не найдено')
                : t('streaming.noPlatforms', 'Нет доступных платформ')}
            </p>
            <div className="mt-3 p-3 bg-[color:var(--color-surface-muted)] rounded-lg text-xs max-w-xs text-center">
              <p className="font-medium text-[color:var(--color-text)] mb-1">
                {t('streaming.noPlatformsHint', '💡 Нет платформ?')}
              </p>
              <p>
                {t(
                  'streaming.noPlatformsInstruction',
                  'Сначала добавьте платформу трансляции в настройках.'
                )}
              </p>
            </div>
          </div>
        ) : (
          <div className="divide-y divide-[color:var(--color-border)]">
            {filteredPlatforms.map((platform) => {
              const config = getPlatformConfig(platform.platform_type);
              return (
                <button
                  key={platform.id}
                  onClick={() => onSelect(platform)}
                  className="w-full flex items-center gap-3 p-3 hover:bg-[color:var(--color-surface-muted)] transition-colors text-left group"
                >
                  {/* Platform icon */}
                  <div className="flex-shrink-0 w-10 h-10 rounded-full bg-[color:var(--color-surface-muted)] flex items-center justify-center">
                    {config ? (
                      <span className={config.color}>{config.icon}</span>
                    ) : (
                      <Plus className="w-5 h-5 text-[color:var(--color-text-muted)]" />
                    )}
                  </div>

                  {/* Platform info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-[color:var(--color-text)] truncate">
                        {platform.platform_name}
                      </span>
                      <span
                        className={`flex-shrink-0 px-1.5 py-0.5 text-xs rounded ${getStatusColor(
                          platform.status
                        )}`}
                      >
                        {getStatusLabel(platform.status)}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 text-xs text-[color:var(--color-text-muted)]">
                      <span>{config?.name || platform.platform_type}</span>
                      {config?.description && (
                        <>
                          <span>•</span>
                          <span>{config.description}</span>
                        </>
                      )}
                    </div>
                    <div className="text-xs text-[color:var(--color-text-muted)] font-mono mt-0.5">
                      ID: {platform.id}
                    </div>
                  </div>

                  {/* Selection icon */}
                  <Check className="w-5 h-5 text-[color:var(--color-accent)] opacity-0 group-hover:opacity-100 transition-opacity" />
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* Buttons */}
      <div className="flex justify-end gap-3">
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 text-[color:var(--color-text-muted)] hover:bg-[color:var(--color-surface-muted)] rounded-lg transition-colors"
        >
          {t('common.cancel', 'Отмена')}
        </button>
      </div>
    </div>
  );
};

export default MultiPlatformSelector;
