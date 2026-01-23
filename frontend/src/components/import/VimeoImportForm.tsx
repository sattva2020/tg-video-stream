import React, { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Video, Layers, Download } from 'lucide-react'
import { useToast } from '../../hooks/useToast'

type ImportType = 'album' | 'batch'
type QualityOption = 'auto' | '1080p' | '720p' | '480p' | 'audio-only'

const importTypes: { key: ImportType; label: string; icon: typeof Layers | typeof Video }[] = [
  { key: 'album', label: 'Album', icon: Layers },
  { key: 'batch', label: 'Batch', icon: Video },
]

const qualityOptions: { key: QualityOption; label: string }[] = [
  { key: 'auto', label: 'Auto' },
  { key: '1080p', label: '1080p' },
  { key: '720p', label: '720p' },
  { key: '480p', label: '480p' },
  { key: 'audio-only', label: 'Audio Only' },
]

interface VimeoImportFormProps {
  /** Callback when import is successfully submitted */
  onImported?: () => void
  /** Optional className for custom styling */
  className?: string
}

const VimeoImportForm: React.FC<VimeoImportFormProps> = ({ onImported, className = '' }) => {
  const { t } = useTranslation()
  const [url, setUrl] = useState('')
  const [importType, setImportType] = useState<ImportType>('album')
  const [quality, setQuality] = useState<QualityOption>('auto')
  const [loading, setLoading] = useState(false)
  const toast = useToast()

  const validateVimeoUrl = (url: string): boolean => {
    if (!url.trim()) return false

    // Basic Vimeo URL validation
    const vimeoPatterns = [
      /^https?:\/\/(www\.)?vimeo\.com\/\d+/, // Single video
      /^https?:\/\/(www\.)?vimeo\.com\/album\/\d+/, // Album
      /^https?:\/\/(www\.)?vimeo\.com\/channels\/[\w-]+/, // Channel
      /^https?:\/\/(www\.)?vimeo\.com\/groups\/[\w-]+/, // Group
      /^https?:\/\/(www\.)?vimeo\.com\/showcase\/\d+/, // Showcase
    ]

    return vimeoPatterns.some((pattern) => pattern.test(url))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!url.trim()) {
      toast.error(t('import.vimeo.urlRequired', 'Введите URL'))
      return
    }

    if (!validateVimeoUrl(url)) {
      toast.error(t('import.vimeo.invalidUrl', 'Неверный формат URL Vimeo'))
      return
    }

    setLoading(true)
    try {
      // TODO: Implement actual import service call
      // For now, simulate API call
      await new Promise((resolve) => setTimeout(resolve, 1500))

      toast.success(
        t(
          'import.vimeo.importStarted',
          importType === 'album'
            ? 'Импорт альбома начат'
            : 'Импорт группы видео начат'
        )
      )

      setUrl('')
      if (onImported) onImported()
    } catch (err) {
      toast.error(t('import.vimeo.importError', 'Не удалось начать импорт'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={`bg-[color:var(--color-panel)] border border-[color:var(--color-outline)] rounded-xl p-4 sm:p-6 ${className}`}>
      <div className="flex items-center gap-3 mb-4">
        <Video className="w-6 h-6 text-cyan-500" />
        <h3 className="text-lg font-semibold text-[color:var(--color-text)]">
          {t('import.vimeo.title', 'Импорт из Vimeo')}
        </h3>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* URL Input */}
        <div>
          <label className="block text-sm font-medium text-[color:var(--color-text-muted)] mb-1">
            {t('import.vimeo.urlLabel', 'URL альбома или видео')} *
          </label>
          <input
            type="url"
            placeholder="https://vimeo.com/album/... или https://vimeo.com/..."
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            required
            className="w-full px-4 py-2.5 rounded-lg border border-[color:var(--color-outline)] bg-[color:var(--color-surface)] text-[color:var(--color-text)] placeholder-[color:var(--color-text-muted)] focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
          />
          <p className="mt-1 text-xs text-[color:var(--color-text-muted)]">
            {t('import.vimeo.urlHint', 'Поддерживаются альбомы, отдельные видео, каналы и витрины')}
          </p>
        </div>

        {/* Import Type Select */}
        <div>
          <label className="block text-sm font-medium text-[color:var(--color-text-muted)] mb-1">
            {t('import.vimeo.typeLabel', 'Тип импорта')}
          </label>
          <div className="flex gap-2">
            {importTypes.map((it) => (
              <button
                key={it.key}
                type="button"
                onClick={() => setImportType(it.key)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg border transition-colors ${
                  importType === it.key
                    ? 'bg-cyan-500 text-white border-cyan-500'
                    : 'bg-[color:var(--color-surface)] text-[color:var(--color-text)] border-[color:var(--color-outline)] hover:bg-[color:var(--color-surface-muted)]'
                }`}
              >
                <it.icon className="w-4 h-4" />
                {it.label}
              </button>
            ))}
          </div>
        </div>

        {/* Quality Select */}
        <div>
          <label className="block text-sm font-medium text-[color:var(--color-text-muted)] mb-1">
            {t('import.vimeo.qualityLabel', 'Качество')}
          </label>
          <div className="grid grid-cols-3 sm:grid-cols-5 gap-2">
            {qualityOptions.map((qo) => (
              <button
                key={qo.key}
                type="button"
                onClick={() => setQuality(qo.key)}
                className={`px-3 py-2 rounded-lg border text-sm transition-colors ${
                  quality === qo.key
                    ? 'bg-cyan-500 text-white border-cyan-500'
                    : 'bg-[color:var(--color-surface)] text-[color:var(--color-text)] border-[color:var(--color-outline)] hover:bg-[color:var(--color-surface-muted)]'
                }`}
              >
                {qo.label}
              </button>
            ))}
          </div>
        </div>

        {/* Submit Button */}
        <button
          type="submit"
          disabled={loading || !url.trim()}
          className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-cyan-500 hover:bg-cyan-600 disabled:bg-gray-400 disabled:cursor-not-allowed text-white font-medium rounded-lg transition-colors"
        >
          {loading ? (
            <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
          ) : (
            <>
              <Download className="w-5 h-5" />
              {t('import.vimeo.importButton', 'Импортировать')}
            </>
          )}
        </button>
      </form>
    </div>
  )
}

export default VimeoImportForm
