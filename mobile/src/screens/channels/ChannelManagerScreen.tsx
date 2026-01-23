/**
 * Channel Manager Screen
 *
 * Mobile-optimized screen for managing Telegram streaming channels.
 * Features:
 * - View all streaming channels with their status
 * - Start/stop streams with confirmation dialogs
 * - Auto-refresh during transitional states (starting/stopping)
 * - Pull-to-refresh for manual updates
 * - Error handling and user feedback
 *
 * Follows patterns from frontend/src/pages/ChannelManager.tsx
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  RefreshControl,
  TouchableOpacity,
  Alert,
  ActivityIndicator,
} from 'react-native';
import { useTranslation } from 'react-i18next';
import { useFocusEffect } from '@react-navigation/native';

// API
import { client } from '../../api/client';
import { channelsApi, StreamingChannel } from '../../api/channels';

interface ChannelCardProps {
  channel: StreamingChannel;
  onStart: (id: string) => void;
  onStop: (id: string) => void;
  loading?: boolean;
}

const ChannelCard: React.FC<ChannelCardProps> = ({ channel, onStart, onStop, loading }) => {
  const { t } = useTranslation();

  const getStatusConfig = () => {
    switch (channel.status) {
      case 'running':
        return {
          label: t('channels.status.running', 'Running'),
          backgroundColor: 'rgba(16, 185, 129, 0.1)',
          textColor: '#10b981',
          borderColor: 'rgba(16, 185, 129, 0.2)',
          icon: '📡',
        };
      case 'starting':
        return {
          label: t('channels.status.starting', 'Starting...'),
          backgroundColor: 'rgba(59, 130, 246, 0.1)',
          textColor: '#3b82f6',
          borderColor: 'rgba(59, 130, 246, 0.2)',
          icon: '⏳',
        };
      case 'stopping':
        return {
          label: t('channels.status.stopping', 'Stopping...'),
          backgroundColor: 'rgba(245, 158, 11, 0.1)',
          textColor: '#f59e0b',
          borderColor: 'rgba(245, 158, 11, 0.2)',
          icon: '⏳',
        };
      case 'error':
        return {
          label: t('channels.status.error', 'Error'),
          backgroundColor: 'rgba(239, 68, 68, 0.1)',
          textColor: '#ef4444',
          borderColor: 'rgba(239, 68, 68, 0.2)',
          icon: '⚠️',
        };
      case 'stopped':
      default:
        return {
          label: t('channels.status.stopped', 'Stopped'),
          backgroundColor: 'rgba(107, 114, 128, 0.1)',
          textColor: '#6b7280',
          borderColor: 'rgba(107, 114, 128, 0.2)',
          icon: '⏹',
        };
    }
  };

  const statusConfig = getStatusConfig();
  const isTransitional = channel.status === 'starting' || channel.status === 'stopping';
  const canStart = channel.status === 'stopped' || channel.status === 'error' || channel.status === 'unknown';
  const canStop = channel.status === 'running' || isTransitional;

  const handleStart = () => {
    Alert.alert(
      t('channels.confirmStart', 'Start Stream'),
      t('channels.confirmStartDesc', 'Start streaming to this channel?'),
      [
        { text: t('common.cancel', 'Cancel'), style: 'cancel' },
        {
          text: t('channels.start', 'Start'),
          onPress: () => onStart(channel.id),
        },
      ]
    );
  };

  const handleStop = () => {
    Alert.alert(
      t('channels.confirmStop', 'Stop Stream'),
      t('channels.confirmStopDesc', 'Stop streaming to this channel?'),
      [
        { text: t('common.cancel', 'Cancel'), style: 'cancel' },
        {
          text: t('channels.stop', 'Stop'),
          style: 'destructive',
          onPress: () => onStop(channel.id),
        },
      ]
    );
  };

  return (
    <View style={[styles.channelCard, { borderColor: statusConfig.borderColor }]}>
      {/* Header with icon and name */}
      <View style={styles.channelHeader}>
        <View style={[styles.statusIcon, { backgroundColor: statusConfig.backgroundColor }]}>
          <Text style={styles.statusIconText}>{statusConfig.icon}</Text>
        </View>
        <View style={styles.channelInfo}>
          <Text style={styles.channelName} numberOfLines={1}>
            {channel.name}
          </Text>
          <View style={styles.channelMeta}>
            <Text style={styles.chatId}>
              {channel.chat_username ? `@${channel.chat_username}` : `ID: ${channel.chat_id}`}
            </Text>
            <Text style={styles.streamType}>
              {channel.stream_type === 'audio' ? '🎵' : '🎬'} {channel.stream_type || 'video'}
            </Text>
          </View>
        </View>
      </View>

      {/* Status badge */}
      <View style={[styles.statusBadge, { backgroundColor: statusConfig.backgroundColor }]}>
        {isTransitional && <ActivityIndicator size="small" color={statusConfig.textColor} />}
        <Text style={[styles.statusText, { color: statusConfig.textColor }]}>
          {statusConfig.label}
        </Text>
      </View>

      {/* Error message */}
      {channel.error_message && (
        <View style={styles.errorContainer}>
          <Text style={styles.errorIcon}>⚠️</Text>
          <Text style={styles.errorText} numberOfLines={2}>
            {channel.error_message}
          </Text>
        </View>
      )}

      {/* Quality indicator */}
      {channel.video_quality && (
        <View style={styles.qualityContainer}>
          <Text style={styles.qualityIcon}>🎥</Text>
          <Text style={styles.qualityText}>
            {t('channels.quality', 'Quality')}: {channel.video_quality}
          </Text>
        </View>
      )}

      {/* Action buttons */}
      <View style={styles.actionButtons}>
        {canStart && (
          <TouchableOpacity
            style={[styles.actionButton, styles.startButton]}
            onPress={handleStart}
            disabled={loading}
            activeOpacity={0.7}
          >
            <Text style={styles.startButtonText}>▶</Text>
            <Text style={styles.startButtonLabel}>
              {t('channels.start', 'Start')}
            </Text>
          </TouchableOpacity>
        )}
        {canStop && (
          <TouchableOpacity
            style={[styles.actionButton, styles.stopButton]}
            onPress={handleStop}
            disabled={loading}
            activeOpacity={0.7}
          >
            <Text style={styles.stopButtonText}>⏹</Text>
            <Text style={styles.stopButtonLabel}>
              {t('channels.stop', 'Stop')}
            </Text>
          </TouchableOpacity>
        )}
      </View>
    </View>
  );
};

const ChannelManagerScreen: React.FC = () => {
  const { t } = useTranslation();

  // State
  const [channels, setChannels] = useState<StreamingChannel[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  // Fetch channels
  const fetchChannels = useCallback(async () => {
    try {
      const data = await channelsApi.list();
      setChannels(data);
    } catch (error) {
      console.error('Failed to fetch channels:', error);
      Alert.alert(
        t('common.error', 'Error'),
        t('channels.loadError', 'Failed to load channels')
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [t]);

  // Pull to refresh
  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await fetchChannels();
  }, [fetchChannels]);

  // Load data when screen comes into focus
  useFocusEffect(
    useCallback(() => {
      setLoading(true);
      fetchChannels();
    }, [fetchChannels])
  );

  // Auto-refresh when channels are in transitional states
  useEffect(() => {
    const hasTransitionalStatus = channels.some(
      ch => ch.status === 'starting' || ch.status === 'stopping'
    );

    if (hasTransitionalStatus) {
      const interval = setInterval(() => {
        fetchChannels();
      }, 2000); // Poll every 2 seconds

      return () => clearInterval(interval);
    }
  }, [channels, fetchChannels]);

  // Start channel
  const handleStart = async (channelId: string) => {
    setActionLoading(channelId);
    try {
      await channelsApi.start(channelId);
      await fetchChannels();
      Alert.alert(
        t('common.success', 'Success'),
        t('channels.startSuccess', 'Stream started successfully')
      );
    } catch (error: any) {
      const errorMessage = error?.response?.data?.detail || t('errors.somethingWentWrong', 'Something went wrong');
      Alert.alert(t('common.error', 'Error'), errorMessage);
    } finally {
      setActionLoading(null);
    }
  };

  // Stop channel
  const handleStop = async (channelId: string) => {
    setActionLoading(channelId);
    try {
      await channelsApi.stop(channelId);
      await fetchChannels();
      Alert.alert(
        t('common.success', 'Success'),
        t('channels.stopSuccess', 'Stream stopped successfully')
      );
    } catch (error: any) {
      const errorMessage = error?.response?.data?.detail || t('errors.somethingWentWrong', 'Something went wrong');
      Alert.alert(t('common.error', 'Error'), errorMessage);
    } finally {
      setActionLoading(null);
    }
  };

  // Render loading state
  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#06b6d4" />
        <Text style={styles.loadingText}>
          {t('channels.loading', 'Loading channels...')}
        </Text>
      </View>
    );
  }

  // Render empty state
  if (channels.length === 0) {
    return (
      <ScrollView
        style={styles.container}
        contentContainerStyle={styles.contentContainer}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#06b6d4" />
        }
      >
        <View style={styles.emptyState}>
          <Text style={styles.emptyIcon}>📺</Text>
          <Text style={styles.emptyTitle}>
            {t('channels.noChannels', 'No Channels')}
          </Text>
          <Text style={styles.emptyDescription}>
            {t('channels.noChannelsDesc', 'Create your first streaming channel to get started')}
          </Text>
        </View>
      </ScrollView>
    );
  }

  // Render channel list
  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.contentContainer}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#06b6d4" />
      }
    >
      {/* Header */}
      <View style={styles.header}>
        <View style={styles.headerLeft}>
          <View style={styles.headerIconContainer}>
            <Text style={styles.headerIcon}>📺</Text>
          </View>
          <View>
            <Text style={styles.headerTitle}>
              {t('nav.channels', 'Channels')}
            </Text>
            <Text style={styles.headerSubtitle}>
              {t('channels.manage', 'Manage your streaming channels')}
            </Text>
          </View>
        </View>
      </View>

      {/* Channel count indicator */}
      <View style={styles.countBanner}>
        <Text style={styles.countText}>
          {channels.length} {t('channels.channels', 'channel{{s}}', { count: channels.length })}
        </Text>
      </View>

      {/* Channels list */}
      {channels.map((channel) => (
        <ChannelCard
          key={channel.id}
          channel={channel}
          onStart={handleStart}
          onStop={handleStop}
          loading={actionLoading === channel.id}
        />
      ))}
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f9fafb',
  },
  contentContainer: {
    padding: 16,
    paddingBottom: 32,
  },
  // Loading state
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#f9fafb',
    gap: 12,
  },
  loadingText: {
    fontSize: 16,
    color: '#6b7280',
    fontWeight: '500',
  },
  // Header
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  headerLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  headerIconContainer: {
    width: 44,
    height: 44,
    borderRadius: 12,
    backgroundColor: '#06b6d4',
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 2,
  },
  headerIcon: {
    fontSize: 20,
  },
  headerTitle: {
    fontSize: 24,
    fontWeight: '700',
    color: '#111827',
  },
  headerSubtitle: {
    fontSize: 14,
    color: '#6b7280',
    marginTop: 2,
  },
  // Count banner
  countBanner: {
    backgroundColor: '#ffffff',
    borderRadius: 12,
    paddingHorizontal: 16,
    paddingVertical: 12,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: '#e5e7eb',
    alignItems: 'center',
  },
  countText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#374151',
  },
  // Empty state
  emptyState: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 64,
    gap: 12,
  },
  emptyIcon: {
    fontSize: 64,
  },
  emptyTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: '#111827',
  },
  emptyDescription: {
    fontSize: 14,
    color: '#6b7280',
    textAlign: 'center',
    paddingHorizontal: 32,
  },
  // Channel Card
  channelCard: {
    backgroundColor: '#ffffff',
    borderRadius: 16,
    borderWidth: 1,
    padding: 16,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 2,
    gap: 12,
  },
  channelHeader: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 12,
  },
  statusIcon: {
    width: 44,
    height: 44,
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
  },
  statusIconText: {
    fontSize: 20,
  },
  channelInfo: {
    flex: 1,
    gap: 4,
  },
  channelName: {
    fontSize: 16,
    fontWeight: '700',
    color: '#111827',
  },
  channelMeta: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  chatId: {
    fontSize: 13,
    color: '#6b7280',
  },
  streamType: {
    fontSize: 12,
    color: '#6b7280',
    backgroundColor: '#f3f4f6',
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 4,
  },
  statusBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    alignSelf: 'flex-start',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 12,
  },
  statusText: {
    fontSize: 12,
    fontWeight: '600',
  },
  errorContainer: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 8,
    backgroundColor: 'rgba(239, 68, 68, 0.1)',
    borderRadius: 8,
    padding: 10,
    borderWidth: 1,
    borderColor: 'rgba(239, 68, 68, 0.2)',
  },
  errorIcon: {
    fontSize: 14,
    marginTop: 1,
  },
  errorText: {
    flex: 1,
    fontSize: 13,
    color: '#b91c1c',
  },
  qualityContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  qualityIcon: {
    fontSize: 14,
  },
  qualityText: {
    fontSize: 13,
    color: '#6b7280',
  },
  // Action buttons
  actionButtons: {
    flexDirection: 'row',
    gap: 8,
    marginTop: 4,
  },
  actionButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    paddingVertical: 12,
    borderRadius: 10,
    minHeight: 44,
  },
  startButton: {
    backgroundColor: '#10b981',
  },
  startButtonText: {
    fontSize: 16,
    color: '#ffffff',
  },
  startButtonLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#ffffff',
  },
  stopButton: {
    backgroundColor: '#ef4444',
  },
  stopButtonText: {
    fontSize: 16,
    color: '#ffffff',
  },
  stopButtonLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#ffffff',
  },
});

export default ChannelManagerScreen;
