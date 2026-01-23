import React, { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { FolderOpen, Upload, CheckCircle2, Folder, FileAudio } from 'lucide-react'
import { useToast } from '../../hooks/useToast'

type ScanMode = 'folder' | 'files'

const scanModes: { key: ScanMode; label: string; icon: typeof Folder | typeof FileAudio }[] = [
  { key: 'folder', label: 'Folder', icon: Folder },
  { key: 'files', label: 'Files', icon: FileAudio },
]

interface LocalImportFormProps {
  /** Callback when import is successfully submitted */
  onImported?: () => void
  /** Optional className for custom styling */
  className?: string
}

const LocalImportForm: React.FC<LocalImportFormProps> = ({ onImported, className = '' }) => {
  const { t } = useTranslation()
  const [scanMode, setScanMode] = useState<ScanMode>('folder')
  const [recursive, setRecursive] = useState(true)
  const [fetchMetadata, setFetchMetadata] = useState(true)
  const [loading, setLoading] = useState(false)
  const toast = useToast()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    // TODO: Validate that files/folder were selected
    // For now, we'll simulate the import
    setLoading(true)
    try {
      // TODO: Implement actual import service call
      // For now, simulate API call
      await new Promise((resolve) => setTimeout(resolve, 1500))

      toast.success(
        t(
          'import.local.importStarted',
          scanMode === 'folder'
            ? 'Сканирование папки начато'
            : 'Импорт файлов начат'
        )
      )

      if (onImported) onImported()
    } catch (err) {
      toast.error(t('import.local.importError', 'Не удалось начать импорт'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={`bg-[color:var(--color-panel)] border border-[color:var(--color-outline)] rounded-xl p-4 sm:p-6 ${className}`}>
      <div className="flex items-center gap-3 mb-4">
        <FolderOpen className="w-6 h-6 text-green-500" />
        <h3 className="text-lg font-semibold text-[color:var(--color-text)]">
          {t('import.local.title', 'Импорт локальных файлов')}
        </h3>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Scan Mode Select */}
        <div>
          <label className="block text-sm font-medium text-[color:var(--color-text-muted)] mb-1">
            {t('import.local.modeLabel', 'Режим сканирования')}
          </label>
          <div className="flex gap-2">
            {scanModes.map((sm) => (
              <button
                key={sm.key}
                type="button"
                onClick={() => setScanMode(sm.key)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg border transition-colors ${
                  scanMode === sm.key
                    ? 'bg-green-500 text-white border-green-500'
                    : 'bg-[color:var(--color-surface)] text-[color:var(--color-text)] border-[color:var(--color-outline)] hover:bg-[color:var(--color-surface-muted)]'
                }`}
              >
                <sm.icon className="w-4 h-4" />
                {sm.label}
              </button>
            ))}
          </div>
        </div>

        {/* File/Folder Input Area */}
        <div>
          <label className="block text-sm font-medium text-[color:var(--color-text-muted)] mb-1">
            {t('import.local.pathLabel', scanMode === 'folder' ? 'Путь к папке' : 'Выберите файлы')} *
          </label>
          <div className="relative">
            <input
              type="text"
              placeholder={scanMode === 'folder' ? '/path/to/media/folder' : 'Выберите файлы...'}
              className="w-full px-4 py-2.5 pr-24 rounded-lg border border-[color:var(--color-outline)] bg-[color:var(--color-surface)] text-[color:var(--color-text)] placeholder-[color:var(--color-text-muted)] focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent"
              disabled
            />
            <button
              type="button"
              className="absolute right-2 top-1/2 -translate-y-1/2 px-3 py-1.5 bg-green-500 hover:bg-green-600 text-white text-sm font-medium rounded-lg transition-colors flex items-center gap-1.5"
            >
              <Upload className="w-4 h-4" />
              {t('import.local.browseButton', 'Обзор')}
            </button>
          </div>
          <p className="mt-1 text-xs text-[color:var(--color-text-muted)]">
            {t('import.local.pathHint', scanMode === 'folder'
              ? 'Выберите папку с медиафайлами для сканирования'
              : 'Поддерживаются аудиофайлы: MP3, FLAC, WAV, OGG, M4A'
            )}
          </p>
        </div>

        {/* Options */}
        <div className="space-y-2">
          {scanMode === 'folder' && (
            <label className="flex items-center gap-3 p-3 rounded-lg border border-[color:var(--color-outline)] bg-[color:var(--color-surface)] cursor-pointer hover:bg-[color:var(--color-surface-muted)] transition-colors">
              <input
                type="checkbox"
                checked={recursive}
                onChange={(e) => setRecursive(e.target.checked)}
                className="w-4 h-4 text-green-500 rounded focus:ring-2 focus:ring-green-500 focus:ring-offset-0"
              />
              <div className="flex-1">
                <div className="text-sm font-medium text-[color:var(--color-text)]">
                  {t('import.local.recursiveLabel', 'Рекурсивное сканирование')}
                </div>
                <div className="text-xs text-[color:var(--color-text-muted)]">
                  {t('import.local.recursiveHint', 'Сканировать вложенные папки')}
                </div>
              </div>
            </label>
          )}

          <label className="flex items-center gap-3 p-3 rounded-lg border border-[color:var(--color-outline)] bg-[color:var(--color-surface)] cursor-pointer hover:bg-[color:var(--color-surface-muted)] transition-colors">
            <input
              type="checkbox"
              checked={fetchMetadata}
              onChange={(e) => setFetchMetadata(e.target.checked)}
              className="w-4 h-4 text-green-500 rounded focus:ring-2 focus:ring-green-500 focus:ring-offset-0"
            />
            <div className="flex-1">
              <div className="text-sm font-medium text-[color:var(--color-text)]">
                {t('import.local.metadataLabel', 'Извлечь метаданные')}
              </div>
              <div className="text-xs text-[color:var(--color-text-muted)]">
                {t('import.local.metadataHint', 'Читать ID3 теги и другую информацию из файлов')}
              </div>
            </div>
          </label>
        </div>

        {/* Submit Button */}
        <button
          type="submit"
          disabled={loading}
          className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-green-500 hover:bg-green-600 disabled:bg-gray-400 disabled:cursor-not-allowed text-white font-medium rounded-lg transition-colors"
        >
          {loading ? (
            <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
          ) : (
            <>
              <CheckCircle2 className="w-5 h-5" />
              {t('import.local.importButton', 'Импортировать')}
            </>
          )}
        </button>
      </form>
    </div>
  )
}

export default LocalImportForm
