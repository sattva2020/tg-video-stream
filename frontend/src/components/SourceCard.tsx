import React from 'react'
import { useTranslation } from 'react-i18next'
import {
  Music,
  Youtube,
  FileAudio,
  Video,
  Radio,
  Cloud,
  FileText,
  Globe,
  Trash2,
  CheckCircle,
  XCircle,
  Clock,
  AlertCircle
} from 'lucide-react'
import type { SourceType } from '../types/video_sources'

interface SourceCardProps {
  id: string
  url: string
  title?: string
  type: SourceType
  status?: 'playing' | 'queued' | 'error' | 'completed'
  duration?: number | null
  thumbnail_url?: string
  is_live?: boolean
  requires_auth?: boolean
  position?: number
  created_at: string
  onDelete?: (id: string) => void
  deleting?: boolean
}

const sourceTypeIcons: Record<SourceType, React.ElementType> = {
  youtube: Youtube,
  vimeo: Video,
  dailymotion: Video,
  twitch: Radio,
  direct: Video,
  hls: Radio,
  dash: Radio,
  google_drive: Cloud,
  dropbox: Cloud,
  onedrive: Cloud,
  rss_feed: FileText,
  unknown: Globe,
}

const sourceTypeLabels: Record<SourceType, string> = {
  youtube: 'YouTube',
  vimeo: 'Vimeo',
  dailymotion: 'Dailymotion',
  twitch: 'Twitch',
  direct: 'Direct URL',
  hls: 'HLS Stream',
  dash: 'DASH Stream',
  google_drive: 'Google Drive',
  dropbox: 'Dropbox',
  onedrive: 'OneDrive',
  rss_feed: 'RSS Feed',
  unknown: 'Unknown',
}

const statusIcons = {
  playing: CheckCircle,
  queued: Clock,
  error: XCircle,
  completed: CheckCircle,
}

const statusColors = {
  playing: 'text-blue-400',
  queued: 'text-yellow-400',
  error: 'text-red-400',
  completed: 'text-green-400',
}

const formatDuration = (seconds: number | null | undefined): string => {
  if (!seconds) return '—'
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins}:${String(secs).padStart(2, '0')}`
}

const SourceCard: React.FC<SourceCardProps> = ({
  id,
  url,
  title,
  type,
  status,
  duration,
  thumbnail_url,
  is_live,
  requires_auth,
  position,
  created_at,
  onDelete,
  deleting = false,
}) => {
  const { t } = useTranslation()
  const TypeIcon = sourceTypeIcons[type] || Globe
  const StatusIcon = status ? statusIcons[status] : null

  const handleDelete = () => {
    if (onDelete && !deleting) {
      onDelete(id)
    }
  }

  return (
    <div className={`p-4 border rounded-lg transition-all ${
      status === 'playing'
        ? 'bg-blue-500/10 border-blue-500/30 shadow-sm'
        : status === 'error'
        ? 'bg-red-500/5 border-red-500/20'
        : 'bg-[color:var(--color-surface-muted)] border-[color:var(--color-outline)] hover:border-[color:var(--color-outline-variant)]'
    }`}>
      <div className="flex gap-4">
        {/* Thumbnail or Icon */}
        <div className="flex-shrink-0">
          {thumbnail_url ? (
            <img
              src={thumbnail_url}
              alt={title || 'Thumbnail'}
              className="w-24 h-16 object-cover rounded-md"
              loading="lazy"
            />
          ) : (
            <div className="w-24 h-16 bg-[color:var(--color-surface)] rounded-md flex items-center justify-center">
              <TypeIcon className="w-8 h-8 text-[color:var(--color-text-muted)]" />
            </div>
          )}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          {/* Title */}
          <div className="flex items-start justify-between gap-2 mb-1">
            <h4 className="font-medium text-[color:var(--color-text)] truncate">
              {title || t('sources.untitled', 'Без названия')}
            </h4>
            {position !== undefined && (
              <span className="text-xs text-[color:var(--color-text-muted)]">
                #{position + 1}
              </span>
            )}
          </div>

          {/* URL */}
          <div className="text-sm text-[color:var(--color-text-muted)] truncate mb-2">
            {url}
          </div>

          {/* Metadata Row */}
          <div className="flex items-center gap-3 flex-wrap text-xs">
            {/* Source Type */}
            <span className="flex items-center gap-1.5 px-2 py-1 rounded bg-[color:var(--color-surface)] text-[color:var(--color-text)]">
              <TypeIcon className="w-3.5 h-3.5" />
              {sourceTypeLabels[type]}
            </span>

            {/* Status */}
            {status && StatusIcon && (
              <span className={`flex items-center gap-1 ${statusColors[status]}`}>
                <StatusIcon className="w-3.5 h-3.5" />
                {t(`sources.status.${status}`, status)}
              </span>
            )}

            {/* Duration */}
            {duration && (
              <span className="text-[color:var(--color-text-muted)]">
                {formatDuration(duration)}
              </span>
            )}

            {/* Live Badge */}
            {is_live && (
              <span className="flex items-center gap-1 px-2 py-0.5 rounded bg-red-500/20 text-red-400 text-xs font-medium">
                <span className="w-1.5 h-1.5 bg-red-500 rounded-full animate-pulse" />
                LIVE
              </span>
            )}

            {/* Auth Badge */}
            {requires_auth && (
              <span className="flex items-center gap-1 text-yellow-500" title="Requires authentication">
                <AlertCircle className="w-3.5 h-3.5" />
              </span>
            )}
          </div>
        </div>

        {/* Actions */}
        <div className="flex-shrink-0">
          {onDelete && (
            <button
              onClick={handleDelete}
              disabled={deleting}
              className="p-2 rounded hover:bg-red-500/10 text-[color:var(--color-text-muted)] hover:text-red-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              title={t('sources.delete', 'Удалить')}
            >
              {deleting ? (
                <div className="w-4 h-4 border-2 border-red-500 border-t-transparent rounded-full animate-spin" />
              ) : (
                <Trash2 className="w-4 h-4" />
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

export default SourceCard
