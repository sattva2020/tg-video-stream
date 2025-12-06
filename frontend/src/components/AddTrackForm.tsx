import React, { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Plus, Music, Youtube, FileAudio } from 'lucide-react'
import * as playlistService from '../services/playlist'
import { useToast } from '../hooks/useToast'

const trackTypes = [
  { key: 'stream', label: 'Stream', icon: Music },
  { key: 'youtube', label: 'YouTube', icon: Youtube },
  { key: 'local', label: 'Local', icon: FileAudio },
]

const AddTrackForm: React.FC<{ onAdded?: () => void }> = ({ onAdded }) => {
  const { t } = useTranslation()
  const [url, setUrl] = useState('')
  const [title, setTitle] = useState('')
  const [type, setType] = useState<'stream' | 'youtube' | 'local'>('youtube')
  const [loading, setLoading] = useState(false)
  const toast = useToast()

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
          <label className="block text-sm font-medium text-[color:var(--color-text-muted)] mb-1">
            URL трека *
          </label>
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
          <label className="block text-sm font-medium text-[color:var(--color-text-muted)] mb-1">
            Тип источника
          </label>
          <div className="flex gap-2">
            {trackTypes.map((tt) => (
              <button
                key={tt.key}
                type="button"
                onClick={() => setType(tt.key as typeof type)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg border transition-colors ${
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
