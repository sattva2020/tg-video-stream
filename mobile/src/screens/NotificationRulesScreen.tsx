/**
 * Notification Rules Screen
 *
 * Mobile-optimized screen for managing notification rules.
 * Follows patterns from frontend/src/pages/notifications/Rules.tsx adapted for React Native.
 *
 * Features:
 * - List all notification rules with toggle enable/disable
 * - View rule details (channels, recipients, filters)
 * - Create, edit, and delete rules
 * - Pull-to-refresh for latest rules
 */

import React, { useState, useCallback } from 'react';
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
import { notificationsApi, NotificationRule } from '../api/notifications';

// Types
import type { StackNavigationProp } from '@react-navigation/stack';

interface NavigationProps {
  navigation: StackNavigationProp<any>;
}

const NotificationRulesScreen: React.FC<NavigationProps> = ({ navigation }) => {
  const { t } = useTranslation();

  // State
  const [rules, setRules] = useState<NotificationRule[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  // Fetch rules
  const fetchRules = useCallback(async () => {
    try {
      const data = await notificationsApi.listRules();
      setRules(data);
    } catch (error) {
      console.error('Failed to fetch notification rules:', error);
      Alert.alert(
        t('common.error', 'Error'),
        t('errors.somethingWentWrong', 'Something went wrong')
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [t]);

  // Load data when screen comes into focus
  useFocusEffect(
    useCallback(() => {
      setLoading(true);
      fetchRules();
    }, [fetchRules])
  );

  // Pull-to-refresh
  const onRefresh = useCallback(() => {
    setRefreshing(true);
    fetchRules();
  }, [fetchRules]);

  // Toggle rule enabled/disabled
  const handleToggleRule = async (rule: NotificationRule) => {
    setActionLoading(rule.id);
    try {
      await notificationsApi.updateRule(rule.id, { enabled: !rule.enabled });
      // Update local state
      setRules((prev) =>
        prev.map((r) =>
          r.id === rule.id ? { ...r, enabled: !r.enabled } : r
        )
      );
    } catch (error) {
      console.error('Failed to toggle rule:', error);
      Alert.alert(
        t('common.error', 'Error'),
        t('notifications.ruleUpdateFailed', 'Failed to update rule')
      );
    } finally {
      setActionLoading(null);
    }
  };

  // Delete rule with confirmation
  const handleDeleteRule = (rule: NotificationRule) => {
    Alert.alert(
      t('notifications.confirmDelete', 'Delete Rule?'),
      t('notifications.confirmDeleteMessage', 'Are you sure you want to delete "{{name}}"?', {
        name: rule.name,
      }),
      [
        {
          text: t('common.cancel', 'Cancel'),
          style: 'cancel',
        },
        {
          text: t('common.delete', 'Delete'),
          style: 'destructive',
          onPress: async () => {
            setActionLoading(rule.id);
            try {
              await notificationsApi.deleteRule(rule.id);
              // Remove from local state
              setRules((prev) => prev.filter((r) => r.id !== rule.id));
              Alert.alert(
                t('common.success', 'Success'),
                t('notifications.ruleDeleted', 'Rule deleted')
              );
            } catch (error) {
              console.error('Failed to delete rule:', error);
              Alert.alert(
                t('common.error', 'Error'),
                t('notifications.ruleDeleteFailed', 'Failed to delete rule')
              );
            } finally {
              setActionLoading(null);
            }
          },
        },
      ]
    );
  };

  // Navigate to create/edit screen (placeholder for now)
  const handleEditRule = (rule?: NotificationRule) => {
    // TODO: Implement rule creation/editing screen
    Alert.alert(
      t('notifications.comingSoon', 'Coming Soon'),
      rule
        ? t('notifications.editRuleDesc', 'Rule editing will be available soon')
        : t('notifications.createRuleDesc', 'Rule creation will be available soon')
    );
  };

  // Get filter badges
  const getFilterBadges = (rule: NotificationRule) => {
    const badges = [];

    if (rule.severity_filter && Object.keys(rule.severity_filter).length > 0) {
      badges.push({
        label: 'Severity',
        color: '#a855f7',
        bgColor: 'rgba(168, 85, 247, 0.15)',
      });
    }

    if (rule.tag_filter && Object.keys(rule.tag_filter).length > 0) {
      badges.push({
        label: 'Tags',
        color: '#3b82f6',
        bgColor: 'rgba(59, 130, 246, 0.15)',
      });
    }

    if (rule.host_filter && Object.keys(rule.host_filter).length > 0) {
      badges.push({
        label: 'Hosts',
        color: '#10b981',
        bgColor: 'rgba(16, 185, 129, 0.15)',
      });
    }

    return badges;
  };

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <View style={styles.headerLeft}>
          <View style={styles.headerIconContainer}>
            <Text style={styles.headerIcon}>⚙️</Text>
          </View>
          <View>
            <Text style={styles.headerTitle}>
              {t('notifications.rules', 'Rules')}
            </Text>
            <Text style={styles.headerSubtitle}>
              {t('notifications.rulesSubtitle', 'Manage notification routing rules')}
            </Text>
          </View>
        </View>

        {/* Add button */}
        <TouchableOpacity
          style={styles.addButton}
          onPress={() => handleEditRule()}
          activeOpacity={0.7}
        >
          <Text style={styles.addButtonText}>+</Text>
        </TouchableOpacity>
      </View>

      {/* Rules List */}
      {loading ? (
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#06b6d4" />
          <Text style={styles.loadingText}>
            {t('common.loading', 'Loading...')}
          </Text>
        </View>
      ) : (
        <ScrollView
          style={styles.rulesContainer}
          contentContainerStyle={styles.rulesContent}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={onRefresh}
              tintColor="#06b6d4"
              colors={['#06b6d4']}
            />
          }
        >
          {rules.length === 0 ? (
            <View style={styles.emptyState}>
              <Text style={styles.emptyIcon}>📋</Text>
              <Text style={styles.emptyTitle}>
                {t('notifications.noRules', 'No rules yet')}
              </Text>
              <Text style={styles.emptyMessage}>
                {t('notifications.noRulesDesc', 'Create your first rule to start receiving notifications')}
              </Text>
              <TouchableOpacity
                style={styles.createButton}
                onPress={() => handleEditRule()}
                activeOpacity={0.7}
              >
                <Text style={styles.createButtonText}>
                  {t('notifications.createFirstRule', 'Create First Rule')}
                </Text>
              </TouchableOpacity>
            </View>
          ) : (
            rules.map((rule) => {
              const badges = getFilterBadges(rule);
              const isLoading = actionLoading === rule.id;

              return (
                <View
                  key={rule.id}
                  style={[
                    styles.ruleCard,
                    !rule.enabled && styles.ruleCardDisabled,
                  ]}
                >
                  {/* Rule Header */}
                  <View style={styles.ruleHeader}>
                    <View style={styles.ruleInfo}>
                      <Text style={styles.ruleName}>{rule.name}</Text>
                      <View style={styles.ruleStats}>
                        <Text style={styles.ruleStatText}>
                          {t('notifications.channels', 'Channels')}: {rule.channel_ids.length} ·{' '}
                          {t('notifications.recipients', 'Recipients')}: {rule.recipient_ids.length}
                        </Text>
                      </View>
                      <View style={styles.ruleStats}>
                        <Text style={styles.ruleStatText}>
                          Failover: {rule.failover_timeout_sec}s · Dedup: {rule.dedup_window_sec}s
                        </Text>
                      </View>
                      {!rule.enabled && (
                        <Text style={styles.disabledText}>
                          {t('notifications.ruleDisabled', 'Rule disabled')}
                        </Text>
                      )}
                    </View>

                    {/* Action Buttons */}
                    <View style={styles.actionButtons}>
                      <TouchableOpacity
                        style={[
                          styles.toggleButton,
                          {
                            backgroundColor: rule.enabled
                              ? '#06b6d4'
                              : '#d1d5db',
                          },
                        ]}
                        onPress={() => handleToggleRule(rule)}
                        disabled={isLoading}
                        activeOpacity={0.7}
                      >
                        <Text
                          style={[
                            styles.toggleButtonText,
                            { color: rule.enabled ? '#ffffff' : '#6b7280' },
                          ]}
                        >
                          {isLoading ? '...' : rule.enabled ? 'ON' : 'OFF'}
                        </Text>
                      </TouchableOpacity>

                      <TouchableOpacity
                        style={styles.iconButton}
                        onPress={() => handleEditRule(rule)}
                        disabled={isLoading}
                        activeOpacity={0.7}
                      >
                        <Text style={styles.iconButtonText}>✏️</Text>
                      </TouchableOpacity>

                      <TouchableOpacity
                        style={[styles.iconButton, styles.deleteButton]}
                        onPress={() => handleDeleteRule(rule)}
                        disabled={isLoading}
                        activeOpacity={0.7}
                      >
                        <Text style={styles.iconButtonText}>🗑️</Text>
                      </TouchableOpacity>
                    </View>
                  </View>

                  {/* Filter Badges */}
                  {badges.length > 0 && (
                    <View style={styles.badgesContainer}>
                      {badges.map((badge, index) => (
                        <View
                          key={index}
                          style={[
                            styles.badge,
                            { backgroundColor: badge.bgColor, borderColor: badge.color },
                          ]}
                        >
                          <Text style={[styles.badgeText, { color: badge.color }]}>
                            {badge.label}
                          </Text>
                        </View>
                      ))}
                    </View>
                  )}
                </View>
              );
            })
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
    flex: 1,
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
  addButton: {
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
  addButtonText: {
    fontSize: 24,
    color: '#ffffff',
    fontWeight: '300',
    lineHeight: 28,
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
  // Rules Container
  rulesContainer: {
    flex: 1,
  },
  rulesContent: {
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
  createButton: {
    backgroundColor: '#06b6d4',
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 12,
    marginTop: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 2,
  },
  createButtonText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#ffffff',
  },
  // Rule Card
  ruleCard: {
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
  ruleCardDisabled: {
    opacity: 0.6,
  },
  ruleHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 8,
  },
  ruleInfo: {
    flex: 1,
    gap: 4,
  },
  ruleName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#111827',
  },
  ruleStats: {
    marginTop: 2,
  },
  ruleStatText: {
    fontSize: 12,
    color: '#6b7280',
  },
  disabledText: {
    fontSize: 12,
    color: '#f59e0b',
    marginTop: 4,
  },
  actionButtons: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginLeft: 12,
  },
  toggleButton: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
    minWidth: 56,
    alignItems: 'center',
  },
  toggleButtonText: {
    fontSize: 11,
    fontWeight: '700',
  },
  iconButton: {
    width: 36,
    height: 36,
    borderRadius: 8,
    backgroundColor: '#f3f4f6',
    justifyContent: 'center',
    alignItems: 'center',
  },
  deleteButton: {
    backgroundColor: '#fef2f2',
  },
  iconButtonText: {
    fontSize: 16,
  },
  // Badges
  badgesContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
  },
  badge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
    borderWidth: 1,
  },
  badgeText: {
    fontSize: 11,
    fontWeight: '600',
  },
});

export default NotificationRulesScreen;
