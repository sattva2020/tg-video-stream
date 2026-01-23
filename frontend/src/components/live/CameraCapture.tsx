import React, { useState, useRef, useEffect } from 'react';
import {
  Video,
  VideoOff,
  Mic,
  MicOff,
  Loader2,
  AlertCircle,
  Settings,
  Check
} from 'lucide-react';
import { useTranslation } from 'react-i18next';

export interface MediaStreamConfig {
  video: boolean | { deviceId: string; width?: number; height?: number };
  audio: boolean | { deviceId: string };
}

export interface CameraCaptureProps {
  onStreamReady?: (stream: MediaStream) => void;
  onStreamError?: (error: Error) => void;
  className?: string;
}

type MediaPermissionState = 'idle' | 'requesting' | 'granted' | 'denied' | 'error';

export const CameraCapture: React.FC<CameraCaptureProps> = ({
  onStreamReady,
  onStreamError,
  className = '',
}) => {
  const { t } = useTranslation();
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);

  const [permissionState, setPermissionState] = useState<MediaPermissionState>('idle');
  const [isVideoEnabled, setIsVideoEnabled] = useState(true);
  const [isAudioEnabled, setIsAudioEnabled] = useState(true);
  const [error, setError] = useState<string>('');
  const [devices, setDevices] = useState<MediaDeviceInfo[]>([]);
  const [selectedVideoDevice, setSelectedVideoDevice] = useState<string>('');
  const [selectedAudioDevice, setSelectedAudioDevice] = useState<string>('');
  const [showSettings, setShowSettings] = useState(false);

  // Load available devices
  useEffect(() => {
    const loadDevices = async () => {
      try {
        // Request permission first to enumerate devices
        await navigator.mediaDevices.getUserMedia({ audio: true, video: true });
        const mediaDevices = await navigator.mediaDevices.enumerateDevices();

        const videoDevices = mediaDevices.filter(device => device.kind === 'videoinput');
        const audioDevices = mediaDevices.filter(device => device.kind === 'audioinput');

        setDevices([...videoDevices, ...audioDevices]);

        if (videoDevices.length > 0) {
          setSelectedVideoDevice(videoDevices[0].deviceId);
        }
        if (audioDevices.length > 0) {
          setSelectedAudioDevice(audioDevices[0].deviceId);
        }
      } catch (err) {
        // Ignore permission errors during device enumeration
      }
    };

    loadDevices();
  }, []);

  // Cleanup stream on unmount
  useEffect(() => {
    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
      }
    };
  }, []);

  const startCapture = async () => {
    setPermissionState('requesting');
    setError('');

    try {
      const constraints: MediaStreamConstraints = {
        video: isVideoEnabled
          ? {
              deviceId: selectedVideoDevice || undefined,
              width: { ideal: 1280 },
              height: { ideal: 720 },
            }
          : false,
        audio: isAudioEnabled
          ? {
              deviceId: selectedAudioDevice || undefined,
            }
          : false,
      };

      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      streamRef.current = stream;

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }

      setPermissionState('granted');
      onStreamReady?.(stream);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : String(err);

      if (errorMessage.includes('Permission denied')) {
        setPermissionState('denied');
        setError(t('live.capture.errorPermissionDenied', 'Camera/microphone access denied. Please grant permission in your browser settings.'));
      } else if (errorMessage.includes('NotFound')) {
        setPermissionState('error');
        setError(t('live.capture.errorNotFound', 'No camera or microphone found. Please connect a device.'));
      } else if (errorMessage.includes('NotAllowedError')) {
        setPermissionState('denied');
        setError(t('live.capture.errorNotAllowed', 'Permission to access camera/microphone was not granted.'));
      } else {
        setPermissionState('error');
        setError(t('live.capture.errorGeneric', 'Failed to access camera/microphone: {{message}}', { message: errorMessage }));
      }

      const error = err instanceof Error ? err : new Error(errorMessage);
      onStreamError?.(error);
    }
  };

  const stopCapture = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }

    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }

    setPermissionState('idle');
  };

  const toggleVideo = () => {
    if (streamRef.current) {
      const videoTrack = streamRef.current.getVideoTracks()[0];
      if (videoTrack) {
        videoTrack.enabled = !isVideoEnabled;
        setIsVideoEnabled(videoTrack.enabled);
      }
    }
  };

  const toggleAudio = () => {
    if (streamRef.current) {
      const audioTrack = streamRef.current.getAudioTracks()[0];
      if (audioTrack) {
        audioTrack.enabled = !isAudioEnabled;
        setIsAudioEnabled(audioTrack.enabled);
      }
    }
  };

  const videoDevices = devices.filter(device => device.kind === 'videoinput');
  const audioDevices = devices.filter(device => device.kind === 'audioinput');

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Error state */}
      {error && (
        <div className="p-3 bg-red-900/30 text-red-300 rounded-md text-sm flex items-start gap-2 border border-red-700">
          <AlertCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Video preview */}
      <div className="relative bg-black rounded-lg overflow-hidden aspect-video">
        {permissionState === 'idle' && (
          <div className="absolute inset-0 flex flex-col items-center justify-center text-[color:var(--color-text-muted)]">
            <VideoOff className="w-12 h-12 mb-2" />
            <p className="text-sm">{t('live.capture.previewIdle', 'Camera is off')}</p>
          </div>
        )}

        {permissionState === 'requesting' && (
          <div className="absolute inset-0 flex flex-col items-center justify-center text-[color:var(--color-text-muted)]">
            <Loader2 className="w-12 h-12 mb-2 animate-spin" />
            <p className="text-sm">{t('live.capture.requestingPermission', 'Requesting camera/microphone access...')}</p>
          </div>
        )}

        {(permissionState === 'denied' || permissionState === 'error') && (
          <div className="absolute inset-0 flex flex-col items-center justify-center text-red-400">
            <AlertCircle className="w-12 h-12 mb-2" />
            <p className="text-sm text-center px-4">
              {permissionState === 'denied'
                ? t('live.capture.permissionDenied', 'Permission denied')
                : t('live.capture.error', 'Access failed')}
            </p>
          </div>
        )}

        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          className={`w-full h-full object-cover ${permissionState !== 'granted' ? 'hidden' : ''}`}
        />

        {/* Status indicator */}
        {permissionState === 'granted' && (
          <div className="absolute top-3 right-3 flex items-center gap-1.5 px-2 py-1 bg-green-600 rounded-full">
            <div className="w-2 h-2 bg-white rounded-full animate-pulse" />
            <span className="text-xs text-white font-medium">
              {t('live.capture.live', 'LIVE')}
            </span>
          </div>
        )}
      </div>

      {/* Controls */}
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          {/* Video toggle */}
          <button
            type="button"
            onClick={toggleVideo}
            disabled={permissionState !== 'granted'}
            className={`p-3 rounded-lg transition-colors ${
              isVideoEnabled
                ? 'bg-[color:var(--color-surface)] text-[color:var(--color-text)]'
                : 'bg-red-600 text-white'
            } disabled:opacity-50 disabled:cursor-not-allowed`}
            title={t('live.capture.toggleVideo', 'Toggle video')}
          >
            {isVideoEnabled ? <Video className="w-5 h-5" /> : <VideoOff className="w-5 h-5" />}
          </button>

          {/* Audio toggle */}
          <button
            type="button"
            onClick={toggleAudio}
            disabled={permissionState !== 'granted'}
            className={`p-3 rounded-lg transition-colors ${
              isAudioEnabled
                ? 'bg-[color:var(--color-surface)] text-[color:var(--color-text)]'
                : 'bg-red-600 text-white'
            } disabled:opacity-50 disabled:cursor-not-allowed`}
            title={t('live.capture.toggleAudio', 'Toggle audio')}
          >
            {isAudioEnabled ? <Mic className="w-5 h-5" /> : <MicOff className="w-5 h-5" />}
          </button>

          {/* Settings toggle */}
          {devices.length > 0 && (
            <button
              type="button"
              onClick={() => setShowSettings(!showSettings)}
              className="p-3 rounded-lg bg-[color:var(--color-surface)] text-[color:var(--color-text)] hover:bg-[color:var(--color-surface-muted)] transition-colors"
              title={t('live.capture.deviceSettings', 'Device settings')}
            >
              <Settings className="w-5 h-5" />
            </button>
          )}
        </div>

        {/* Start/Stop button */}
        {permissionState === 'granted' ? (
          <button
            type="button"
            onClick={stopCapture}
            className="px-6 py-3 bg-red-600 hover:bg-red-700 text-white rounded-lg flex items-center gap-2 transition-colors font-medium"
          >
            <VideoOff className="w-5 h-5" />
            {t('live.capture.stop', 'Stop Capture')}
          </button>
        ) : (
          <button
            type="button"
            onClick={startCapture}
            disabled={permissionState === 'requesting'}
            className="px-6 py-3 bg-green-600 hover:bg-green-700 text-white rounded-lg flex items-center gap-2 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {permissionState === 'requesting' ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Video className="w-5 h-5" />
            )}
            {t('live.capture.start', 'Start Capture')}
          </button>
        )}
      </div>

      {/* Device settings */}
      {showSettings && devices.length > 0 && (
        <div className="p-4 bg-[color:var(--color-surface-muted)] rounded-lg space-y-4">
          <h3 className="text-sm font-medium text-[color:var(--color-text)]">
            {t('live.capture.deviceSettings', 'Device Settings')}
          </h3>

          {videoDevices.length > 0 && (
            <div>
              <label className="block text-xs font-medium text-[color:var(--color-text-muted)] mb-1.5">
                {t('live.capture.camera', 'Camera')}
              </label>
              <select
                value={selectedVideoDevice}
                onChange={(e) => setSelectedVideoDevice(e.target.value)}
                className="w-full px-3 py-2 border border-[color:var(--color-border)] bg-[color:var(--color-surface)] text-[color:var(--color-text)] rounded-lg text-sm"
              >
                {videoDevices.map((device) => (
                  <option key={device.deviceId} value={device.deviceId}>
                    {device.label || `${t('live.capture.camera', 'Camera')} ${device.deviceId.slice(0, 8)}`}
                  </option>
                ))}
              </select>
            </div>
          )}

          {audioDevices.length > 0 && (
            <div>
              <label className="block text-xs font-medium text-[color:var(--color-text-muted)] mb-1.5">
                {t('live.capture.microphone', 'Microphone')}
              </label>
              <select
                value={selectedAudioDevice}
                onChange={(e) => setSelectedAudioDevice(e.target.value)}
                className="w-full px-3 py-2 border border-[color:var(--color-border)] bg-[color:var(--color-surface)] text-[color:var(--color-text)] rounded-lg text-sm"
              >
                {audioDevices.map((device) => (
                  <option key={device.deviceId} value={device.deviceId}>
                    {device.label || `${t('live.capture.microphone', 'Microphone')} ${device.deviceId.slice(0, 8)}`}
                  </option>
                ))}
              </select>
            </div>
          )}

          <button
            type="button"
            onClick={() => {
              if (permissionState === 'granted') {
                stopCapture();
                setTimeout(() => startCapture(), 100);
              } else {
                startCapture();
              }
            }}
            className="w-full px-4 py-2 bg-[color:var(--color-accent)] hover:opacity-90 text-white rounded-lg text-sm flex items-center justify-center gap-2 transition-colors"
          >
            <Check className="w-4 h-4" />
            {t('live.capture.applySettings', 'Apply Settings')}
          </button>
        </div>
      )}
    </div>
  );
};

export default CameraCapture;
