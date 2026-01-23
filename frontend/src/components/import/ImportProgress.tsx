import React, { useCallback, useEffect, useState, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { Pause, Play, X, RefreshCw } from 'lucide-react'
import type { ImportJob, ImportStatus } from '../../types/import'
import * as importApi from '../../api/import'
import { useToast } from '../../hooks/useToast'
import { Skeleton } from '../ui/Skeleton'

export const POLL_INTERVAL_MS = 3000
const MAX_CONSECUTIVE_ERRORS = 3
const MAX_BACKOFF_MS = 60000 // Max 1 minute between retries

interface ImportProgressProps {
  /** ID of the import job to track */
  jobId: string
  /** Callback when import is completed */
  onComplete?: (job: ImportJob) => void
  /** Callback when import is cancelled */
  onCancel?: () => void
  /** Custom CSS class name */
  className?: string
}

const ImportProgress: React.FC<ImportProgressProps> = ({
  jobId,
  onComplete,
  onCancel,
  className = '',
}) => {
  const { t } = useTranslation()
  const [loading, setLoading] = useState(true)
  const [updating, setUpdating] = useState(false)
  const toast = useToast()

  const [job, setJob] = useState<ImportJob | null>(null)
  const errorCountRef = useRef(0)
  const backoffRef = useRef(POLL_INTERVAL_MS)

  const fetchJob = useCallback(async () => {
    try {
      const data = await importApi.importApi.getImportJob(jobId)
      setJob(data)

      // Reset error state on success
      errorCountRef.current = 0
      backoffRef.current = POLL_INTERVAL_MS

      // Trigger callbacks based on status
      if (data.status === 'completed') {
        onComplete?.(data)
      } else if (data.status === 'cancelled') {
        onCancel?.()
      }
    } catch (e) {
      console.error('[ImportProgress] Failed to fetch import job', e)
      errorCountRef.current++
      // Exponential backoff: 3s -> 6s -> 12s -> 24s -> 48s -> 60s max
      backoffRef.current = Math.min(backoffRef.current * 2, MAX_BACKOFF_MS)

      if (errorCountRef.current === 1) {
        toast.error(t('import.fetchError', 'Не удалось загрузить прогресс импорта'))
      }
    } finally {
      setLoading(false)
      setUpdating(false)
    }
  }, [jobId, onComplete, onCancel, toast, t])

  // Initial fetch and polling
  useEffect(() => {
    // Initial fetch
    fetchJob()

    // Setup polling with dynamic interval based on backoff
    let timeoutId: NodeJS.Timeout
    const scheduleNext = () => {
      // Stop polling if job is in terminal state
      if (job?.status === 'completed' || job?.status === 'failed' || job?.status === 'cancelled') {
        return
      }

      // Stop polling after too many consecutive errors
      if (errorCountRef.current >= MAX_CONSECUTIVE_ERRORS) {
        console.warn('[ImportProgress] Polling paused due to consecutive errors')
        return
      }

      timeoutId = setTimeout(() => {
        fetchJob().finally(() => {
          const shouldContinue =
            job?.status !== 'completed' &&
            job?.status !== 'failed' &&
            job?.status !== 'cancelled' &&
            errorCountRef.current < MAX_CONSECUTIVE_ERRORS

          if (shouldContinue) {
            scheduleNext()
          }
        })
      }, backoffRef.current)
    }
    scheduleNext()

    return () => clearTimeout(timeoutId)
  }, [fetchJob, job?.status])

  const handlePauseResume = useCallback(async () => {
    if (!job) return

    const newStatus: ImportStatus = job.status === 'paused' ? 'in_progress' : 'paused'
    setUpdating(true)

    try {
      const updated = await importApi.importApi.updateImportJob(jobId, { status: newStatus })
      setJob(updated)
      toast.success(
        newStatus === 'paused'
          ? t('import.paused', 'Импорт приостановлен')
          : t('import.resumed', 'Импорт возобновлён')
      )
    } catch (e) {
      console.error('[ImportProgress] Failed to update job status', e)
      toast.error(t('import.updateError', 'Не удалось изменить статус'))
      setUpdating(false)
    }
  }, [job, jobId, toast, t])

  const handleCancel = useCallback(async () => {
    if (!job) return

    setUpdating(true)

    try {
      await importApi.importApi.cancelImportJob(jobId)
      setJob({ ...job, status: 'cancelled' })
      toast.info(t('import.cancelled', 'Импорт отменён'))
      onCancel?.()
    } catch (e) {
      console.error('[ImportProgress] Failed to cancel job', e)
      toast.error(t('import.cancelError', 'Не удалось отменить импорт'))
      setUpdating(false)
    }
  }, [job, jobId, onCancel, toast, t])

  const handleRefresh = useCallback(() => {
    fetchJob()
  }, [fetchJob])

  if (loading) {
    return (
      <div className={`bg-[color:var(--color-panel)] shadow rounded-lg p-6 ${className}`}>
        <div className="space-y-4">
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-3/4" />
          <div className="grid grid-cols-4 gap-4 mt-4">
            <Skeleton className="h-16" />
            <Skeleton className="h-16" />
            <Skeleton className="h-16" />
            <Skeleton className="h-16" />
          </div>
        </div>
      </div>
    )
  }

  if (!job) {
    return (
      <div className={`bg-[color:var(--color-panel)] shadow rounded-lg p-6 ${className}`}>
        <p className="text-[color:var(--color-text-muted)]">
          {t('import.notFound', 'Задание импорта не найдено')}
        </p>
      </div>
    )
  }

  const statusColors: Record<ImportStatus, string> = {
    pending: 'text-yellow-500',
    in_progress: 'text-blue-500',
    completed: 'text-green-500',
    failed: 'text-red-500',
    cancelled: 'text-gray-500',
    paused: 'text-orange-500',
  }

  const statusLabels: Record<ImportStatus, string> = {
    pending: t('import.status.pending', 'Ожидает'),
    in_progress: t('import.status.inProgress', 'В процессе'),
    completed: t('import.status.completed', 'Завершён'),
    failed: t('import.status.failed', 'Ошибка'),
    cancelled: t('import.status.cancelled', 'Отменён'),
    paused: t('import.status.paused', 'Приостановлен'),
  }

  const canPauseResume = job.status === 'in_progress' || job.status === 'paused'
  const canCancel = job.status === 'pending' || job.status === 'in_progress' || job.status === 'paused'
  const isPaused = job.status === 'paused'

  return (
    <div className={`bg-[color:var(--color-panel)] shadow rounded-lg p-6 ${className}`}>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-[color:var(--color-text)]">
          {t('import.progressTitle', 'Прогресс импорта')}
        </h3>
        <div className="flex items-center gap-2">
          <span className={`flex items-center gap-1 text-xs ${statusColors[job.status]}`}>
            {statusLabels[job.status]}
          </span>
          <button
            onClick={handleRefresh}
            className="text-xs text-[color:var(--color-text-muted)] hover:text-[color:var(--color-text)] transition-colors disabled:opacity-50"
            title={t('common.refresh', 'Обновить')}
            disabled={updating}
          >
            <RefreshCw className={`w-4 h-4 ${updating ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Progress bar */}
      <div className="mb-4">
        <div className="flex items-center justify-between text-sm mb-2">
          <span className="text-[color:var(--color-text-muted)]">
            {t('import.progress', 'Прогресс')}: {job.progress_percentage.toFixed(1)}%
          </span>
          {job.total_items && job.total_items > 0 && (
            <span className="text-[color:var(--color-text-muted)]">
              {job.processed_items} / {job.total_items}
            </span>
          )}
        </div>
        <div className="w-full bg-[color:var(--color-surface-muted)] rounded-full h-3 overflow-hidden">
          <div
            className="h-full bg-blue-500 transition-all duration-300 ease-out"
            style={{ width: `${job.progress_percentage}%` }}
          />
        </div>
      </div>

      {/* Statistics */}
      <div className="grid grid-cols-4 gap-4 mb-4">
        <div className="bg-[color:var(--color-surface-muted)] rounded-lg p-3 text-center">
          <div className="text-2xl font-bold text-[color:var(--color-text)]">{job.processed_items}</div>
          <div className="text-xs text-[color:var(--color-text-muted)]">
            {t('import.processed', 'Обработано')}
          </div>
        </div>
        <div className="bg-[color:var(--color-surface-muted)] rounded-lg p-3 text-center">
          <div className="text-2xl font-bold text-green-500">{job.successful_items}</div>
          <div className="text-xs text-[color:var(--color-text-muted)]">
            {t('import.successful', 'Успешно')}
          </div>
        </div>
        <div className="bg-[color:var(--color-surface-muted)] rounded-lg p-3 text-center">
          <div className="text-2xl font-bold text-red-500">{job.failed_items}</div>
          <div className="text-xs text-[color:var(--color-text-muted)]">
            {t('import.failed', 'Ошибок')}
          </div>
        </div>
        <div className="bg-[color:var(--color-surface-muted)] rounded-lg p-3 text-center">
          <div className="text-2xl font-bold text-yellow-500">{job.skipped_items}</div>
          <div className="text-xs text-[color:var(--color-text-muted)]">
            {t('import.skipped', 'Пропущено')}
          </div>
        </div>
      </div>

      {/* Error message */}
      {job.error_message && (
        <div className="mb-4 p-3 bg-red-500/10 border border-red-500/30 rounded-lg">
          <p className="text-sm text-red-400">{job.error_message}</p>
        </div>
      )}

      {/* Action buttons */}
      <div className="flex items-center gap-2 justify-end">
        {canPauseResume && (
          <button
            onClick={handlePauseResume}
            disabled={updating}
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed
              ${isPaused
                ? 'bg-blue-500 text-white hover:bg-blue-600'
                : 'bg-yellow-500 text-white hover:bg-yellow-600'
              }"
          >
            {isPaused ? (
              <>
                <Play className="w-4 h-4" />
                {t('import.resume', 'Возобновить')}
              </>
            ) : (
              <>
                <Pause className="w-4 h-4" />
                {t('import.pause', 'Приостановить')}
              </>
            )}
          </button>
        )}
        {canCancel && (
          <button
            onClick={handleCancel}
            disabled={updating}
            className="flex items-center gap-2 px-4 py-2 bg-red-500 text-white rounded-lg text-sm font-medium hover:bg-red-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <X className="w-4 h-4" />
            {t('import.cancel', 'Отменить')}
          </button>
        )}
      </div>
    </div>
  )
}

export default ImportProgress
