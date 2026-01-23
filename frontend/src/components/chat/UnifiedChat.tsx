import React, { useState, useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import {
  MessageCircle,
  RefreshCw,
  XCircle,
  Clock,
  Send,
  Trash2,
  Search,
  Filter,
  X,
  Youtube,
  Gamepad2,
  Video,
  Hash,
  LucideIcon,
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { format, formatDistanceToNow, parseISO } from 'date-fns';
import { ru, enUS } from 'date-fns/locale';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { chatApi } from '../../api/chat';
import { streamingPlatformsApi, type PlatformType } from '../../api/streaming_platforms';
import type { ChatMessage } from '../../api/chat';

interface PlatformInfo {
  id: string;
  platform_type: PlatformType;
  platform_name: string;
}

interface UnifiedChatProps {
  channelId?: string;
  autoRefresh?: boolean;
  refreshInterval?: number;
  maxMessages?: number;
}

const platformConfig: Record<PlatformType, { icon: LucideIcon; color: string; bgColor: string; label: string; labelRu: string }> = {
  youtube: {
    icon: Youtube,
    color: 'text-red-500',
    bgColor: 'bg-red-500/10',
    label: 'YouTube',
    labelRu: 'YouTube',
  },
  twitch: {
    icon: Gamepad2,
    color: 'text-purple-500',
    bgColor: 'bg-purple-500/10',
    label: 'Twitch',
    labelRu: 'Twitch',
  },
  twitter: {
    icon: Hash,
    color: 'text-sky-500',
    bgColor: 'bg-sky-500/10',
    label: 'Twitter',
    labelRu: 'Twitter',
  },
  discord: {
    icon: Video,
    color: 'text-indigo-500',
    bgColor: 'bg-indigo-500/10',
    label: 'Discord',
    labelRu: 'Discord',
  },
  custom_rtmp: {
    icon: Video,
    color: 'text-gray-500',
    bgColor: 'bg-gray-500/10',
    label: 'Custom RTMP',
    labelRu: 'Custom RTMP',
  },
};

const SkeletonMessage: React.FC = () => (
  <div className="flex gap-3 animate-pulse">
    <div className="w-8 h-8 rounded-full bg-gray-200 dark:bg-gray-700 flex-shrink-0" />
    <div className="flex-1 space-y-2">
      <div className="h-4 w-1/4 bg-gray-200 dark:bg-gray-700 rounded" />
      <div className="h-3 w-3/4 bg-gray-200 dark:bg-gray-700 rounded" />
      <div className="h-3 w-1/2 bg-gray-200 dark:bg-gray-700 rounded" />
    </div>
  </div>
);

export const UnifiedChat: React.FC<UnifiedChatProps> = ({
  channelId,
  autoRefresh = true,
  refreshInterval = 10000,
  maxMessages = 50,
}) => {
  const { t, i18n } = useTranslation();
  const locale = i18n.language === 'ru' ? ru : enUS;
  const queryClient = useQueryClient();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const [platformFilter, setPlatformFilter] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [searchInput, setSearchInput] = useState<string>('');
  const [showFilters, setShowFilters] = useState<boolean>(false);
  const [wsConnected, setWsConnected] = useState<boolean>(false);

  // Fetch aggregated chat messages
  const {
    data: aggregatedData,
    isLoading,
    isError,
    error,
    refetch,
    isFetching,
  } = useQuery({
    queryKey: ['chat', 'aggregated', channelId, platformFilter || 'all'],
    queryFn: async () => {
      if (channelId) {
        return await chatApi.getAggregatedMessages({
          channel_id: channelId,
          limit: maxMessages,
        });
      }
      return await chatApi.getAggregatedMessages({
        limit: maxMessages,
      });
    },
    refetchInterval: autoRefresh ? refreshInterval : false,
    enabled: true,
  });

  // Fetch platform info for badges
  const { data: platformsData } = useQuery({
    queryKey: ['streaming-platforms'],
    queryFn: streamingPlatformsApi.listPlatforms,
    enabled: true,
  });

  const platformsMap = React.useMemo<Record<string, PlatformInfo>>(() => {
    if (!platformsData?.platforms) return {};
    return platformsData.platforms.reduce((acc, platform) => {
      acc[platform.id] = {
        id: platform.id,
        platform_type: platform.platform_type,
        platform_name: platform.platform_name,
      };
      return acc;
    }, {} as Record<string, PlatformInfo>);
  }, [platformsData]);

  // Delete message mutation
  const deleteMutation = useMutation({
    mutationFn: chatApi.deleteMessage,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chat', 'aggregated'] });
    },
  });

  // WebSocket connection for real-time updates
  useEffect(() => {
    const wsUrl = `${import.meta.env.VITE_API_URL?.replace('http', 'ws') || 'ws://localhost:8000'}/api/chat/ws`;

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setWsConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'chat_message' || data.type === 'chat_messages_batch') {
            queryClient.invalidateQueries({ queryKey: ['chat', 'aggregated'] });
          }
        } catch (e) {
          // Ignore JSON parse errors
        }
      };

      ws.onerror = () => {
        setWsConnected(false);
      };

      ws.onclose = () => {
        setWsConnected(false);
      };

      return () => {
        ws.close();
      };
    } catch (e) {
      setWsConnected(false);
    }
  }, [queryClient]);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [aggregatedData]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSearchQuery(searchInput);
  };

  const clearFilters = () => {
    setPlatformFilter('');
    setSearchQuery('');
    setSearchInput('');
  };

  const hasActiveFilters = platformFilter || searchQuery;

  // Filter messages
  const filteredMessages = React.useMemo(() => {
    if (!aggregatedData) return [];

    let messages = aggregatedData.messages || [];

    // Filter by platform
    if (platformFilter) {
      messages = messages.filter((msg) => msg.platform_id === platformFilter);
    }

    // Filter by search query
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      messages = messages.filter((msg) =>
        msg.content.toLowerCase().includes(query) ||
        msg.author_name.toLowerCase().includes(query) ||
        (msg.author_display_name && msg.author_display_name.toLowerCase().includes(query))
      );
    }

    return messages;
  }, [aggregatedData, platformFilter, searchQuery]);

  // Get platform info for a message
  const getPlatformInfo = (platformId: string): PlatformInfo | undefined => {
    return platformsMap[platformId];
  };

  // Error state
  if (isError) {
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <MessageCircle className="w-5 h-5 text-violet-500" />
          <h3 className="text-lg font-semibold text-[color:var(--color-text)]">
            {t('chat.unified.title', 'Объединенный чат')}
          </h3>
        </div>
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-rose-600 dark:text-rose-400">
              <XCircle className="w-5 h-5" />
              <span className="text-sm font-medium">
                {t('chat.unified.error', 'Не удалось загрузить сообщения')}
              </span>
            </div>
            <button
              onClick={() => refetch()}
              disabled={isFetching}
              className="p-2 rounded-lg hover:bg-rose-500/10 transition-colors"
            >
              <RefreshCw className={`w-4 h-4 text-rose-500 ${isFetching ? 'animate-spin' : ''}`} />
            </button>
          </div>
          <p className="mt-2 text-xs text-[color:var(--color-text-muted)]">
            {error instanceof Error ? error.message : t('chat.unified.tryAgain', 'Попробуйте обновить страницу')}
          </p>
        </div>
      </div>
    );
  }

  // Loading state
  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <MessageCircle className="w-5 h-5 text-violet-500" />
          <h3 className="text-lg font-semibold text-[color:var(--color-text)]">
            {t('chat.unified.title', 'Объединенный чат')}
          </h3>
        </div>
        <div className="space-y-4 p-4 rounded-xl bg-[color:var(--color-panel)] border border-[color:var(--color-border)]">
          {[1, 2, 3, 4, 5].map((i) => (
            <SkeletonMessage key={i} />
          ))}
        </div>
      </div>
    );
  }

  // Empty state
  if (!aggregatedData || filteredMessages.length === 0) {
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <MessageCircle className="w-5 h-5 text-violet-500" />
          <h3 className="text-lg font-semibold text-[color:var(--color-text)]">
            {t('chat.unified.title', 'Объединенный чат')}
          </h3>
        </div>
        <div className="p-8 rounded-xl bg-[color:var(--color-panel)] border border-[color:var(--color-border)] text-center space-y-3">
          <Clock className="w-12 h-12 mx-auto text-[color:var(--color-text-muted)]" />
          <div className="space-y-1">
            <p className="text-[color:var(--color-text)] font-medium">
              {t('chat.unified.noMessages', 'Нет сообщений')}
            </p>
            <p className="text-sm text-[color:var(--color-text-muted)]">
              {hasActiveFilters
                ? t('chat.unified.noFilteredMessages', 'Нет сообщений, соответствующих фильтрам')
                : t('chat.unified.noMessagesHint', 'Сообщения из всех платформ появятся здесь')}
            </p>
          </div>
          {hasActiveFilters && (
            <button
              onClick={clearFilters}
              className="px-3 py-2 text-sm font-medium rounded-lg bg-violet-500 text-white hover:bg-violet-600 transition-colors"
            >
              {t('chat.unified.clearFilters', 'Очистить фильтры')}
            </button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4 max-w-4xl">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <MessageCircle className="w-5 h-5 text-violet-500" />
          <h3 className="text-lg font-semibold text-[color:var(--color-text)]">
            {t('chat.unified.title', 'Объединенный чат')}
          </h3>
          {wsConnected && (
            <span className="flex h-2 w-2 relative">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {hasActiveFilters && (
            <button
              onClick={clearFilters}
              className="flex items-center gap-1 px-2 py-1 text-xs text-rose-600 dark:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-900/20 rounded-lg transition-colors"
            >
              <X className="w-3 h-3" />
              {t('chat.unified.clearFilters', 'Сбросить')}
            </button>
          )}
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`p-2 rounded-lg transition-colors ${
              showFilters || hasActiveFilters
                ? 'bg-violet-100 dark:bg-violet-900/30 text-violet-600 dark:text-violet-400'
                : 'hover:bg-[color:var(--color-surface-muted)]'
            }`}
            title={t('chat.unified.filters', 'Фильтры')}
          >
            <Filter className="w-4 h-4" />
          </button>
          <button
            onClick={() => refetch()}
            disabled={isFetching}
            className="p-2 rounded-lg hover:bg-[color:var(--color-surface-muted)] transition-colors"
            title={t('chat.unified.refresh', 'Обновить')}
          >
            <RefreshCw className={`w-4 h-4 ${isFetching ? 'animate-spin' : ''}`} />
          </button>
          <span className="text-xs text-[color:var(--color-text-muted)] px-2 py-1 rounded-full bg-[color:var(--color-surface-muted)]">
            {filteredMessages.length} {t('chat.unified.messages', 'сообщений')}
          </span>
        </div>
      </div>

      {/* Filters */}
      {showFilters && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          exit={{ opacity: 0, height: 0 }}
          className="flex flex-col sm:flex-row gap-3 p-3 rounded-xl bg-[color:var(--color-surface-muted)] border border-[color:var(--color-border)]"
        >
          {/* Platform filter */}
          <div className="flex-1">
            <label className="block text-xs text-[color:var(--color-text-muted)] mb-1">
              {t('chat.unified.filterByPlatform', 'Платформа')}
            </label>
            <select
              value={platformFilter}
              onChange={(e) => setPlatformFilter(e.target.value)}
              className="w-full px-3 py-2 text-sm rounded-lg border border-[color:var(--color-border)] bg-[color:var(--color-panel)] text-[color:var(--color-text)] focus:outline-none focus:ring-2 focus:ring-violet-500/50"
            >
              <option value="">{t('chat.unified.allPlatforms', 'Все платформы')}</option>
              {Object.values(platformsMap).map((platform) => {
                const config = platformConfig[platform.platform_type];
                return (
                  <option key={platform.id} value={platform.id}>
                    {i18n.language === 'ru' ? config.labelRu : config.label} - {platform.platform_name}
                  </option>
                );
              })}
            </select>
          </div>

          {/* Search */}
          <div className="flex-1">
            <label className="block text-xs text-[color:var(--color-text-muted)] mb-1">
              {t('chat.unified.search', 'Поиск')}
            </label>
            <form onSubmit={handleSearchSubmit} className="flex gap-2">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[color:var(--color-text-muted)]" />
                <input
                  type="text"
                  value={searchInput}
                  onChange={(e) => setSearchInput(e.target.value)}
                  placeholder={t('chat.unified.searchPlaceholder', 'Поиск по сообщениям...')}
                  className="w-full pl-9 pr-3 py-2 text-sm rounded-lg border border-[color:var(--color-border)] bg-[color:var(--color-panel)] text-[color:var(--color-text)] placeholder:text-[color:var(--color-text-muted)] focus:outline-none focus:ring-2 focus:ring-violet-500/50"
                />
              </div>
              <button
                type="submit"
                className="px-3 py-2 text-sm font-medium text-white bg-violet-500 hover:bg-violet-600 rounded-lg transition-colors"
              >
                {t('chat.unified.searchBtn', 'Найти')}
              </button>
            </form>
          </div>
        </motion.div>
      )}

      {/* Messages */}
      <div className="relative rounded-xl bg-[color:var(--color-panel)] border border-[color:var(--color-border)] overflow-hidden">
        <div className="divide-y divide-[color:var(--color-border)] max-h-[600px] overflow-y-auto">
          {filteredMessages.map((message, index) => {
            const platformInfo = getPlatformInfo(message.platform_id);
            const platformConfigData = platformInfo
              ? platformConfig[platformInfo.platform_type]
              : null;
            const PlatformIcon = platformConfigData?.icon || MessageCircle;

            const timestamp = parseISO(message.message_timestamp);

            return (
              <motion.div
                key={message.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: Math.min(index * 0.02, 0.5) }}
                className="relative flex gap-3 p-4 hover:bg-[color:var(--color-surface-muted)]/50 transition-colors group"
              >
                {/* Avatar */}
                <div className="relative z-10 flex-shrink-0">
                  <div
                    className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-semibold text-white"
                    style={{
                      backgroundColor: message.author_color || '#8b5cf6',
                    }}
                  >
                    {message.author_display_name?.[0] || message.author_name[0]}
                  </div>
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0 space-y-1">
                  {/* Header: Author + Platform + Time */}
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-sm font-medium text-[color:var(--color-text)]">
                      {message.author_display_name || message.author_name}
                    </span>

                    {/* Platform badge */}
                    {platformConfigData && (
                      <span
                        className={`inline-flex items-center gap-1 px-2 py-0.5 text-[10px] font-medium rounded-full ${platformConfigData.bgColor} ${platformConfigData.color}`}
                      >
                        <PlatformIcon className="w-3 h-3" />
                        {i18n.language === 'ru' ? platformConfigData.labelRu : platformConfigData.label}
                      </span>
                    )}

                    <span className="text-[10px] text-[color:var(--color-text-muted)] uppercase tracking-wide">
                      {formatDistanceToNow(timestamp, { addSuffix: true, locale })}
                    </span>
                  </div>

                  {/* Message content */}
                  <p className="text-sm text-[color:var(--color-text)] break-words whitespace-pre-wrap">
                    {message.content}
                  </p>
                </div>

                {/* Delete button (on hover) */}
                <button
                  onClick={() => deleteMutation.mutate(message.id)}
                  className="opacity-0 group-hover:opacity-100 p-2 rounded-lg hover:bg-rose-500/10 text-rose-500 transition-all"
                  title={t('chat.unified.deleteMessage', 'Удалить сообщение')}
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </motion.div>
            );
          })}
        </div>

        <div ref={messagesEndRef} />
      </div>

      {/* Load more indicator if we have more messages */}
      {aggregatedData.total > maxMessages && (
        <div className="p-3 text-center border-t border-[color:var(--color-border)]">
          <span className="text-xs text-[color:var(--color-text-muted)]">
            {t('chat.unified.showingRecent', 'Показаны последние {count} из {total} сообщений', {
              count: filteredMessages.length,
              total: aggregatedData.total,
            })}
          </span>
        </div>
      )}
    </div>
  );
};
