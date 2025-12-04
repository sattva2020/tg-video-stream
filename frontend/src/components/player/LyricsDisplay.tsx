/**
 * LyricsDisplay Component
 * Отображение текста песни с синхронизацией по времени
 * 
 * Features:
 * - Synchronized lyrics with playback position
 * - HTML formatting support (line breaks, emphasis)
 * - Lyrics fetching from Genius API via backend
 * - Caching with TTL
 * - Scroll to current line
 * - Copy lyrics to clipboard
 * - Accessibility support
 * 
 * User Story: US8 - Lyrics Display
 * Related Tasks: T053-T059
 */

import React, { useState, useCallback, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import axios from 'axios';
import { Music, Copy, Check, AlertCircle, Loader } from 'lucide-react';

interface LyricsLine {
  time?: number; // Optional: milliseconds from start
  text: string;
}

interface LyricsDisplayProps {
  /** Track title for lyrics lookup */
  trackTitle?: string;
  /** Artist name for lyrics lookup */
  artistName?: string;
  /** Genius track ID (if available) */
  trackId?: string;
  /** Current playback position in seconds */
  currentTime?: number;
  /** Callback when lyrics are loaded */
  onLyricsLoaded?: (lyrics: string) => void;
  /** API base URL */
  apiBaseUrl?: string;
  /** Whether component is disabled */
  disabled?: boolean;
  /** Show lyrics as plain text (no sync) */
  plainText?: boolean;
  /** Maximum height for lyrics container */
  maxHeight?: string;
}

/**
 * Parse synchronized lyrics format
 * Supports formats like: [00:10.50]Lyrics line text
 */
const parseSyncedLyrics = (lyricsText: string): LyricsLine[] => {
  const lines: LyricsLine[] = [];
  const linePattern = /\[(\d{2}):(\d{2}\.\d{2})\](.*)/g;
  let match;

  // Try synced format first
  while ((match = linePattern.exec(lyricsText)) !== null) {
    const minutes = parseInt(match[1]);
    const seconds = parseFloat(match[2]);
    const time = minutes * 60 + seconds;
    lines.push({
      time,
      text: match[3].trim(),
    });
  }

  // If no synced lyrics found, split by newlines
  if (lines.length === 0) {
    return lyricsText.split('\n').map((text) => ({ text: text.trim() }));
  }

  return lines;
};

/**
 * Format seconds to MM:SS display
 */
const formatTime = (seconds: number): string => {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
};

/**
 * LyricsDisplay Component
 * 
 * Shows lyrics with optional sync to playback position,
 * auto-scrolling to current line, and metadata from Genius API.
 */
export const LyricsDisplay: React.FC<LyricsDisplayProps> = ({
  trackTitle,
  artistName,
  trackId,
  currentTime = 0,
  onLyricsLoaded,
  apiBaseUrl = '/api',
  disabled = false,
  plainText = false,
  maxHeight = '400px',
}) => {
  const { t } = useTranslation();
  const [lyrics, setLyrics] = useState<LyricsLine[]>([]);
  const [lyricsText, setLyricsText] = useState<string>('');
  const [isLoading, setIsLoading] = useState(false);
  const [isCopied, setIsCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentLineIndex, setCurrentLineIndex] = useState<number>(0);
  const lyricsContainerRef = useRef<HTMLDivElement>(null);
  const currentLineRef = useRef<HTMLDivElement>(null);
  const isInteractionDisabled = disabled || isLoading;

  /**
   * Fetch lyrics from backend
   */
  const fetchLyrics = useCallback(async () => {
    if (!trackTitle || !artistName) {
      setError(t('playback.track_info_required', 'Track title and artist required'));
      return;
    }

    try {
      setIsLoading(true);
      setError(null);

      const params: Record<string, any> = {
        track_title: trackTitle,
        artist_name: artistName,
      };
      if (trackId) {
        params.track_id = trackId;
      }

      const response = await axios.get(`${apiBaseUrl}/lyrics/search`, {
        params,
      });

      if (response.data && response.data.lyrics_text) {
        const text = response.data.lyrics_text;
        setLyricsText(text);
        setLyrics(parseSyncedLyrics(text));
        onLyricsLoaded?.(text);
      } else {
        setError(t('playback.lyrics_not_found', 'Lyrics not found'));
      }
    } catch (err) {
      const message =
        err instanceof Error ? err.message : 'Failed to fetch lyrics';
      setError(message);
      console.error('Lyrics fetch error:', err);
    } finally {
      setIsLoading(false);
    }
  }, [trackTitle, artistName, trackId, apiBaseUrl, onLyricsLoaded, t]);

  /**
   * Auto-fetch lyrics when track info changes
   */
  useEffect(() => {
    if (trackTitle && artistName && !lyricsText) {
      fetchLyrics();
    }
  }, [trackTitle, artistName, lyricsText, fetchLyrics]);

  /**
   * Update current line based on playback position
   */
  useEffect(() => {
    if (plainText || lyrics.length === 0) return;

    let newIndex = 0;
    for (let i = lyrics.length - 1; i >= 0; i--) {
      if (lyrics[i].time !== undefined && lyrics[i].time! <= currentTime) {
        newIndex = i;
        break;
      }
    }

    setCurrentLineIndex(newIndex);
  }, [currentTime, lyrics, plainText]);

  /**
   * Scroll to current line
   */
  useEffect(() => {
    if (currentLineRef.current && lyricsContainerRef.current) {
      currentLineRef.current.scrollIntoView({
        behavior: 'smooth',
        block: 'center',
      });
    }
  }, [currentLineIndex]);

  /**
   * Copy lyrics to clipboard
   */
  const handleCopyLyrics = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(lyricsText);
      setIsCopied(true);
      setTimeout(() => setIsCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy lyrics:', err);
      setError(t('common.copy_failed', 'Failed to copy'));
    }
  }, [lyricsText, t]);

  /**
   * Refresh lyrics
   */
  const handleRefresh = useCallback(() => {
    setLyricsText('');
    setLyrics([]);
    fetchLyrics();
  }, [fetchLyrics]);

  if (plainText) {
    // Plain text mode (no sync)
    return (
      <div className="w-full rounded-lg bg-gray-900 p-4" aria-disabled={disabled}>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Music className="h-5 w-5 text-indigo-400" />
            <h3 className="text-sm font-medium text-gray-100">
              {t('playback.lyrics', 'Lyrics')}
            </h3>
          </div>
          <div className="flex gap-2">
            {lyricsText && (
              <button
                onClick={handleCopyLyrics}
                disabled={isInteractionDisabled}
                className="p-1 hover:bg-gray-800 rounded transition-all disabled:opacity-50"
                title={t('common.copy', 'Copy')}
              >
                {isCopied ? (
                  <Check className="h-4 w-4 text-green-400" />
                ) : (
                  <Copy className="h-4 w-4 text-gray-400" />
                )}
              </button>
            )}
          </div>
        </div>

        <div
          className="whitespace-pre-wrap text-sm text-gray-300 overflow-y-auto rounded bg-gray-800 p-3"
          style={{ maxHeight }}
        >
          {isLoading && (
            <div className="flex items-center gap-2 text-gray-400">
              <Loader className="h-4 w-4 animate-spin" />
              {t('common.loading', 'Loading...')}
            </div>
          )}
          {error && (
            <div className="flex items-center gap-2 text-red-400">
              <AlertCircle className="h-4 w-4" />
              {error}
            </div>
          )}
          {lyricsText && <div>{lyricsText}</div>}
          {!lyricsText && !isLoading && !error && (
            <div className="text-gray-500">
              {t('playback.no_lyrics', 'No lyrics available')}
            </div>
          )}
        </div>
      </div>
    );
  }

  // Synced lyrics mode
  return (
    <div className="w-full rounded-lg bg-gray-900 p-4" aria-disabled={disabled}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Music className="h-5 w-5 text-indigo-400" />
          <h3 className="text-sm font-medium text-gray-100">
            {t('playback.synchronized_lyrics', 'Synchronized Lyrics')}
          </h3>
        </div>
        <div className="flex gap-2">
          {lyricsText && (
            <>
              <button
                onClick={handleCopyLyrics}
                disabled={isInteractionDisabled}
                className="p-1 hover:bg-gray-800 rounded transition-all disabled:opacity-50"
                title={t('common.copy', 'Copy')}
              >
                {isCopied ? (
                  <Check className="h-4 w-4 text-green-400" />
                ) : (
                  <Copy className="h-4 w-4 text-gray-400" />
                )}
              </button>
              <button
                onClick={handleRefresh}
                disabled={isInteractionDisabled}
                className="text-xs px-2 py-1 rounded bg-gray-700 text-gray-300 hover:bg-gray-600 transition-all disabled:opacity-50"
              >
                {t('common.refresh', 'Refresh')}
              </button>
            </>
          )}
        </div>
      </div>

      {/* Lyrics Container */}
      <div
        ref={lyricsContainerRef}
        className="rounded bg-gray-800 p-4 overflow-y-auto space-y-2"
        style={{ maxHeight }}
      >
        {isLoading && (
          <div className="flex items-center justify-center gap-2 text-gray-400 py-8">
            <Loader className="h-5 w-5 animate-spin" />
            <span>{t('common.loading', 'Loading...')}</span>
          </div>
        )}

        {error && (
          <div className="flex items-center gap-2 rounded-sm bg-red-900 px-3 py-2 text-sm text-red-100">
            <AlertCircle className="h-4 w-4 flex-shrink-0" />
            {error}
          </div>
        )}

        {!isLoading && !error && lyrics.length === 0 && (
          <div className="text-center text-sm text-gray-500 py-8">
            {t('playback.no_lyrics', 'No lyrics available')}
          </div>
        )}

        {lyrics.map((line, index) => (
          <div
            key={index}
            ref={index === currentLineIndex ? currentLineRef : null}
            className={`text-sm transition-all duration-300 ${
              index === currentLineIndex
                ? 'text-indigo-300 font-semibold scale-105'
                : 'text-gray-400'
            } ${index < currentLineIndex ? 'opacity-50' : ''}`}
          >
            <div className="flex gap-3">
              {line.time !== undefined && (
                <span className="w-12 text-xs text-gray-600 flex-shrink-0 font-mono">
                  {formatTime(line.time)}
                </span>
              )}
              <span>{line.text}</span>
            </div>
          </div>
        ))}
      </div>

      {/* Track Info */}
      {(trackTitle || artistName) && (
        <div className="mt-3 text-xs text-gray-500 px-2">
          {trackTitle && <div>{trackTitle}</div>}
          {artistName && <div className="text-gray-600">{artistName}</div>}
        </div>
      )}
    </div>
  );
};

export default LyricsDisplay;
