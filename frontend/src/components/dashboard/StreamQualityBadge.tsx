/**
 * Feature 022 Phase 2: Stream Quality Badge Component
 * 
 * Отображает информацию о качестве потока в виде красивого бейджа
 * с цветовой кодировкой уровней качества и детальными метриками.
 */

import React, { useState } from 'react';
import { StreamQualityResponse } from '../../api/admin';

interface StreamQualityBadgeProps {
  quality?: StreamQualityResponse | null;
  loading?: boolean;
  error?: string | null;
  compact?: boolean;  // Компактный вид (только бейдж без деталей)
}

export const StreamQualityBadge: React.FC<StreamQualityBadgeProps> = ({
  quality,
  loading = false,
  error = null,
  compact = false,
}) => {
  const [showDetails, setShowDetails] = useState(false);

  if (loading) {
    return (
      <div className="inline-flex items-center px-3 py-1 rounded-full bg-gray-100 text-gray-600 text-sm">
        <div className="animate-spin h-3 w-3 border-2 border-gray-400 border-t-transparent rounded-full mr-2" />
        Analyzing...
      </div>
    );
  }

  if (error) {
    return (
      <div className="inline-flex items-center px-3 py-1 rounded-full bg-red-100 text-red-700 text-sm font-medium">
        <span className="mr-1">⚠️</span>
        Analysis Error
      </div>
    );
  }

  if (!quality) {
    return (
      <div className="inline-flex items-center px-3 py-1 rounded-full bg-gray-100 text-gray-600 text-sm">
        No Data
      </div>
    );
  }

  // Определяем цвет и иконку в зависимости от качества
  const getQualityStyle = (qualityLevel: string) => {
    switch (qualityLevel) {
      case 'lossless':
      case 'ultra':
        return {
          bg: 'bg-green-100',
          text: 'text-green-800',
          border: 'border-green-300',
          icon: '🎬',
        };
      case 'high':
        return {
          bg: 'bg-blue-100',
          text: 'text-blue-800',
          border: 'border-blue-300',
          icon: '📺',
        };
      case 'medium':
        return {
          bg: 'bg-yellow-100',
          text: 'text-yellow-800',
          border: 'border-yellow-300',
          icon: '📻',
        };
      case 'low':
        return {
          bg: 'bg-orange-100',
          text: 'text-orange-800',
          border: 'border-orange-300',
          icon: '📱',
        };
      default:
        return {
          bg: 'bg-gray-100',
          text: 'text-gray-800',
          border: 'border-gray-300',
          icon: '❓',
        };
    }
  };

  const qualityStyle = getQualityStyle(quality.overall_quality);

  if (compact) {
    return (
      <div
        className={`inline-flex items-center px-3 py-1 rounded-full border ${qualityStyle.bg} ${qualityStyle.text} text-sm font-medium cursor-pointer hover:shadow-md transition-shadow`}
        onClick={() => setShowDetails(!showDetails)}
        title={`Click to ${showDetails ? 'hide' : 'show'} details`}
      >
        <span className="mr-1">{qualityStyle.icon}</span>
        {quality.overall_quality.toUpperCase()}
      </div>
    );
  }

  // Full view
  return (
    <div className="space-y-2">
      {/* Main Badge */}
      <div
        className={`inline-flex items-center px-4 py-2 rounded-lg border-2 ${qualityStyle.bg} ${qualityStyle.text} font-semibold cursor-pointer hover:shadow-lg transition-shadow`}
        onClick={() => setShowDetails(!showDetails)}
      >
        <span className="text-xl mr-2">{qualityStyle.icon}</span>
        <span>{quality.overall_quality.toUpperCase()} Quality</span>
        <span className="ml-2 text-xs opacity-70">
          {showDetails ? '▼' : '▶'}
        </span>
      </div>

      {/* Detailed Metrics */}
      {showDetails && (
        <div className={`mt-3 p-4 rounded-lg border ${qualityStyle.border} ${qualityStyle.bg} space-y-3`}>
          {/* Audio Metrics */}
          {quality.audio && (
            <div className="space-y-1">
              <h4 className="font-semibold text-sm flex items-center">
                <span className="mr-2">🔊</span>
                Audio
              </h4>
              <div className="ml-6 space-y-0.5 text-sm">
                {quality.audio.codec && (
                  <div>
                    <span className="font-medium">Codec:</span> {quality.audio.codec.toUpperCase()}
                  </div>
                )}
                {quality.audio.bitrate_kbps && (
                  <div>
                    <span className="font-medium">Bitrate:</span> {quality.audio.bitrate_kbps} kbps
                  </div>
                )}
                {quality.audio.sample_rate_hz && (
                  <div>
                    <span className="font-medium">Sample Rate:</span> {quality.audio.sample_rate_hz / 1000} kHz
                  </div>
                )}
                {quality.audio.channels && (
                  <div>
                    <span className="font-medium">Channels:</span> {quality.audio.channels}
                  </div>
                )}
                {quality.audio.quality && (
                  <div>
                    <span className="font-medium">Quality:</span>{' '}
                    <span className="inline-block px-2 py-0.5 bg-white rounded text-xs font-medium">
                      {quality.audio.quality}
                    </span>
                  </div>
                )}
                {quality.audio.duration_sec && (
                  <div>
                    <span className="font-medium">Duration:</span> {Math.round(quality.audio.duration_sec)}s
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Video Metrics */}
          {quality.video && (
            <div className="space-y-1 border-t border-opacity-30 pt-3">
              <h4 className="font-semibold text-sm flex items-center">
                <span className="mr-2">📹</span>
                Video
              </h4>
              <div className="ml-6 space-y-0.5 text-sm">
                {quality.video.codec && (
                  <div>
                    <span className="font-medium">Codec:</span> {quality.video.codec.toUpperCase()}
                  </div>
                )}
                {quality.video.resolution && (
                  <div>
                    <span className="font-medium">Resolution:</span> {quality.video.resolution}
                  </div>
                )}
                {quality.video.bitrate_kbps && (
                  <div>
                    <span className="font-medium">Bitrate:</span> {quality.video.bitrate_kbps} kbps
                  </div>
                )}
                {quality.video.fps && (
                  <div>
                    <span className="font-medium">FPS:</span> {quality.video.fps.toFixed(1)}
                  </div>
                )}
                {quality.video.quality && (
                  <div>
                    <span className="font-medium">Quality:</span>{' '}
                    <span className="inline-block px-2 py-0.5 bg-white rounded text-xs font-medium">
                      {quality.video.quality}
                    </span>
                  </div>
                )}
                {quality.video.duration_sec && (
                  <div>
                    <span className="font-medium">Duration:</span> {Math.round(quality.video.duration_sec)}s
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Stream Info */}
          <div className="border-t border-opacity-30 pt-3 text-xs opacity-70 space-y-1">
            <div>
              {quality.is_audio_only && <span className="inline-block px-2 py-0.5 bg-white rounded mr-1">Audio Only</span>}
              {quality.is_video_only && <span className="inline-block px-2 py-0.5 bg-white rounded mr-1">Video Only</span>}
              {quality.has_both && <span className="inline-block px-2 py-0.5 bg-white rounded mr-1">Audio + Video</span>}
            </div>
            <div className="truncate">
              <span className="font-medium">URL:</span> {quality.url}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default StreamQualityBadge;
