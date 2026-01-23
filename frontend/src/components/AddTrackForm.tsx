import React, { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Plus,
  Music,
  Youtube,
  FileAudio,
  Video,
  Radio,
  Cloud,
  FileText,
  Globe,
  Loader2
} from 'lucide-react'
import * as playlistService from '../services/playlist'
import { useToast } from '../hooks/useToast'
import { videoSourcesApi } from '../api/video_sources'
import type { SourceType } from '../types/video_sources'

const trackTypes = [
  { key: 'stream', label: 'Stream', icon: Music },
  { key: 'youtube', label: 'YouTube', icon: Youtube },
  { key: 'vimeo', label: 'Vimeo', icon: Video },
  { key: 'dailymotion', label: 'Dailymotion', icon: Video },
  { key: 'twitch', label: 'Twitch', icon: Radio },
  { key: 'direct', label: 'Direct URL', icon: Video },
  { key: 'hls', label: 'HLS Stream', icon: Radio },
  { key: 'dash', label: 'DASH Stream', icon: Radio },
  { key: 'google_drive', label: 'Google Drive', icon: Cloud },
  { key: 'dropbox', label: 'Dropbox', icon: Cloud },
  { key: 'onedrive', label: 'OneDrive', icon: Cloud },
  { key: 'rss_feed', label: 'RSS Feed', icon: FileText },
  { key: 'local', label: 'Local', icon: FileAudio },
] as const

const AddTrackForm: React.FC<{ onAdded?: () => void }> = ({ onAdded }) => {
  const { t } = useTranslation()
  const [url, setUrl] = useState('')
  const [title, setTitle] = useState('')
  const [type, setType] = useState<SourceType>('youtube')
  const [loading, setLoading] = useState(false)
  const [detecting, setDetecting] = useState(false)
  const [detectedType, setDetectedType] = useState<SourceType | null>(null)
  const [autoDetectEnabled, setAutoDetectEnabled] = useState(true)
  const toast = useToast()

  // Auto-detect source type from URL
  useEffect(() => {
    if (!url.trim() || !autoDetectEnabled) {
      setDetectedType(null)
      return
    }

    const timeoutId = setTimeout(async () => {
      setDetecting(true)
      try {
        const result = await videoSourcesApi.detectSource(url.trim())
        if (result.valid && result.source_type) {
          setDetectedType(result.source_type as SourceType)
          setType(result.source_type as SourceType)
        } else {
          setDetectedType(null)
        }
      } catch (err) {
        // Silently fail on detection errors - user can still select manually
        setDetectedType(null)
      } finally {
        setDetecting(false)
      }
    }, 500) // Debounce detection

    return () => clearTimeout(timeoutId)
  }, [url, autoDetectEnabled])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!url.trim()) {
      toast.error(t('playlist.urlRequired', 'Введите URL'))
      return
    }
    setLoading(true)
    try {
      await playlistService.addTrack({ url: url.trim(), title: title.trim() || undefined, type })
      setUrl('')
      setTitle('')
      toast.success(t('playlist.trackAdded', 'Трек успешно добавлен'))
      if (onAdded) onAdded()
    } catch (err) {
      console.error('Failed to add track', err)
      toast.error(t('playlist.addError', 'Не удалось добавить трек'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="bg-[color:var(--color-panel)] border border-[color:var(--color-outline)] rounded-xl p-4 sm:p-6">
      <h3 className="text-lg font-semibold text-[color:var(--color-text)] mb-4">
        {t('playlist.addTrack', 'Добавить трек')}
      </h3>
      
      <form onSubmit={handleSubmit} className="space-y-4">
        {/* URL Input */}
        <div>
          <div className="flex items-center justify-between mb-1">
            <label className="block text-sm font-medium text-[color:var(--color-text-muted)]">
              URL трека *
            </label>
            {detecting && (
              <div className="flex items-center gap-1.5 text-xs text-[color:var(--color-text-muted)]">
                <Loader2 className="w-3 h-3 animate-spin" />
                Detecting...
              </div>
            )}
            {detectedType && !detecting && (
              <div className="flex items-center gap-1.5 text-xs text-green-600">
                <Globe className="w-3 h-3" />
                Detected: {trackTypes.find(t => t.key === detectedType)?.label}
              </div>
            )}
          </div>
          <input
            type="url"
            placeholder="https://www.youtube.com/watch?v=..."
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            required
            className="w-full px-4 py-2.5 rounded-lg border border-[color:var(--color-outline)] bg-[color:var(--color-surface)] text-[color:var(--color-text)] placeholder-[color:var(--color-text-muted)] focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent"
          />
        </div>

        {/* Type Select */}
        <div>
          <div className="flex items-center justify-between mb-1">
            <label className="block text-sm font-medium text-[color:var(--color-text-muted)]">
              Тип источника
            </label>
            <label className="flex items-center gap-1.5 text-xs text-[color:var(--color-text-muted)] cursor-pointer">
              <input
                type="checkbox"
                checked={autoDetectEnabled}
                onChange={(e) => setAutoDetectEnabled(e.target.checked)}
                className="rounded"
              />
              Auto-detect
            </label>
          </div>
          <div className="flex flex-wrap gap-2">
            {trackTypes.map((tt) => (
              <button
                key={tt.key}
                type="button"
                onClick={() => {
                  setType(tt.key as SourceType)
                  setAutoDetectEnabled(false) // Disable auto-detect when manually selecting
                }}
                className={`flex items-center gap-2 px-3 py-2 rounded-lg border transition-colors ${
                  type === tt.key
                    ? 'bg-orange-500 text-white border-orange-500'
                    : 'bg-[color:var(--color-surface)] text-[color:var(--color-text)] border-[color:var(--color-outline)] hover:bg-[color:var(--color-surface-muted)]'
                }`}
              >
                <tt.icon className="w-4 h-4" />
                {tt.label}
              </button>
            ))}
          </div>
        </div>

        {/* Title Input */}
        <div>
          <label className="block text-sm font-medium text-[color:var(--color-text-muted)] mb-1">
            {t('playlist.titlePlaceholder', 'Название (необязательно)')}
          </label>
          <input
            type="text"
            placeholder="Название трека"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="w-full px-4 py-2.5 rounded-lg border border-[color:var(--color-outline)] bg-[color:var(--color-surface)] text-[color:var(--color-text)] placeholder-[color:var(--color-text-muted)] focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent"
          />
        </div>
        
        {/* Submit Button */}
        <button
          type="submit"
          disabled={loading || !url.trim()}
          className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-orange-500 hover:bg-orange-600 disabled:bg-gray-400 disabled:cursor-not-allowed text-white font-medium rounded-lg transition-colors"
        >
          {loading ? (
            <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
          ) : (
            <>
              <Plus className="w-5 h-5" />
              {t('playlist.add', 'Добавить')}
            </>
          )}
        </button>
      </form>
    </div>
  )
}

export default AddTrackForm
