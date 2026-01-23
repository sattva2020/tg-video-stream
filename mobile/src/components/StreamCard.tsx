/**
 * Stream Card Component
 *
 * Displays stream status including online/offline state, current track, and listener count.
 * Mobile-optimized with touch targets at least 44x44px.
 * Follows patterns from frontend/src/components/dashboard/StreamStatusCard.tsx
 */

import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ViewStyle,
} from 'react-native';
import { useTranslation } from 'react-i18next';
import { LinearGradient } from 'expo-linear-gradient';

export interface StreamData {
  online: boolean;
  status: 'running' | 'stopped' | 'error';
  uptime_seconds?: number;
  current_track?: {
    title?: string;
    type?: string;
    duration?: number;
    url?: string;
  };
  queue?: {
    total: number;
    queued: number;
  };
  listener_count?: number;
  error?: string;
}

interface StreamCardProps {
  streamData: StreamData | null;
  loading?: boolean;
  onRefresh?: () => void;
  style?: ViewStyle;
}

// Format uptime to human-readable string
function formatUptime(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}m ${secs}s`;
  }
  const hours = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  return `${hours}h ${mins}m`;
}

// Format duration to MM:SS
function formatDuration(seconds: number | null): string {
  if (!seconds) return '--:--';
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${String(secs).padStart(2, '0')}`;
}

// Simple icon components
const StreamIcon: React.FC<{ online: boolean }> = ({ online }) => {
  return (
    <View style={[styles.statusIcon, online ? styles.statusIconOnline : styles.statusIconOffline]}>
      <Text style={styles.statusIconText}>{online ? '📻' : '⏸'}</Text>
    </View>
  );
};

export const StreamCard: React.FC<StreamCardProps> = ({
  streamData,
  loading = false,
  onRefresh,
  style,
}) => {
  const { t } = useTranslation();

  const getStatusConfig = () => {
    if (!streamData || streamData.status === 'error') {
      return {
        label: t('dashboard.offline', 'Offline'),
        backgroundColor: 'rgba(239, 68, 68, 0.1)',
        textColor: '#ef4444',
        borderColor: 'rgba(239, 68, 68, 0.2)',
      };
    }

    if (streamData.online && streamData.status === 'running') {
      return {
        label: t('dashboard.online', 'Online'),
        backgroundColor: 'rgba(16, 185, 129, 0.1)',
        textColor: '#10b981',
        borderColor: 'rgba(16, 185, 129, 0.2)',
      };
    }

    return {
      label: t('dashboard.offline', 'Offline'),
      backgroundColor: 'rgba(107, 114, 128, 0.1)',
      textColor: '#6b7280',
      borderColor: 'rgba(107, 114, 128, 0.2)',
    };
  };

  const statusConfig = getStatusConfig();

  if (loading) {
    return (
      <View style={[styles.container, style]}>
        <View style={styles.header}>
          <View style={styles.headerLeft}>
            <View style={[styles.statusIconPlaceholder, { backgroundColor: statusConfig.borderColor }]} />
            <View>
              <View style={[styles.skeletonText, { width: 140, height: 20 }]} />
              <View style={[styles.skeletonText, { width: 80, height: 16, marginTop: 4 }]} />
            </View>
          </View>
          <TouchableOpacity style={styles.refreshButton} disabled>
            <Text style={styles.refreshIcon}>↻</Text>
          </TouchableOpacity>
        </View>
      </View>
    );
  }

  return (
    <View style={[styles.container, { borderColor: statusConfig.borderColor }, style]}>
      {/* Header with status and refresh */}
      <View style={styles.header}>
        <View style={styles.headerLeft}>
          <StreamIcon online={streamData?.online || false} />
          <View>
            <Text style={styles.title}>{t('dashboard.streamStatus', 'Stream Status')}</Text>
            <View style={styles.statusRow}>
              <View style={[styles.statusBadge, { backgroundColor: statusConfig.backgroundColor }]}>
                <Text style={[styles.statusText, { color: statusConfig.textColor }]}>
                  {statusConfig.label}
                </Text>
              </View>
              {streamData?.uptime_seconds && (
                <Text style={styles.uptimeText}>
                  ⏱ {formatUptime(streamData.uptime_seconds)}
                </Text>
              )}
            </View>
          </View>
        </View>

        {onRefresh && (
          <TouchableOpacity
            style={styles.refreshButton}
            onPress={onRefresh}
            activeOpacity={0.7}
            hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
          >
            <Text style={[styles.refreshIcon, loading && styles.refreshIconSpinning]}>↻</Text>
          </TouchableOpacity>
        )}
      </View>

      {/* Current track */}
      {streamData?.current_track && (
        <View style={styles.trackSection}>
          <View style={styles.trackHeader}>
            <Text style={styles.trackIcon}>🎵</Text>
            <View style={styles.trackInfo}>
              <View style={styles.trackPlayingRow}>
                <Text style={styles.trackPlayingIndicator}>▶</Text>
                <Text style={styles.trackPlayingLabel}>
                  {t('dashboard.currentTrack', 'Now Playing')}
                </Text>
              </View>
              <Text style={styles.trackTitle} numberOfLines={1}>
                {streamData.current_track.title || t('common.noTrack', 'No track')}
              </Text>
              <View style={styles.trackDetails}>
                <Text style={styles.trackType}>
                  {streamData.current_track.type?.toUpperCase() || 'TRACK'}
                </Text>
                <Text style={styles.trackDuration}>
                  {formatDuration(streamData.current_track.duration || null)}
                </Text>
              </View>
            </View>
          </View>
        </View>
      )}

      {/* Queue stats */}
      {streamData?.queue && (
        <View style={styles.queueSection}>
          <View style={styles.queueStat}>
            <Text style={styles.queueStatLabel}>
              {t('dashboard.totalTracks', 'Total Tracks')}
            </Text>
            <Text style={styles.queueStatValue}>{streamData.queue.total}</Text>
          </View>
          <View style={styles.queueStat}>
            <Text style={styles.queueStatLabel}>
              {t('dashboard.queueWaiting', 'Waiting')}
            </Text>
            <Text style={styles.queueStatValue}>{streamData.queue.queued}</Text>
          </View>
        </View>
      )}

      {/* Listener count */}
      {streamData?.listener_count !== undefined && (
        <View style={styles.listenerSection}>
          <LinearGradient
            colors={['#06b6d4', '#0891b2']}
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 0 }}
            style={styles.listenerGradient}
          >
            <Text style={styles.listenerIcon}>👥</Text>
            <View style={styles.listenerInfo}>
              <Text style={styles.listenerLabel}>
                {t('dashboard.listeners', '{{count}} listeners', { count: streamData.listener_count })}
              </Text>
            </View>
          </LinearGradient>
        </View>
      )}

      {/* Error message */}
      {streamData?.error && (
        <View style={styles.errorSection}>
          <Text style={styles.errorIcon}>⚠</Text>
          <Text style={styles.errorText}>{streamData.error}</Text>
        </View>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    backgroundColor: '#ffffff',
    borderRadius: 24,
    borderWidth: 1,
    padding: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 3,
    gap: 12,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
  },
  headerLeft: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 12,
    flex: 1,
  },
  title: {
    fontSize: 18,
    fontWeight: '700',
    color: '#111827',
    marginBottom: 4,
  },
  statusRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  statusBadge: {
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 12,
  },
  statusText: {
    fontSize: 12,
    fontWeight: '600',
  },
  uptimeText: {
    fontSize: 12,
    color: '#6b7280',
  },
  statusIcon: {
    width: 40,
    height: 40,
    borderRadius: 10,
    justifyContent: 'center',
    alignItems: 'center',
  },
  statusIconOnline: {
    backgroundColor: 'rgba(16, 185, 129, 0.1)',
  },
  statusIconOffline: {
    backgroundColor: 'rgba(107, 114, 128, 0.1)',
  },
  statusIconText: {
    fontSize: 20,
  },
  statusIconPlaceholder: {
    width: 40,
    height: 40,
    borderRadius: 10,
  },
  refreshButton: {
    width: 36,
    height: 36,
    borderRadius: 8,
    backgroundColor: '#f3f4f6',
    justifyContent: 'center',
    alignItems: 'center',
    minHeight: 44, // Ensure adequate touch target
    minWidth: 44,
  },
  refreshIcon: {
    fontSize: 18,
    color: '#6b7280',
  },
  refreshIconSpinning: {
    // Animation would require Animated API
  },
  // Track section
  trackSection: {
    backgroundColor: '#f9fafb',
    borderRadius: 12,
    padding: 12,
    borderWidth: 1,
    borderColor: '#e5e7eb',
  },
  trackHeader: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 12,
  },
  trackIcon: {
    fontSize: 16,
    marginTop: 2,
  },
  trackInfo: {
    flex: 1,
  },
  trackPlayingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    marginBottom: 4,
  },
  trackPlayingIndicator: {
    fontSize: 12,
    color: '#10b981',
  },
  trackPlayingLabel: {
    fontSize: 11,
    color: '#6b7280',
    fontWeight: '500',
  },
  trackTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#111827',
    marginBottom: 4,
  },
  trackDetails: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  trackType: {
    fontSize: 11,
    color: '#6b7280',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  trackDuration: {
    fontSize: 11,
    color: '#6b7280',
  },
  // Queue section
  queueSection: {
    flexDirection: 'row',
    gap: 12,
  },
  queueStat: {
    flex: 1,
    backgroundColor: '#f9fafb',
    borderRadius: 12,
    padding: 12,
    borderWidth: 1,
    borderColor: '#e5e7eb',
    alignItems: 'center',
  },
  queueStatLabel: {
    fontSize: 11,
    color: '#6b7280',
    marginBottom: 4,
  },
  queueStatValue: {
    fontSize: 20,
    fontWeight: '700',
    color: '#111827',
  },
  // Listener section
  listenerSection: {
    borderRadius: 12,
    overflow: 'hidden',
  },
  listenerGradient: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 12,
    gap: 12,
  },
  listenerIcon: {
    fontSize: 20,
  },
  listenerInfo: {
    flex: 1,
  },
  listenerLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#ffffff',
  },
  // Error section
  errorSection: {
    backgroundColor: 'rgba(239, 68, 68, 0.1)',
    borderRadius: 12,
    padding: 12,
    borderWidth: 1,
    borderColor: 'rgba(239, 68, 68, 0.2)',
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 8,
  },
  errorIcon: {
    fontSize: 16,
    color: '#ef4444',
    marginTop: 1,
  },
  errorText: {
    flex: 1,
    fontSize: 13,
    color: '#b91c1c',
  },
  // Skeleton styles
  skeletonText: {
    backgroundColor: '#e5e7eb',
    borderRadius: 4,
  },
});
