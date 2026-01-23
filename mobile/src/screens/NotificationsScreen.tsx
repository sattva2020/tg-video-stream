/**
 * Notifications Screen
 *
 * Mobile-optimized screen for viewing notification delivery logs.
 * Follows patterns from frontend/src/pages/notifications/Logs.tsx adapted for React Native.
 *
 * Features:
 * - Display delivery logs with status badges
 * - Filter by status, rule, channel, recipient
 * - Pull-to-refresh for latest logs
 * - Mobile-friendly layout with proper touch targets
 */

import React, { useState, useCallback, useEffect, useMemo } from 'react';
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
import { notificationsApi, DeliveryLog, DeliveryLogStatus } from '../api/notifications';

// Types
import type { StackNavigationProp } from '@react-navigation/stack';

interface NavigationProps {
  navigation: StackNavigationProp<any>;
}

const getStatusColor = (status: DeliveryLogStatus): string => {
  const colors: Record<DeliveryLogStatus, string> = {
    success: '#10b981',
    fail: '#ef4444',
    failover: '#f59e0b',
    'rate-limited': '#f97316',
    suppressed: '#6b7280',
    deduped: '#6366f1',
  };
  return colors[status] || '#9ca3af';
};

const getStatusLabel = (status: DeliveryLogStatus): string => {
  const labels: Record<DeliveryLogStatus, string> = {
    success: '✓',
    fail: '✕',
    failover: '↻',
    'rate-limited': '⚠',
    suppressed: '⊘',
    deduped: '〃',
  };
  return labels[status] || '?';
};

const NotificationsScreen: React.FC<NavigationProps> = ({ navigation }) => {
  const { t } = useTranslation();

  // State
  const [logs, setLogs] = useState<DeliveryLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [filterStatus, setFilterStatus] = useState<DeliveryLogStatus[]>(['fail', 'failover']);

  // Fetch delivery logs
  const fetchLogs = useCallback(async () => {
    try {
      const filters = {
        statuses: filterStatus.length > 0 ? filterStatus : undefined,
        limit: 50,
      };
      const data = await notificationsApi.listLogs(filters);
      setLogs(data);
    } catch (error) {
      console.error('Failed to fetch notification logs:', error);
      Alert.alert(
        t('common.error', 'Error'),
        t('errors.somethingWentWrong', 'Something went wrong')
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [filterStatus, t]);

  // Load data when screen comes into focus
  useFocusEffect(
    useCallback(() => {
      setLoading(true);
      fetchLogs();
    }, [fetchLogs])
  );

  // Pull-to-refresh
  const onRefresh = useCallback(() => {
    setRefreshing(true);
    fetchLogs();
  }, [fetchLogs]);

  // Toggle status filter
  const toggleStatusFilter = (status: DeliveryLogStatus) => {
    setFilterStatus((prev) =>
      prev.includes(status) ? prev.filter((s) => s !== status) : [...prev, status]
    );
  };

  // Format date for display
  const formatDate = (dateString: string): string => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);

    if (diffMins < 1) return t('notifications.justNow', 'Just now');
    if (diffMins < 60) return t('notifications.minutesAgo', '{{m}}m ago', { m: diffMins });
    if (diffHours < 24) return t('notifications.hoursAgo', '{{h}}h ago', { h: diffHours });
    return date.toLocaleDateString();
  };

  // Filter buttons
  const statusFilters: DeliveryLogStatus[] = ['success', 'fail', 'failover', 'suppressed', 'rate-limited', 'deduped'];

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <View style={styles.headerLeft}>
          <View style={styles.headerIconContainer}>
            <Text style={styles.headerIcon}>🔔</Text>
          </View>
          <View>
            <Text style={styles.headerTitle}>
              {t('nav.notifications', 'Notifications')}
            </Text>
            <Text style={styles.headerSubtitle}>
              {t('notifications.deliveryLogs', 'Delivery Logs')}
            </Text>
          </View>
        </View>
      </View>

      {/* Status Filters */}
      <View style={styles.filterSection}>
        <Text style={styles.filterLabel}>
          {t('notifications.filterByStatus', 'Filter by status')}
        </Text>
        <View style={styles.filterButtons}>
          {statusFilters.map((status) => {
            const isSelected = filterStatus.includes(status);
            return (
              <TouchableOpacity
                key={status}
                style={[
                  styles.filterButton,
                  {
                    backgroundColor: isSelected
                      ? getStatusColor(status)
                      : '#f3f4f6',
                    borderColor: getStatusColor(status),
                  },
                ]}
                onPress={() => toggleStatusFilter(status)}
                activeOpacity={0.7}
              >
                <Text
                  style={[
                    styles.filterButtonText,
                    { color: isSelected ? '#ffffff' : getStatusColor(status) },
                  ]}
                >
                  {getStatusLabel(status)} {status}
                </Text>
              </TouchableOpacity>
            );
          })}
        </View>
      </View>

      {/* Logs List */}
      {loading ? (
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#06b6d4" />
          <Text style={styles.loadingText}>
            {t('common.loading', 'Loading...')}
          </Text>
        </View>
      ) : (
        <ScrollView
          style={styles.logsContainer}
          contentContainerStyle={styles.logsContent}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={onRefresh}
              tintColor="#06b6d4"
              colors={['#06b6d4']}
            />
          }
        >
          {logs.length === 0 ? (
            <View style={styles.emptyState}>
              <Text style={styles.emptyIcon}>📭</Text>
              <Text style={styles.emptyTitle}>
                {t('notifications.noLogs', 'No logs found')}
              </Text>
              <Text style={styles.emptyMessage}>
                {t('notifications.noLogsDesc', 'Try adjusting your filters or pull to refresh')}
              </Text>
            </View>
          ) : (
            logs.map((log) => (
              <View key={log.id} style={styles.logCard}>
                <View style={styles.logHeader}>
                  <View
                    style={[
                      styles.statusBadge,
                      { backgroundColor: getStatusColor(log.status) },
                    ]}
                  >
                    <Text style={styles.statusBadgeText}>
                      {getStatusLabel(log.status)} {log.status}
                    </Text>
                  </View>
                  <Text style={styles.logTime}>
                    {formatDate(log.created_at)}
                  </Text>
                </View>

                <View style={styles.logDetails}>
                  <View style={styles.logDetailRow}>
                    <Text style={styles.logDetailLabel}>
                      {t('notifications.eventId', 'Event')}:
                    </Text>
                    <Text style={styles.logDetailValue}>
                      {log.event_id}
                    </Text>
                  </View>

                  {log.rule_id && (
                    <View style={styles.logDetailRow}>
                      <Text style={styles.logDetailLabel}>
                        {t('notifications.rule', 'Rule')}:
                      </Text>
                      <Text style={styles.logDetailValue}>
                        {log.rule_id}
                      </Text>
                    </View>
                  )}

                  {log.channel_id && (
                    <View style={styles.logDetailRow}>
                      <Text style={styles.logDetailLabel}>
                        {t('notifications.channel', 'Channel')}:
                      </Text>
                      <Text style={styles.logDetailValue}>
                        {log.channel_id}
                      </Text>
                    </View>
                  )}

                  <View style={styles.logDetailRow}>
                    <Text style={styles.logDetailLabel}>
                      {t('notifications.attempt', 'Attempt')}:
                    </Text>
                    <Text style={styles.logDetailValue}>
                      #{log.attempt}
                    </Text>
                  </View>

                  {(log.response_code || log.latency_ms) && (
                    <View style={styles.logDetailRow}>
                      <Text style={styles.logDetailLabel}>
                        {t('notifications.response', 'Response')}:
                      </Text>
                      <Text style={styles.logDetailValue}>
                        {log.response_code && `HTTP ${log.response_code}`}
                        {log.response_code && log.latency_ms && ' · '}
                        {log.latency_ms && `${log.latency_ms}ms`}
                      </Text>
                    </View>
                  )}

                  {log.error_message && (
                    <View style={styles.logDetailRow}>
                      <Text style={styles.logDetailLabel}>
                        {t('notifications.error', 'Error')}:
                      </Text>
                      <Text style={[styles.logDetailValue, styles.errorText]}>
                        {log.error_message}
                      </Text>
                    </View>
                  )}
                </View>
              </View>
            ))
          )}
        </ScrollView>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f9fafb',
  },
  // Header
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 16,
    backgroundColor: '#ffffff',
    borderBottomWidth: 1,
    borderBottomColor: '#e5e7eb',
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
    fontSize: 20,
    fontWeight: '700',
    color: '#111827',
  },
  headerSubtitle: {
    fontSize: 13,
    color: '#6b7280',
    marginTop: 2,
  },
  // Filter Section
  filterSection: {
    backgroundColor: '#ffffff',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#e5e7eb',
  },
  filterLabel: {
    fontSize: 13,
    fontWeight: '600',
    color: '#374151',
    marginBottom: 8,
  },
  filterButtons: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  filterButton: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
    borderWidth: 1,
    minHeight: 32,
    justifyContent: 'center',
  },
  filterButtonText: {
    fontSize: 11,
    fontWeight: '600',
  },
  // Loading
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    gap: 12,
  },
  loadingText: {
    fontSize: 14,
    color: '#6b7280',
  },
  // Logs Container
  logsContainer: {
    flex: 1,
  },
  logsContent: {
    padding: 16,
  },
  // Empty State
  emptyState: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 64,
    gap: 12,
  },
  emptyIcon: {
    fontSize: 48,
  },
  emptyTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#111827',
  },
  emptyMessage: {
    fontSize: 14,
    color: '#6b7280',
    textAlign: 'center',
    paddingHorizontal: 32,
  },
  // Log Card
  logCard: {
    backgroundColor: '#ffffff',
    borderRadius: 12,
    padding: 12,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 2,
    elevation: 1,
    borderWidth: 1,
    borderColor: '#e5e7eb',
  },
  logHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  statusBadge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 8,
  },
  statusBadgeText: {
    fontSize: 11,
    fontWeight: '600',
    color: '#ffffff',
  },
  logTime: {
    fontSize: 12,
    color: '#6b7280',
  },
  logDetails: {
    gap: 4,
  },
  logDetailRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
  },
  logDetailLabel: {
    fontSize: 12,
    color: '#6b7280',
    minWidth: 70,
  },
  logDetailValue: {
    fontSize: 12,
    color: '#1f2937',
    flex: 1,
  },
  errorText: {
    color: '#ef4444',
  },
});

export default NotificationsScreen;
