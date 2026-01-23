import React, { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Youtube, ListVideo, Video, Download } from 'lucide-react'
import { useToast } from '../../hooks/useToast'

type ImportType = 'playlist' | 'video'
type QualityOption = 'auto' | '1080p' | '720p' | '480p' | 'audio-only'

const importTypes: { key: ImportType; label: string; icon: typeof ListVideo | typeof Video }[] = [
  { key: 'playlist', label: 'Playlist', icon: ListVideo },
  { key: 'video', label: 'Video', icon: Video },
]

const qualityOptions: { key: QualityOption; label: string }[] = [
  { key: 'auto', label: 'Auto' },
  { key: '1080p', label: '1080p' },
  { key: '720p', label: '720p' },
  { key: '480p', label: '480p' },
  { key: 'audio-only', label: 'Audio Only' },
]

interface YouTubeImportFormProps {
  /** Callback when import is submitted with request data */
  onImported?: (data: { source_url: string; options: Record<string, unknown> }) => void
  /** Optional className for custom styling */
  className?: string
}

const YouTubeImportForm: React.FC<YouTubeImportFormProps> = ({ onImported, className = '' }) => {
  const { t } = useTranslation()
  const [url, setUrl] = useState('')
  const [importType, setImportType] = useState<ImportType>('playlist')
  const [quality, setQuality] = useState<QualityOption>('auto')
  const [loading, setLoading] = useState(false)
  const toast = useToast()

  const validateYouTubeUrl = (url: string): boolean => {
    if (!url.trim()) return false

    // Basic YouTube URL validation
    const youtubePatterns = [
      /^https?:\/\/(www\.)?youtube\.com\/watch\?v=[\w-]+/,
      /^https?:\/\/(www\.)?youtube\.com\/playlist\?list=[\w-]+/,
      /^https?:\/\/youtu\.be\/[\w-]+/,
      /^https?:\/\/(www\.)?youtube\.com\/shorts\/[\w-]+/,
    ]

    return youtubePatterns.some((pattern) => pattern.test(url))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!url.trim()) {
      toast.error(t('import.youtube.urlRequired', 'Введите URL'))
      return
    }

    if (!validateYouTubeUrl(url)) {
      toast.error(t('import.youtube.invalidUrl', 'Неверный формат URL YouTube'))
      return
    }

    setLoading(true)
    try {
      // Map quality option to backend format
      const qualityMap: Record<QualityOption, string> = {
        'auto': 'best',
        '1080p': 'high',
        '720p': 'medium',
        '480p': 'low',
        'audio-only': 'audio',
      }

      const requestData = {
        source_url: url.trim(),
        options: {
          quality: qualityMap[quality],
          fetch_metadata: true,
          import_type: importType,
        },
      }

      toast.success(
        t(
          'import.youtube.importStarted',
          importType === 'playlist'
            ? 'Импорт плейлиста начат'
            : 'Импорт видео начат'
        )
      )

      setUrl('')
      if (onImported) onImported(requestData)
    } catch (err) {
      toast.error(t('import.youtube.importError', 'Не удалось начать импорт'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={`bg-[color:var(--color-panel)] border border-[color:var(--color-outline)] rounded-xl p-4 sm:p-6 ${className}`}>
      <div className="flex items-center gap-3 mb-4">
        <Youtube className="w-6 h-6 text-red-500" />
        <h3 className="text-lg font-semibold text-[color:var(--color-text)]">
          {t('import.youtube.title', 'Импорт из YouTube')}
        </h3>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* URL Input */}
        <div>
          <label className="block text-sm font-medium text-[color:var(--color-text-muted)] mb-1">
            {t('import.youtube.urlLabel', 'URL плейлиста или видео')} *
          </label>
          <input
            type="url"
            placeholder="https://www.youtube.com/playlist?list=... или https://youtu.be/..."
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            required
            className="w-full px-4 py-2.5 rounded-lg border border-[color:var(--color-outline)] bg-[color:var(--color-surface)] text-[color:var(--color-text)] placeholder-[color:var(--color-text-muted)] focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-transparent"
          />
          <p className="mt-1 text-xs text-[color:var(--color-text-muted)]">
            {t('import.youtube.urlHint', 'Поддерживаются плейлисты, отдельные видео и Shorts')}
          </p>
        </div>

        {/* Import Type Select */}
        <div>
          <label className="block text-sm font-medium text-[color:var(--color-text-muted)] mb-1">
            {t('import.youtube.typeLabel', 'Тип импорта')}
          </label>
          <div className="flex gap-2">
            {importTypes.map((it) => (
              <button
                key={it.key}
                type="button"
                onClick={() => setImportType(it.key)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg border transition-colors ${
                  importType === it.key
                    ? 'bg-red-500 text-white border-red-500'
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
            {t('import.youtube.qualityLabel', 'Качество')}
          </label>
          <div className="grid grid-cols-3 sm:grid-cols-5 gap-2">
            {qualityOptions.map((qo) => (
              <button
                key={qo.key}
                type="button"
                onClick={() => setQuality(qo.key)}
                className={`px-3 py-2 rounded-lg border text-sm transition-colors ${
                  quality === qo.key
                    ? 'bg-red-500 text-white border-red-500'
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
          className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-red-500 hover:bg-red-600 disabled:bg-gray-400 disabled:cursor-not-allowed text-white font-medium rounded-lg transition-colors"
        >
          {loading ? (
            <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
          ) : (
            <>
              <Download className="w-5 h-5" />
              {t('import.youtube.importButton', 'Импортировать')}
            </>
          )}
        </button>
      </form>
    </div>
  )
}

export default YouTubeImportForm
