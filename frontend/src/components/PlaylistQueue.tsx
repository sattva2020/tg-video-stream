import React, { useCallback, useEffect, useState, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import type { PlaylistItem } from '../services/playlist'
import * as playlistService from '../services/playlist'
import { usePlaylistWebSocket } from '../hooks/usePlaylistWebSocket'
import { useToast } from '../hooks/useToast'
import { SkeletonPlaylistQueue } from './ui/Skeleton'

export const POLL_INTERVAL_MS = 5000 // Increased from 3s to 5s
const MAX_CONSECUTIVE_ERRORS = 3
const MAX_BACKOFF_MS = 60000 // Max 1 minute between retries

interface PlaylistQueueProps {
  channelId?: string;
}

const PlaylistQueue: React.FC<PlaylistQueueProps> = ({ channelId }) => {
  const { t } = useTranslation()
  const [loading, setLoading] = useState(false)
  const toast = useToast()
  
  // Use WebSocket for real-time updates
  const { 
    items, 
    isConnected, 
    refresh,
    lastEvent 
  } = usePlaylistWebSocket({
    channelId,
    enabled: true,
  })

  // Show toast notifications for WebSocket events
  useEffect(() => {
    if (!lastEvent) return
    
    switch (lastEvent.type) {
      case 'item_added':
        toast.success(`Трек добавлен: ${lastEvent.item?.title || 'Новый трек'}`)
        break
      case 'item_removed':
        toast.info('Трек удалён из очереди')
        break
      case 'stream_started':
        toast.success('Трансляция запущена')
        break
      case 'stream_stopped':
        toast.warning('Трансляция остановлена')
        break
      case 'track_playing':
        // Optionally show current track
        if (lastEvent.item?.title) {
          toast.info(`▶ Сейчас играет: ${lastEvent.item.title}`)
        }
        break
    }
  }, [lastEvent, toast])

  // Fallback to polling if WebSocket is not connected
  const [fallbackItems, setFallbackItems] = useState<PlaylistItem[]>([])
  const errorCountRef = useRef(0)
  const backoffRef = useRef(POLL_INTERVAL_MS)
  
  const fetch = useCallback(async () => {
    if (isConnected) {
      // Reset error state when WebSocket reconnects
      errorCountRef.current = 0
      backoffRef.current = POLL_INTERVAL_MS
      return
    }
    
    // Stop polling after too many consecutive errors
    if (errorCountRef.current >= MAX_CONSECUTIVE_ERRORS) {
      console.warn('[PlaylistQueue] Polling paused due to consecutive errors')
      return
    }
    
    setLoading(true)
    try {
      const data = await playlistService.getPlaylist(channelId)
      setFallbackItems(data)
      // Reset on success
      errorCountRef.current = 0
      backoffRef.current = POLL_INTERVAL_MS
    } catch (e) {
      console.error('Failed to fetch playlist', e)
      errorCountRef.current++
      // Exponential backoff: 5s -> 10s -> 20s -> 40s -> 60s max
      backoffRef.current = Math.min(backoffRef.current * 2, MAX_BACKOFF_MS)
      if (errorCountRef.current === 1) {
        toast.error('Не удалось загрузить плейлист')
      }
    } finally {
      setLoading(false)
    }
  }, [channelId, isConnected, toast])

  useEffect(() => {
    if (isConnected) return // Don't poll when WebSocket is connected
    
    // Initial fetch
    fetch()
    
    // Setup polling with dynamic interval based on backoff
    let timeoutId: NodeJS.Timeout
    const scheduleNext = () => {
      timeoutId = setTimeout(() => {
        fetch().finally(() => {
          if (!isConnected && errorCountRef.current < MAX_CONSECUTIVE_ERRORS) {
            scheduleNext()
          }
        })
      }, backoffRef.current)
    }
    scheduleNext()
    
    return () => clearTimeout(timeoutId)
  }, [isConnected, fetch])

  // Use WebSocket items if connected, otherwise use fallback
  const displayItems = isConnected ? items : fallbackItems

  return (
    <div className="bg-[color:var(--color-panel)] shadow rounded-lg p-6 mt-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-[color:var(--color-text)]">{t('playlist.currentQueue', 'Текущая очередь')}</h3>
        <div className="flex items-center gap-2">
          {isConnected ? (
            <span className="flex items-center gap-1 text-xs text-green-500">
              <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
              {t('playlist.live', 'Live')}
            </span>
          ) : (
            <span className="flex items-center gap-1 text-xs text-yellow-500">
              <span className="w-2 h-2 bg-yellow-500 rounded-full" />
              {t('playlist.polling', 'Polling')}
            </span>
          )}
          <button 
            onClick={refresh}
            className="text-xs text-[color:var(--color-text-muted)] hover:text-[color:var(--color-text)] transition-colors"
            title="Refresh"
          >
            ↻
          </button>
        </div>
      </div>
      {loading && !isConnected && <SkeletonPlaylistQueue itemCount={3} />}
      <ul className="space-y-2">
        {displayItems.length === 0 && <li className="text-[color:var(--color-text-muted)]">{t('playlist.emptyQueue', 'Треки отсутствуют')}</li>}
        {displayItems.map((it) => (
          <li 
            key={it.id} 
            className={`p-3 border rounded-lg flex justify-between items-center transition-colors ${
              it.status === 'playing' 
                ? 'bg-blue-500/10 border-blue-500/30' 
                : 'bg-[color:var(--color-surface-muted)] border-[color:var(--color-outline)]'
            }`}
          >
            <div className="truncate">
              <div className="flex items-center gap-2">
                <strong className="truncate w-64 text-[color:var(--color-text)]">{it.title || it.url}</strong>
                <span className="text-xs text-[color:var(--color-text-muted)]">{it.type.toUpperCase()}</span>
              </div>
              <div className="text-xs text-[color:var(--color-text-muted)] truncate">{it.url}</div>
            </div>
            <div className="text-right text-xs text-[color:var(--color-text-muted)]">
              {it.duration ? `${Math.floor(it.duration/60)}:${String(it.duration%60).padStart(2,'0')}` : '—'}
              <div className={`text-xxs ${
                it.status === 'playing' ? 'text-blue-400' : 
                it.status === 'error' ? 'text-red-400' : 
                'text-[color:var(--color-text-muted)]'
              }`}>
                {it.status === 'playing' && '▶ '}
                {it.status}
              </div>
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}

export default PlaylistQueue
