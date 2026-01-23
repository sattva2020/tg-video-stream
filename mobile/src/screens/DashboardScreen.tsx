/**
 * Dashboard Screen
 *
 * Mobile-optimized dashboard showing stream status, listener counts, and quick action buttons.
 * Follows patterns from frontend/src/pages/DashboardPage.tsx and AdminDashboardV2.tsx
 *
 * Features:
 * - Stream status display with online/offline state
 * - Listener count and uptime statistics
 * - Quick action buttons for stream control
 * - Mobile-friendly layout with proper touch targets (44x44px minimum)
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
} from 'react-native';
import { useTranslation } from 'react-i18next';
import { useFocusEffect } from '@react-navigation/native';

// Contexts
import { useAuth } from '../contexts/AuthContext';
import { apiClient } from '../api/client';

// Components
import { StreamCard, StreamData } from '../components/StreamCard';
import { StatCard, IconName } from '../components/StatCard';

// Types
import type { UserRole } from '../api/types';

interface DashboardStats {
  total_listeners: number;
  total_streams: number;
  active_channels: number;
  uptime_seconds?: number;
}

const DashboardScreen: React.FC = () => {
  const { t } = useTranslation();
  const { user } = useAuth();
  const userRole = user?.role || 'user';

  // State
  const [streamData, setStreamData] = useState<StreamData | null>(null);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  // Determine permissions based on role
  const canControlStream = ['superadmin', 'admin', 'operator', 'moderator'].includes(userRole);
  const canViewSystemStats = ['superadmin', 'admin'].includes(userRole);

  // Fetch stream status
  const fetchStreamStatus = useCallback(async () => {
    try {
      const response = await apiClient.get<any>('/stream/status');
      setStreamData({
        online: response.data.online || false,
        status: response.data.status || 'stopped',
        uptime_seconds: response.data.uptime_seconds,
        current_track: response.data.current_track,
        queue: response.data.queue,
        listener_count: response.data.listener_count || 0,
        error: response.data.error,
      });
    } catch (error) {
      console.error('Failed to fetch stream status:', error);
      // Set offline state on error
      setStreamData({
        online: false,
        status: 'error',
        listener_count: 0,
        error: t('errors.networkError', 'Failed to load stream status'),
      });
    }
  }, [t]);

  // Fetch statistics
  const fetchStats = useCallback(async () => {
    if (!canViewSystemStats) {
      // Set basic stats for all users
      if (streamData) {
        setStats({
          total_listeners: streamData.listener_count || 0,
          total_streams: streamData.online ? 1 : 0,
          active_channels: streamData.online ? 1 : 0,
        });
      }
      return;
    }

    try {
      const response = await apiClient.get<any>('/analytics/stats');
      setStats(response.data);
    } catch (error) {
      console.error('Failed to fetch stats:', error);
      // Fallback to stream data for basic stats
      if (streamData) {
        setStats({
          total_listeners: streamData.listener_count || 0,
          total_streams: streamData.online ? 1 : 0,
          active_channels: streamData.online ? 1 : 0,
        });
      }
    }
  }, [canViewSystemStats, streamData, t]);

  // Load all data
  const loadData = useCallback(async () => {
    setLoading(true);
    await Promise.all([fetchStreamStatus(), fetchStats()]);
    setLoading(false);
  }, [fetchStreamStatus, fetchStats]);

  // Refresh data (pull-to-refresh)
  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await Promise.all([fetchStreamStatus(), fetchStats()]);
    setRefreshing(false);
  }, [fetchStreamStatus, fetchStats]);

  // Load data when screen comes into focus
  useFocusEffect(
    useCallback(() => {
      loadData();
    }, [loadData])
  );

  // Stream control handlers
  const handleStartStream = async () => {
    if (!canControlStream) return;
    setActionLoading('start');
    try {
      await apiClient.post('/stream/start');
      await fetchStreamStatus();
      Alert.alert(t('common.success', 'Success'), t('dashboard.streamStarted', 'Stream started'));
    } catch (error: any) {
      const errorMessage = error?.response?.data?.detail || t('errors.somethingWentWrong', 'Something went wrong');
      Alert.alert(t('common.error', 'Error'), errorMessage);
    } finally {
      setActionLoading(null);
    }
  };

  const handleStopStream = async () => {
    if (!canControlStream) return;
    setActionLoading('stop');
    try {
      await apiClient.post('/stream/stop');
      await fetchStreamStatus();
      Alert.alert(t('common.success', 'Success'), t('dashboard.streamStopped', 'Stream stopped'));
    } catch (error: any) {
      const errorMessage = error?.response?.data?.detail || t('errors.somethingWentWrong', 'Something went wrong');
      Alert.alert(t('common.error', 'Error'), errorMessage);
    } finally {
      setActionLoading(null);
    }
  };

  const handleRestartStream = async () => {
    if (!canControlStream) return;
    Alert.alert(
      t('dashboard.confirmRestart', 'Confirm Restart'),
      t('dashboard.restartDesc', 'Restart the stream? This will interrupt current playback.'),
      [
        { text: t('common.cancel', 'Cancel'), style: 'cancel' },
        {
          text: t('dashboard.restart', 'Restart'),
          style: 'destructive',
          onPress: async () => {
            setActionLoading('restart');
            try {
              await apiClient.post('/stream/restart');
              await fetchStreamStatus();
              Alert.alert(t('common.success', 'Success'), t('dashboard.streamRestarted', 'Stream restarted'));
            } catch (error: any) {
              const errorMessage = error?.response?.data?.detail || t('errors.somethingWentWrong', 'Something went wrong');
              Alert.alert(t('common.error', 'Error'), errorMessage);
            } finally {
              setActionLoading(null);
            }
          },
        },
      ]
    );
  };

  // Build stat cards
  const getStatCards = () => {
    const cards: Array<{
      title: string;
      value: string | number;
      subtitle?: string;
      icon: IconName;
      color: 'violet' | 'amber' | 'emerald' | 'rose' | 'blue' | 'cyan';
      loading?: boolean;
    }> = [];

    // System stats (admin only)
    if (canViewSystemStats && stats) {
      cards.push(
        {
          title: t('dashboard.totalListeners', 'Total Listeners'),
          value: stats.total_listeners || 0,
          icon: 'users',
          color: 'violet',
        },
        {
          title: t('dashboard.activeChannels', 'Active Channels'),
          value: stats.active_channels || 0,
          icon: 'radio',
          color: 'emerald',
        }
      );
    }

    // Stream status (all users)
    cards.push({
      title: t('dashboard.streamStatus', 'Stream Status'),
      value: streamData?.online ? t('dashboard.online', 'Online') : t('dashboard.offline', 'Offline'),
      icon: streamData?.online ? 'check' : 'clock',
      color: streamData?.online ? 'emerald' : 'rose',
      subtitle: streamData?.uptime_seconds
        ? `${t('dashboard.uptime', 'Uptime')}: ${Math.floor(streamData.uptime_seconds / 3600)}h`
        : undefined,
    });

    return cards;
  };

  // Quick actions
  const getQuickActions = () => {
    const actions = [];

    if (canControlStream) {
      if (streamData?.online) {
        actions.push({
          id: 'stop' as const,
          title: t('dashboard.stopStream', 'Stop'),
          icon: '⏹',
          color: '#ef4444',
          onPress: handleStopStream,
          loading: actionLoading === 'stop',
        });
      } else {
        actions.push({
          id: 'start' as const,
          title: t('dashboard.startStream', 'Start'),
          icon: '▶',
          color: '#10b981',
          onPress: handleStartStream,
          loading: actionLoading === 'start',
        });
      }

      if (streamData?.online) {
        actions.push({
          id: 'restart' as const,
          title: t('dashboard.restart', 'Restart'),
          icon: '↻',
          color: '#3b82f6',
          onPress: handleRestartStream,
          loading: actionLoading === 'restart',
        });
      }
    }

    return actions;
  };

  const statCards = getStatCards();
  const quickActions = getQuickActions();

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
            <Text style={styles.headerIcon}>📊</Text>
          </View>
          <View>
            <Text style={styles.headerTitle}>
              {t('nav.dashboard', 'Dashboard')}
            </Text>
            <Text style={styles.headerSubtitle}>
              {t('dashboard.welcome', 'Welcome')}, {user?.full_name || t('common.user', 'User')}!
            </Text>
          </View>
        </View>

        {/* Live indicator */}
        {streamData?.online && (
          <View style={styles.liveIndicator}>
            <View style={styles.liveDot} />
            <Text style={styles.liveText}>{t('dashboard.liveNow', 'LIVE')}</Text>
          </View>
        )}
      </View>

      {/* Stats Grid */}
      <View style={styles.statsGrid}>
        {statCards.map((card, index) => (
          <StatCard
            key={`${card.title}-${index}`}
            {...card}
            loading={loading}
            style={styles.statCard}
          />
        ))}
      </View>

      {/* Stream Status Card */}
      <StreamCard
        streamData={streamData}
        loading={loading}
        onRefresh={fetchStreamStatus}
        style={styles.streamCard}
      />

      {/* Quick Actions */}
      {quickActions.length > 0 && (
        <View style={styles.quickActionsSection}>
          <Text style={styles.quickActionsTitle}>
            {t('dashboard.quickActions', 'Quick Actions')}
          </Text>
          <View style={styles.quickActionsGrid}>
            {quickActions.map((action) => (
              <TouchableOpacity
                key={action.id}
                style={[
                  styles.quickActionButton,
                  { backgroundColor: action.color },
                  action.loading && styles.quickActionButtonDisabled,
                ]}
                onPress={action.onPress}
                disabled={action.loading}
                activeOpacity={0.7}
              >
                <Text style={styles.quickActionIcon}>{action.icon}</Text>
                <Text style={styles.quickActionTitle}>
                  {action.loading ? '...' : action.title}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>
      )}
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
  // Header
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 24,
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
  liveIndicator: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 12,
    paddingVertical: 6,
    backgroundColor: 'rgba(16, 185, 129, 0.1)',
    borderRadius: 16,
    borderWidth: 1,
    borderColor: 'rgba(16, 185, 129, 0.2)',
  },
  liveDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: '#10b981',
  },
  liveText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#10b981',
  },
  // Stats Grid
  statsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginHorizontal: -6,
    marginBottom: 16,
  },
  statCard: {
    width: '50%',
    paddingHorizontal: 6,
    marginBottom: 12,
  },
  // Stream Card
  streamCard: {
    marginBottom: 16,
  },
  // Quick Actions
  quickActionsSection: {
    marginBottom: 16,
  },
  quickActionsTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#111827',
    marginBottom: 12,
    marginLeft: 4,
  },
  quickActionsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginHorizontal: -6,
    gap: 12,
  },
  quickActionButton: {
    flex: 1,
    minWidth: '45%',
    minHeight: 80,
    borderRadius: 16,
    padding: 16,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 2,
  },
  quickActionButtonDisabled: {
    opacity: 0.5,
  },
  quickActionIcon: {
    fontSize: 24,
  },
  quickActionTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#ffffff',
  },
});

export default DashboardScreen;
