/**
 * Мастер импорта контента.
 *
 * ОрMexестрает многошаговый процесс импорта:
 * - Выбор платформы (YouTube, Vimeo, Local)
 * - Заполнение формы импорта (специфично для платформы)
 * - Отслеживание прогресса импорта
 * - Просмотр результатов и сводки
 *
 * Feature: 011-content-import-migration-tools
 */
import React, { useState, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { X, ArrowLeft, ArrowRight } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import type { ImportPlatform, ImportJob } from '../../types/import'
import * as importApi from '../../api/import'
import { useToast } from '../../hooks/useToast'
import PlatformSelector from './PlatformSelector'
import YouTubeImportForm from './YouTubeImportForm'
import VimeoImportForm from './VimeoImportForm'
import LocalImportForm from './LocalImportForm'
import ImportProgress from './ImportProgress'
import ImportSummary from './ImportSummary'

/** Шаги мастера импорта */
type WizardStep = 'platform' | 'configure' | 'progress' | 'summary'

interface ImportWizardProps {
  /** Callback для закрытия мастера */
  onClose?: () => void
  /** Callback при успешном завершении импорта */
  onComplete?: (job: ImportJob) => void
  /** Опциональный channelId для импорта в конкретный канал */
  channelId?: string
  /** Custom CSS class name */
  className?: string
}

const ImportWizard: React.FC<ImportWizardProps> = ({
  onClose,
  onComplete,
  channelId,
  className = '',
}) => {
  const { t } = useTranslation()
  const toast = useToast()

  // State управления wizard
  const [currentStep, setCurrentStep] = useState<WizardStep>('platform')
  const [selectedPlatform, setSelectedPlatform] = useState<ImportPlatform | null>(null)
  const [jobId, setJobId] = useState<string | null>(null)
  const [completedJob, setCompletedJob] = useState<ImportJob | null>(null)

  // Переход к следующему шагу после выбора платформы
  const handlePlatformSelect = useCallback((platform: ImportPlatform) => {
    setSelectedPlatform(platform)
    setCurrentStep('configure')
  }, [])

  // Обработка успешного создания импорта из формы
  const handleImportCreated = useCallback(
    async (platform: ImportPlatform, requestData: Record<string, unknown>) => {
      try {
        const importRequest = {
          platform,
          channel_id: channelId,
          ...requestData,
        }

        const job = await importApi.importApi.createImport(importRequest as any)
        setJobId(job.id)
        setCurrentStep('progress')

        toast.success(
          t('import.wizard.jobCreated', 'Задание импорта создано успешно')
        )
      } catch (err: any) {
        console.error('[ImportWizard] Failed to create import job', err)

        const errorMessage =
          err?.response?.data?.detail ||
          t('import.wizard.createError', 'Не удалось создать задание импорта')

        toast.error(errorMessage)
        throw err // Re-throw to let form handle loading state
      }
    },
    [channelId, toast, t]
  )

  // Обработка завершения импорта
  const handleImportComplete = useCallback(
    (job: ImportJob) => {
      setCompletedJob(job)
      setCurrentStep('summary')

      // Notify parent component
      if (onComplete) {
        onComplete(job)
      }
    },
    [onComplete]
  )

  // Обработка отмены импорта
  const handleImportCancel = useCallback(() => {
    toast.info(t('import.wizard.cancelled', 'Импорт отменён'))

    // Return to platform selection to start over
    resetWizard()
  }, [toast, t])

  // Начать новый импорт из сводки
  const handleNewImport = useCallback(() => {
    resetWizard()
  }, [])

  // Сброс состояния мастера
  const resetWizard = useCallback(() => {
    setCurrentStep('platform')
    setSelectedPlatform(null)
    setJobId(null)
    setCompletedJob(null)
  }, [])

  // Закрытие мастера
  const handleClose = useCallback(() => {
    if (onClose) {
      onClose()
    }
  }, [onClose])

  // Можно ли вернуться назад
  const canGoBack = currentStep === 'configure'

  // Обработка перехода назад
  const handleBack = useCallback(() => {
    if (canGoBack) {
      setCurrentStep('platform')
      setSelectedPlatform(null)
    }
  }, [canGoBack])

  // Рендер текущего шага
  const renderStep = () => {
    switch (currentStep) {
      case 'platform':
        return <PlatformSelector selectedPlatform={selectedPlatform} onPlatformSelect={handlePlatformSelect} />

      case 'configure':
        if (!selectedPlatform) {
          setCurrentStep('platform')
          return null
        }

        switch (selectedPlatform) {
          case 'youtube':
            return (
              <YouTubeImportForm
                onImported={(data) => handleImportCreated('youtube', data)}
              />
            )
          case 'vimeo':
            return (
              <VimeoImportForm
                onImported={(data) => handleImportCreated('vimeo', data)}
              />
            )
          case 'local':
            return (
              <LocalImportForm
                onImported={(data) => handleImportCreated('local', data)}
              />
            )
          default:
            return null
        }

      case 'progress':
        if (!jobId) {
          setCurrentStep('platform')
          return null
        }

        return (
          <ImportProgress
            jobId={jobId}
            onComplete={handleImportComplete}
            onCancel={handleImportCancel}
          />
        )

      case 'summary':
        if (!jobId) {
          setCurrentStep('platform')
          return null
        }

        return <ImportSummary jobId={jobId} onNewImport={handleNewImport} />

      default:
        return null
    }
  }

  // Заголовок текущего шага
  const getStepTitle = () => {
    switch (currentStep) {
      case 'platform':
        return t('import.wizard.steps.platform', 'Выберите платформу')
      case 'configure':
        return t('import.wizard.steps.configure', 'Настройте импорт')
      case 'progress':
        return t('import.wizard.steps.progress', 'Прогресс импорта')
      case 'summary':
        return t('import.wizard.steps.summary', 'Результаты импорта')
      default:
        return ''
    }
  }

  return (
    <div
      className={`fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm ${className}`}
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        transition={{ duration: 0.2 }}
        className="relative w-full max-w-4xl max-h-[90vh] overflow-y-auto bg-[color:var(--color-panel)] rounded-xl shadow-2xl m-4"
      >
        {/* Header */}
        <div className="sticky top-0 z-10 flex items-center justify-between px-6 py-4 border-b border-[color:var(--color-border)] bg-[color:var(--color-panel)]">
          <div className="flex items-center gap-3">
            <button
              onClick={handleBack}
              disabled={!canGoBack}
              className={`p-2 rounded-lg transition-colors ${
                canGoBack
                  ? 'text-[color:var(--color-text)] hover:bg-[color:var(--color-surface-muted)]'
                  : 'text-[color:var(--color-text-muted)] cursor-not-allowed opacity-50'
              }`}
              title={t('common.back', 'Назад')}
            >
              <ArrowLeft className="w-5 h-5" />
            </button>

            <div>
              <h2 className="text-lg font-semibold text-[color:var(--color-text)]">
                {t('import.wizard.title', 'Мастер импорта')}
              </h2>
              <p className="text-xs text-[color:var(--color-text-muted)]">
                {getStepTitle()}
              </p>
            </div>
          </div>

          <button
            onClick={handleClose}
            className="p-2 rounded-lg text-[color:var(--color-text-muted)] hover:bg-[color:var(--color-surface-muted)] transition-colors"
            title={t('common.close', 'Закрыть')}
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Progress indicator */}
        <div className="px-6 py-3 border-b border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)]">
          <div className="flex items-center justify-between">
            {['platform', 'configure', 'progress', 'summary'].map((step, index) => {
              const stepNumber = index + 1
              const isCurrent = currentStep === step
              const isPast =
                ['platform', 'configure', 'progress', 'summary'].indexOf(currentStep) > index

              return (
                <React.Fragment key={step}>
                  <div className="flex flex-col items-center">
                    <div
                      className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium transition-colors ${
                        isCurrent
                          ? 'bg-[color:var(--color-accent)] text-white'
                          : isPast
                            ? 'bg-green-500 text-white'
                            : 'bg-[color:var(--color-surface)] text-[color:var(--color-text-muted)] border border-[color:var(--color-border)]'
                      }`}
                    >
                      {isPast ? <span className="text-xs">✓</span> : stepNumber}
                    </div>
                    <span
                      className={`text-xs mt-1 ${
                        isCurrent
                          ? 'text-[color:var(--color-text)] font-medium'
                          : 'text-[color:var(--color-text-muted)]'
                      }`}
                    >
                      {t(`import.wizard.indicator.${step}`, step)}
                    </span>
                  </div>

                  {index < 3 && (
                    <div
                      className={`flex-1 h-0.5 mx-2 transition-colors ${
                        isPast ? 'bg-green-500' : 'bg-[color:var(--color-border)]'
                      }`}
                    />
                  )}
                </React.Fragment>
              )
            })}
          </div>
        </div>

        {/* Content */}
        <div className="p-6">
          <AnimatePresence mode="wait">
            <motion.div
              key={currentStep}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ duration: 0.2 }}
            >
              {renderStep()}
            </motion.div>
          </AnimatePresence>
        </div>

        {/* Footer */}
        <div className="sticky bottom-0 px-6 py-4 border-t border-[color:var(--color-border)] bg-[color:var(--color-panel)]">
          <div className="flex items-center justify-between text-sm text-[color:var(--color-text-muted)]">
            <p>
              {t('import.wizard.footerHint', 'Следуйте шагам для импорта контента')}
            </p>
            {currentStep === 'platform' && (
              <button
                onClick={handleClose}
                className="px-4 py-2 rounded-lg border border-[color:var(--color-border)] hover:bg-[color:var(--color-surface-muted)] transition-colors"
              >
                {t('common.cancel', 'Отмена')}
              </button>
            )}
          </div>
        </div>
      </motion.div>
    </div>
  )
}

export default ImportWizard
