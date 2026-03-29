import React, { useState, useCallback, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import {
  RefreshCw,
  Filter,
  Trash2,
  Loader2,
  Search,
  ChevronDown,
  Info
} from 'lucide-react'
import { useToast } from '../hooks/useToast'
import * as playlistService from '../services/playlist'
import type { PlaylistItem } from '../services/playlist'
import { videoSourcesApi } from '../api/video_sources'
import SourceCard from './SourceCard'
import type { SourceType } from '../types/video_sources'

interface SourceManagerProps {
  channelId?: string
  autoRefresh?: boolean
  refreshInterval?: number
}

type FilterStatus = 'all' | 'playing' | 'queued' | 'error' | 'completed'
type FilterType = 'all' | SourceType

const SourceManager: React.FC<SourceManagerProps> = ({
  channelId,
  autoRefresh = true,
  refreshInterval = 5000,
}) => {
  const { t } = useTranslation()
  const toast = useToast()

  const [sources, setSources] = useState<PlaylistItem[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [deletingIds, setDeletingIds] = useState<Set<string>>(new Set())

  // Filters
  const [statusFilter, setStatusFilter] = useState<FilterStatus>('all')
  const [typeFilter, setTypeFilter] = useState<FilterType>('all')
  const [searchQuery, setSearchQuery] = useState('')
  const [showFilters, setShowFilters] = useState(true)

  // Available source types for filtering
  const sourceTypes: (FilterType | { key: FilterType; label: string })[] = [
    'all',
    { key: 'youtube' as SourceType, label: 'YouTube' },
    { key: 'vimeo' as SourceType, label: 'Vimeo' },
    { key: 'dailymotion' as SourceType, label: 'Dailymotion' },
    { key: 'twitch' as SourceType, label: 'Twitch' },
    { key: 'direct' as SourceType, label: 'Direct URL' },
    { key: 'hls' as SourceType, label: 'HLS' },
    { key: 'dash' as SourceType, label: 'DASH' },
    { key: 'google_drive' as SourceType, label: 'Google Drive' },
    { key: 'dropbox' as SourceType, label: 'Dropbox' },
    { key: 'onedrive' as SourceType, label: 'OneDrive' },
    { key: 'rss_feed' as SourceType, label: 'RSS Feed' },
  ]

  const fetchSources = useCallback(async () => {
    try {
      setRefreshing(true)
      const data = await playlistService.getPlaylist(channelId)
      setSources(data)
    } catch (err) {
      console.error('Failed to fetch sources', err)
      toast.error(t('sources.fetchError', 'Не удалось загрузить источники'))
    } finally {
      setRefreshing(false)
      setLoading(false)
    }
  }, [channelId, toast, t])

  useEffect(() => {
    fetchSources()

    if (autoRefresh) {
      const interval = setInterval(fetchSources, refreshInterval)
      return () => clearInterval(interval)
    }
  }, [fetchSources, autoRefresh, refreshInterval])

  const handleDelete = useCallback(async (id: string) => {
    setDeletingIds((prev) => new Set(prev).add(id))

    try {
      await playlistService.deletePlaylistItem(id)
      setSources((prev) => prev.filter((s) => s.id !== id))
      toast.success(t('sources.deleted', 'Источник удалён'))
    } catch (err) {
      console.error('Failed to delete source', err)
      toast.error(t('sources.deleteError', 'Не удалось удалить источник'))
    } finally {
      setDeletingIds((prev) => {
        const next = new Set(prev)
        next.delete(id)
        return next
      })
    }
  }, [toast, t])

  const handleDeleteAll = useCallback(async () => {
    if (sources.length === 0) return

    if (!confirm(t('sources.confirmDeleteAll', 'Удалить все источники?'))) {
      return
    }

    setDeletingIds(new Set(sources.map((s) => s.id)))

    try {
      await Promise.all(sources.map((s) => playlistService.deletePlaylistItem(s.id)))
      setSources([])
      toast.success(t('sources.allDeleted', 'Все источники удалены'))
    } catch (err) {
      console.error('Failed to delete all sources', err)
      toast.error(t('sources.deleteAllError', 'Не удалось удалить все источники'))
      fetchSources()
    } finally {
      setDeletingIds(new Set())
    }
  }, [sources, toast, t, fetchSources])

  // Filter sources
  const filteredSources = sources.filter((source) => {
    // Status filter
    if (statusFilter !== 'all' && source.status !== statusFilter) {
      return false
    }

    // Type filter
    if (typeFilter !== 'all' && source.type !== typeFilter) {
      return false
    }

    // Search query
    if (searchQuery) {
      const query = searchQuery.toLowerCase()
      return (
        (source.title && source.title.toLowerCase().includes(query)) ||
        source.url.toLowerCase().includes(query)
      )
    }

    return true
  })

  // Get source type label
  const getTypeLabel = (type: FilterType): string => {
    if (type === 'all') return t('sources.allTypes', 'Все типы')
    return sourceTypes.find((st) => typeof st === 'object' && st.key === type)?.label || type
  }

  return (
    <div className="bg-[color:var(--color-panel)] border border-[color:var(--color-outline)] rounded-xl p-4 sm:p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-[color:var(--color-text)]">
            {t('sources.title', 'Источники видео')}
          </h3>
          <p className="text-sm text-[color:var(--color-text-muted)] mt-0.5">
            {t('sources.count', '{count} источников', { count: sources.length })}
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* Delete All Button */}
          {sources.length > 0 && (
            <button
              onClick={handleDeleteAll}
              disabled={loading || deletingIds.size > 0}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg border border-red-500/30 text-red-500 hover:bg-red-500/10 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              title={t('sources.deleteAll', 'Удалить все')}
            >
              <Trash2 className="w-4 h-4" />
              <span className="hidden sm:inline">{t('sources.clearAll', 'Очистить всё')}</span>
            </button>
          )}

          {/* Refresh Button */}
          <button
            onClick={fetchSources}
            disabled={refreshing}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg border border-[color:var(--color-outline)] text-[color:var(--color-text)] hover:bg-[color:var(--color-surface-muted)] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            title={t('sources.refresh', 'Обновить')}
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
            <span className="hidden sm:inline">{t('sources.refresh', 'Обновить')}</span>
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="mb-4">
        <button
          onClick={() => setShowFilters(!showFilters)}
          className="flex items-center gap-2 text-sm text-[color:var(--color-text-muted)] hover:text-[color:var(--color-text)] transition-colors mb-3"
        >
          <Filter className="w-4 h-4" />
          {t('sources.filters', 'Фильтры')}
          <ChevronDown className={`w-4 h-4 transition-transform ${showFilters ? 'rotate-180' : ''}`} />
        </button>

        {showFilters && (
          <div className="space-y-3 p-4 bg-[color:var(--color-surface)] rounded-lg border border-[color:var(--color-outline)]">
            {/* Search */}
            <div>
              <label className="block text-sm font-medium text-[color:var(--color-text-muted)] mb-1.5">
                {t('sources.search', 'Поиск')}
              </label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[color:var(--color-text-muted)]" />
                <input
                  type="text"
                  placeholder={t('sources.searchPlaceholder', 'Название или URL...')}
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 rounded-lg border border-[color:var(--color-outline)] bg-[color:var(--color-panel)] text-[color:var(--color-text)] placeholder-[color:var(--color-text-muted)] focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {/* Status Filter */}
              <div>
                <label className="block text-sm font-medium text-[color:var(--color-text-muted)] mb-1.5">
                  {t('sources.statusFilter', 'Статус')}
                </label>
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value as FilterStatus)}
                  className="w-full px-3 py-2 rounded-lg border border-[color:var(--color-outline)] bg-[color:var(--color-panel)] text-[color:var(--color-text)] focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                >
                  <option value="all">{t('sources.allStatuses', 'Все статусы')}</option>
                  <option value="playing">{t('sources.status.playing', 'Воспроизводится')}</option>
                  <option value="queued">{t('sources.status.queued', 'В очереди')}</option>
                  <option value="error">{t('sources.status.error', 'Ошибка')}</option>
                  <option value="completed">{t('sources.status.completed', 'Завершён')}</option>
                </select>
              </div>

              {/* Type Filter */}
              <div>
                <label className="block text-sm font-medium text-[color:var(--color-text-muted)] mb-1.5">
                  {t('sources.typeFilter', 'Тип источника')}
                </label>
                <select
                  value={typeFilter}
                  onChange={(e) => setTypeFilter(e.target.value as FilterType)}
                  className="w-full px-3 py-2 rounded-lg border border-[color:var(--color-outline)] bg-[color:var(--color-panel)] text-[color:var(--color-text)] focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                >
                  {sourceTypes.map((st) => {
                    const key = typeof st === 'string' ? st : st.key
                    const label = typeof st === 'string' ? getTypeLabel(key) : st.label
                    return (
                      <option key={key} value={key}>
                        {label}
                      </option>
                    )
                  })}
                </select>
              </div>
            </div>

            {/* Filter Summary */}
            {(statusFilter !== 'all' || typeFilter !== 'all' || searchQuery) && (
              <div className="flex items-center justify-between pt-2 border-t border-[color:var(--color-outline)]">
                <span className="text-sm text-[color:var(--color-text-muted)]">
                  {t('sources.showing', 'Показано: {count} из {total}', {
                    count: filteredSources.length,
                    total: sources.length,
                  })}
                </span>
                <button
                  onClick={() => {
                    setStatusFilter('all')
                    setTypeFilter('all')
                    setSearchQuery('')
                  }}
                  className="text-sm text-orange-500 hover:text-orange-600 transition-colors"
                >
                  {t('sources.clearFilters', 'Сбросить фильтры')}
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Sources List */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-[color:var(--color-text-muted)]" />
        </div>
      ) : filteredSources.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <Info className="w-12 h-12 text-[color:var(--color-text-muted)] mb-3" />
          <p className="text-[color:var(--color-text-muted)]">
            {sources.length === 0
              ? t('sources.empty', 'Нет добавленных источников')
              : t('sources.noResults', 'Нет источников, соответствующих фильтрам')}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {filteredSources.map((source) => (
            <SourceCard
              key={source.id}
              id={source.id}
              url={source.url}
              title={source.title}
              type={source.type as SourceType}
              status={source.status as 'playing' | 'queued' | 'error' | 'completed'}
              duration={source.duration}
              position={source.position}
              created_at={source.created_at}
              onDelete={handleDelete}
              deleting={deletingIds.has(source.id)}
            />
          ))}
        </div>
      )}
    </div>
  )
}

export default SourceManager
