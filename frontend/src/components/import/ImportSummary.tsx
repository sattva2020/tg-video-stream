import React, { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { CheckCircle2, XCircle, AlertTriangle, Clock, Copy, RefreshCw } from 'lucide-react'
import type { ImportSummary as ImportSummaryType } from '../../types/import'
import * as importApi from '../../api/import'
import { useToast } from '../../hooks/useToast'
import { Skeleton } from '../ui/Skeleton'

interface ImportSummaryProps {
  /** ID of the import job to show summary for */
  jobId: string
  /** Callback when user wants to perform another import */
  onNewImport?: () => void
  /** Custom CSS class name */
  className?: string
}

/**
 * ImportSummary Component
 *
 * Displays the results of an import operation including:
 * - Total items processed
 * - Successfully imported items
 * - Duplicate items (skipped)
 * - Failed items with errors
 * - Import duration
 *
 * @example
 * const handleNewImport = () => {
 *   // Reset wizard state to start a new import
 *   setCurrentStep('platform')
 *   setSelectedPlatform(null)
 *   setJobId(null)
 * }
 *
 * <ImportSummary
 *   jobId="import-123"
 *   onNewImport={handleNewImport}
 * />
 */
const ImportSummary: React.FC<ImportSummaryProps> = ({
  jobId,
  onNewImport,
  className = '',
}) => {
  const { t } = useTranslation()
  const [loading, setLoading] = useState(true)
  const [summary, setSummary] = useState<ImportSummaryType | null>(null)
  const toast = useToast()

  const fetchSummary = useCallback(async () => {
    try {
      const data = await importApi.importApi.getImportSummary(jobId)
      setSummary(data)
    } catch (e) {
      console.error('[ImportSummary] Failed to fetch import summary', e)
      toast.error(t('import.summaryFetchError', 'Не удалось загрузить сводку импорта'))
    } finally {
      setLoading(false)
    }
  }, [jobId, toast, t])

  useEffect(() => {
    fetchSummary()
  }, [fetchSummary])

  const handleRefresh = useCallback(() => {
    fetchSummary()
  }, [fetchSummary])

  if (loading) {
    return (
      <div className={`bg-[color:var(--color-panel)] shadow rounded-lg p-6 ${className}`}>
        <div className="space-y-4">
          <Skeleton className="h-6 w-48" />
          <div className="grid grid-cols-4 gap-4">
            <Skeleton className="h-24" />
            <Skeleton className="h-24" />
            <Skeleton className="h-24" />
            <Skeleton className="h-24" />
          </div>
          <Skeleton className="h-32 w-full" />
        </div>
      </div>
    )
  }

  if (!summary) {
    return (
      <div className={`bg-[color:var(--color-panel)] shadow rounded-lg p-6 ${className}`}>
        <p className="text-[color:var(--color-text-muted)]">
          {t('import.summaryNotAvailable', 'Сводка импорта недоступна')}
        </p>
      </div>
    )
  }

  const successRate =
    summary.total_items > 0
      ? Math.round((summary.imported_count / summary.total_items) * 100)
      : 0

  const formatDuration = (seconds?: number): string => {
    if (!seconds) return '-'
    if (seconds < 60) return `${seconds}s`
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    return `${hours}h ${minutes}m`
  }

  const platformIcons: Record<string, React.ReactNode> = {
    youtube: <Copy className="w-5 h-5 text-red-500" />,
    vimeo: <Copy className="w-5 h-5 text-cyan-500" />,
    local: <Copy className="w-5 h-5 text-green-500" />,
  }

  const platformLabels: Record<string, string> = {
    youtube: t('import.platform.youtube', 'YouTube'),
    vimeo: t('import.platform.vimeo', 'Vimeo'),
    local: t('import.platform.local', 'Локальные файлы'),
  }

  return (
    <div className={`bg-[color:var(--color-panel)] shadow rounded-lg p-6 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          {platformIcons[summary.platform]}
          <div>
            <h3 className="text-lg font-semibold text-[color:var(--color-text)]">
              {t('import.summaryTitle', 'Сводка импорта')}
            </h3>
            <p className="text-xs text-[color:var(--color-text-muted)]">
              {platformLabels[summary.platform]} • {new Date().toLocaleString()}
            </p>
          </div>
        </div>
        <button
          onClick={handleRefresh}
          className="text-[color:var(--color-text-muted)] hover:text-[color:var(--color-text)] transition-colors"
          title={t('common.refresh', 'Обновить')}
        >
          <RefreshCw className="w-5 h-5" />
        </button>
      </div>

      {/* Success Rate Banner */}
      {summary.status === 'completed' && (
        <div className="mb-6 p-4 bg-green-500/10 border border-green-500/30 rounded-lg">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-5 h-5 text-green-500" />
            <div className="flex-1">
              <p className="text-sm font-medium text-green-400">
                {t('import.completed', 'Импорт завершён')}
              </p>
              <p className="text-xs text-[color:var(--color-text-muted)]">
                {t('import.successRate', 'Успешность')}: {successRate}%
              </p>
            </div>
          </div>
        </div>
      )}

      {summary.status === 'failed' && (
        <div className="mb-6 p-4 bg-red-500/10 border border-red-500/30 rounded-lg">
          <div className="flex items-center gap-2">
            <XCircle className="w-5 h-5 text-red-500" />
            <div className="flex-1">
              <p className="text-sm font-medium text-red-400">
                {t('import.failed', 'Импорт завершён с ошибками')}
              </p>
              <p className="text-xs text-[color:var(--color-text-muted)]">
                {t('import.someItemsFailed', 'Некоторые элементы не были импортированы')}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Statistics Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {/* Total Items */}
        <div className="bg-[color:var(--color-surface-muted)] rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <Copy className="w-4 h-4 text-[color:var(--color-text-muted)]" />
            <span className="text-xs text-[color:var(--color-text-muted)]">
              {t('import.totalItems', 'Всего элементов')}
            </span>
          </div>
          <div className="text-2xl font-bold text-[color:var(--color-text)]">
            {summary.total_items}
          </div>
        </div>

        {/* Imported */}
        <div className="bg-[color:var(--color-surface-muted)] rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <CheckCircle2 className="w-4 h-4 text-green-500" />
            <span className="text-xs text-[color:var(--color-text-muted)]">
              {t('import.imported', 'Импортировано')}
            </span>
          </div>
          <div className="text-2xl font-bold text-green-500">
            {summary.imported_count}
          </div>
        </div>

        {/* Duplicates */}
        <div className="bg-[color:var(--color-surface-muted)] rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <Copy className="w-4 h-4 text-yellow-500" />
            <span className="text-xs text-[color:var(--color-text-muted)]">
              {t('import.duplicates', 'Дубликатов')}
            </span>
          </div>
          <div className="text-2xl font-bold text-yellow-500">
            {summary.duplicate_count}
          </div>
        </div>

        {/* Failed */}
        <div className="bg-[color:var(--color-surface-muted)] rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <XCircle className="w-4 h-4 text-red-500" />
            <span className="text-xs text-[color:var(--color-text-muted)]">
              {t('import.failedItems', 'Ошибок')}
            </span>
          </div>
          <div className="text-2xl font-bold text-red-500">
            {summary.failed_count}
          </div>
        </div>
      </div>

      {/* Duration */}
      {summary.duration_seconds && summary.duration_seconds > 0 && (
        <div className="flex items-center gap-2 mb-6 p-3 bg-[color:var(--color-surface-muted)] rounded-lg">
          <Clock className="w-4 h-4 text-[color:var(--color-text-muted)]" />
          <span className="text-sm text-[color:var(--color-text-muted)]">
            {t('import.duration', 'Время выполнения')}: {formatDuration(summary.duration_seconds)}
          </span>
        </div>
      )}

      {/* Errors Section */}
      {summary.errors && summary.errors.length > 0 && (
        <div className="mb-6">
          <h4 className="text-sm font-semibold text-[color:var(--color-text)] mb-3 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-red-500" />
            {t('import.errors', 'Ошибки')} ({summary.errors.length})
          </h4>
          <div className="bg-red-500/5 border border-red-500/20 rounded-lg p-3 max-h-48 overflow-y-auto">
            <ul className="space-y-2">
              {summary.errors.map((error, index) => (
                <li key={index} className="text-sm text-red-400 flex items-start gap-2">
                  <span className="text-red-500 mt-0.5">•</span>
                  <span>{error}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center gap-3 justify-end">
        {onNewImport && (
          <button
            onClick={onNewImport}
            className="flex items-center gap-2 px-4 py-2 bg-[color:var(--color-accent)] text-white rounded-lg text-sm font-medium hover:opacity-90 transition-opacity"
          >
            <Copy className="w-4 h-4" />
            {t('import.newImport', 'Новый импорт')}
          </button>
        )}
      </div>
    </div>
  )
}

export default ImportSummary
