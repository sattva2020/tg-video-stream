import React, { useState, useEffect } from 'react';
import { Settings, Film, Music, Monitor, Sliders, AlertCircle, Info, Check } from 'lucide-react';
import { useTranslation } from 'react-i18next';

// === Types ===

export type VideoCodec = 'h264' | 'h265' | 'vp9';
export type AudioCodec = 'aac' | 'mp3' | 'opus';
export type QualityPreset = 'low' | 'medium' | 'high' | 'ultra' | 'custom';

export interface EncodingProfile {
  video_codec?: VideoCodec;
  audio_codec?: AudioCodec;
  video_bitrate?: number;
  audio_bitrate?: number;
  resolution?: string;
  custom_ffmpeg_args?: string;
}

export interface EncodingProfileFormProps {
  /** Initial profile values */
  initialProfile?: EncodingProfile;
  /** Callback when profile changes */
  onChange?: (profile: EncodingProfile) => void;
  /** Callback when form is validated */
  onValidationChange?: (isValid: boolean, errors: string[]) => void;
  /** Show advanced options */
  showAdvanced?: boolean;
  /** CSS class name */
  className?: string;
}

// === Quality Presets Configuration ===

const QUALITY_PRESETS: Record<QualityPreset, {
  label: string;
  description: string;
  video_bitrate: number;
  audio_bitrate: number;
  resolution: string;
}> = {
  low: {
    label: 'Low',
    description: '480p, 1 Mbps - Minimal bandwidth',
    video_bitrate: 1000,
    audio_bitrate: 96,
    resolution: '854x480',
  },
  medium: {
    label: 'Medium',
    description: '720p, 2.5 Mbps - Balanced quality',
    video_bitrate: 2500,
    audio_bitrate: 128,
    resolution: '1280x720',
  },
  high: {
    label: 'High',
    description: '1080p, 4 Mbps - Good quality',
    video_bitrate: 4000,
    audio_bitrate: 128,
    resolution: '1920x1080',
  },
  ultra: {
    label: 'Ultra',
    description: '1080p, 6 Mbps - Best quality',
    video_bitrate: 6000,
    audio_bitrate: 192,
    resolution: '1920x1080',
  },
  custom: {
    label: 'Custom',
    description: 'Manual configuration',
    video_bitrate: 2500,
    audio_bitrate: 128,
    resolution: '1920x1080',
  },
};

// === Video Codecs ===

const VIDEO_CODECS: Array<{ value: VideoCodec; label: string; description: string }> = [
  {
    value: 'h264',
    label: 'H.264 (AVC)',
    description: 'Best compatibility, good compression',
  },
  {
    value: 'h265',
    label: 'H.265 (HEVC)',
    description: 'Better compression, more CPU',
  },
  {
    value: 'vp9',
    label: 'VP9',
    description: 'Open source, good quality',
  },
];

// === Audio Codecs ===

const AUDIO_CODECS: Array<{ value: AudioCodec; label: string; description: string }> = [
  {
    value: 'aac',
    label: 'AAC',
    description: 'Best compatibility',
  },
  {
    value: 'mp3',
    label: 'MP3',
    description: 'Universal support',
  },
  {
    value: 'opus',
    label: 'Opus',
    description: 'Best quality, modern',
  },
];

// === Resolutions ===

const RESOLUTIONS = [
  { value: '854x480', label: '480p (SD)' },
  { value: '1280x720', label: '720p (HD)' },
  { value: '1920x1080', label: '1080p (Full HD)' },
  { value: '2560x1440', label: '1440p (2K)' },
  { value: '3840x2160', label: '2160p (4K)' },
];

// === Validation ===

function validateProfile(profile: EncodingProfile): string[] {
  const errors: string[] = [];

  // Validate video bitrate
  if (profile.video_bitrate !== undefined) {
    if (profile.video_bitrate < 500) {
      errors.push('Video bitrate must be at least 500 kbps');
    }
    if (profile.video_bitrate > 20000) {
      errors.push('Video bitrate must not exceed 20000 kbps');
    }
  }

  // Validate audio bitrate
  if (profile.audio_bitrate !== undefined) {
    if (profile.audio_bitrate < 64) {
      errors.push('Audio bitrate must be at least 64 kbps');
    }
    if (profile.audio_bitrate > 320) {
      errors.push('Audio bitrate must not exceed 320 kbps');
    }
  }

  // Validate resolution format
  if (profile.resolution) {
    const resolutionRegex = /^\d+x\d+$/;
    if (!resolutionRegex.test(profile.resolution)) {
      errors.push('Resolution must be in format WIDTHxHEIGHT (e.g., 1920x1080)');
    }
  }

  return errors;
}

// === Component ===

export const EncodingProfileForm: React.FC<EncodingProfileFormProps> = ({
  initialProfile = {},
  onChange,
  onValidationChange,
  showAdvanced = false,
  className = '',
}) => {
  const { t } = useTranslation();

  // State
  const [profile, setProfile] = useState<EncodingProfile>(initialProfile);
  const [qualityPreset, setQualityPreset] = useState<QualityPreset>('medium');
  const [errors, setErrors] = useState<string[]>([]);
  const [touched, setTouched] = useState<Set<string>>(new Set());

  // Compute validation
  useEffect(() => {
    const validationErrors = validateProfile(profile);
    setErrors(validationErrors);
    onValidationChange?.(validationErrors.length === 0, validationErrors);
  }, [profile, onValidationChange]);

  // Handle quality preset change
  const handlePresetChange = (preset: QualityPreset) => {
    setQualityPreset(preset);

    if (preset !== 'custom') {
      const config = QUALITY_PRESETS[preset];
      const newProfile = {
        ...profile,
        video_bitrate: config.video_bitrate,
        audio_bitrate: config.audio_bitrate,
        resolution: config.resolution,
      };
      setProfile(newProfile);
      onChange?.(newProfile);
    }
  };

  // Handle field change
  const handleFieldChange = <K extends keyof EncodingProfile>(
    field: K,
    value: EncodingProfile[K]
  ) => {
    const newProfile = { ...profile, [field]: value };
    setProfile(newProfile);

    // If user manually changes a field, switch to custom preset
    if (
      (field === 'video_bitrate' || field === 'audio_bitrate' || field === 'resolution') &&
      qualityPreset !== 'custom'
    ) {
      setQualityPreset('custom');
    }

    onChange?.(newProfile);
    setTouched(prev => new Set(prev).add(field));
  };

  // Format bitrate display
  const formatBitrate = (kbps?: number) => {
    if (kbps === undefined) return '';
    if (kbps >= 1000) {
      return `${(kbps / 1000).toFixed(1)} Mbps`;
    }
    return `${kbps} kbps`;
  };

  const isValid = errors.length === 0;

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Quality Presets */}
      <div>
        <label className="flex items-center gap-2 text-sm font-medium text-[color:var(--color-text)] mb-2">
          <Sliders className="w-4 h-4" />
          {t('encoding.qualityPreset', 'Quality Preset')}
        </label>
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
          {(Object.keys(QUALITY_PRESETS) as Array<QualityPreset>).map((preset) => (
            <button
              key={preset}
              type="button"
              onClick={() => handlePresetChange(preset)}
              className={`
                px-3 py-2 rounded-lg text-sm font-medium transition-all
                ${
                  qualityPreset === preset
                    ? 'bg-[color:var(--color-accent)] text-white shadow-md'
                    : 'bg-[color:var(--color-surface-muted)] text-[color:var(--color-text)] hover:bg-[color:var(--color-border)]'
                }
              `}
              title={QUALITY_PRESETS[preset].description}
            >
              {QUALITY_PRESETS[preset].label}
            </button>
          ))}
        </div>
        {qualityPreset !== 'custom' && (
          <p className="text-xs text-[color:var(--color-text-muted)] mt-1">
            {QUALITY_PRESETS[qualityPreset].description}
          </p>
        )}
      </div>

      {/* Video Codec */}
      <div>
        <label className="flex items-center gap-2 text-sm font-medium text-[color:var(--color-text)] mb-2">
          <Film className="w-4 h-4" />
          {t('encoding.videoCodec', 'Video Codec')}
        </label>
        <select
          className="w-full px-3 py-2 border border-[color:var(--color-border)] bg-[color:var(--color-surface)] text-[color:var(--color-text)] rounded-lg text-sm"
          value={profile.video_codec || 'h264'}
          onChange={(e) => handleFieldChange('video_codec', e.target.value as VideoCodec)}
        >
          {VIDEO_CODECS.map((codec) => (
            <option key={codec.value} value={codec.value}>
              {codec.label} - {codec.description}
            </option>
          ))}
        </select>
      </div>

      {/* Audio Codec */}
      <div>
        <label className="flex items-center gap-2 text-sm font-medium text-[color:var(--color-text)] mb-2">
          <Music className="w-4 h-4" />
          {t('encoding.audioCodec', 'Audio Codec')}
        </label>
        <select
          className="w-full px-3 py-2 border border-[color:var(--color-border)] bg-[color:var(--color-surface)] text-[color:var(--color-text)] rounded-lg text-sm"
          value={profile.audio_codec || 'aac'}
          onChange={(e) => handleFieldChange('audio_codec', e.target.value as AudioCodec)}
        >
          {AUDIO_CODECS.map((codec) => (
            <option key={codec.value} value={codec.value}>
              {codec.label} - {codec.description}
            </option>
          ))}
        </select>
      </div>

      {/* Video Bitrate */}
      <div>
        <label className="flex items-center gap-2 text-sm font-medium text-[color:var(--color-text)] mb-2">
          <Settings className="w-4 h-4" />
          {t('encoding.videoBitrate', 'Video Bitrate')}
        </label>
        <div className="flex gap-2">
          <input
            type="number"
            min="500"
            max="20000"
            step="100"
            className="flex-1 px-3 py-2 border border-[color:var(--color-border)] bg-[color:var(--color-surface)] text-[color:var(--color-text)] rounded-lg text-sm"
            value={profile.video_bitrate || ''}
            onChange={(e) => handleFieldChange('video_bitrate', e.target.value ? parseInt(e.target.value) : undefined)}
            placeholder={t('encoding.videoBitratePlaceholder', '2500')}
          />
          <span className="px-3 py-2 bg-[color:var(--color-surface-muted)] text-[color:var(--color-text-muted)] rounded-lg text-sm whitespace-nowrap">
            {formatBitrate(profile.video_bitrate) || 'kbps'}
          </span>
        </div>
      </div>

      {/* Audio Bitrate */}
      <div>
        <label className="flex items-center gap-2 text-sm font-medium text-[color:var(--color-text)] mb-2">
          <Settings className="w-4 h-4" />
          {t('encoding.audioBitrate', 'Audio Bitrate')}
        </label>
        <div className="flex gap-2">
          <input
            type="number"
            min="64"
            max="320"
            step="32"
            className="flex-1 px-3 py-2 border border-[color:var(--color-border)] bg-[color:var(--color-surface)] text-[color:var(--color-text)] rounded-lg text-sm"
            value={profile.audio_bitrate || ''}
            onChange={(e) => handleFieldChange('audio_bitrate', e.target.value ? parseInt(e.target.value) : undefined)}
            placeholder={t('encoding.audioBitratePlaceholder', '128')}
          />
          <span className="px-3 py-2 bg-[color:var(--color-surface-muted)] text-[color:var(--color-text-muted)] rounded-lg text-sm whitespace-nowrap">
            {formatBitrate(profile.audio_bitrate) || 'kbps'}
          </span>
        </div>
      </div>

      {/* Resolution */}
      <div>
        <label className="flex items-center gap-2 text-sm font-medium text-[color:var(--color-text)] mb-2">
          <Monitor className="w-4 h-4" />
          {t('encoding.resolution', 'Resolution')}
        </label>
        <div className="flex gap-2">
          <select
            className="flex-1 px-3 py-2 border border-[color:var(--color-border)] bg-[color:var(--color-surface)] text-[color:var(--color-text)] rounded-lg text-sm"
            value={profile.resolution || ''}
            onChange={(e) => handleFieldChange('resolution', e.target.value || undefined)}
          >
            <option value="">{t('encoding.selectResolution', 'Select...')}</option>
            {RESOLUTIONS.map((res) => (
              <option key={res.value} value={res.value}>
                {res.label}
              </option>
            ))}
          </select>
          <input
            type="text"
            pattern="^\d+x\d+$"
            className="w-32 px-3 py-2 border border-[color:var(--color-border)] bg-[color:var(--color-surface)] text-[color:var(--color-text)] rounded-lg text-sm"
            value={profile.resolution || ''}
            onChange={(e) => handleFieldChange('resolution', e.target.value || undefined)}
            placeholder={t('encoding.customResolution', '1920x1080')}
          />
        </div>
      </div>

      {/* Custom FFmpeg Args */}
      {(showAdvanced || profile.custom_ffmpeg_args) && (
        <div>
          <label className="flex items-center gap-2 text-sm font-medium text-[color:var(--color-text)] mb-2">
            <Settings className="w-4 h-4" />
            {t('encoding.customArgs', 'Custom FFmpeg Args')}
            <Info className="w-3 h-3 text-[color:var(--color-text-muted)]" />
          </label>
          <input
            type="text"
            className="w-full px-3 py-2 border border-[color:var(--color-border)] bg-[color:var(--color-surface)] text-[color:var(--color-text)] rounded-lg text-sm font-mono"
            value={profile.custom_ffmpeg_args || ''}
            onChange={(e) => handleFieldChange('custom_ffmpeg_args', e.target.value || undefined)}
            placeholder={t('encoding.customArgsPlaceholder', '-preset fast -tune zerolatency')}
          />
          <p className="text-xs text-[color:var(--color-text-muted)] mt-1">
            {t('encoding.customArgsHint', 'Optional: Additional FFmpeg parameters (advanced)')}
          </p>
        </div>
      )}

      {/* Validation Errors */}
      {!isValid && touched.size > 0 && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3">
          <div className="flex items-start gap-2">
            <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="text-sm font-medium text-red-500">
                {t('encoding.validationError', 'Configuration Issues')}
              </p>
              <ul className="mt-1 space-y-1">
                {errors.map((error, idx) => (
                  <li key={idx} className="text-xs text-red-400">
                    • {error}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Success Indicator */}
      {isValid && touched.size > 0 && (
        <div className="bg-green-500/10 border border-green-500/20 rounded-lg p-3">
          <div className="flex items-center gap-2 text-sm text-green-500">
            <Check className="w-4 h-4" />
            <span>{t('encoding.validConfiguration', 'Configuration is valid')}</span>
          </div>
        </div>
      )}

      {/* Info Box */}
      {profile.video_codec === 'h265' && (
        <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-3">
          <div className="flex items-start gap-2">
            <Info className="w-4 h-4 text-blue-500 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-blue-500">
                {t('encoding.h265Warning', 'H.265 Warning')}
              </p>
              <p className="text-xs text-blue-400 mt-1">
                {t('encoding.h265WarningHint', 'H.265 provides better compression but requires more CPU power. Ensure your server can handle it.')}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default EncodingProfileForm;
