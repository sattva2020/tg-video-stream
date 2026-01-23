/**
 * Empty State Component
 *
 * A reusable component for displaying empty states (no data).
 * Provides user-friendly messaging and optional actions.
 * Follows patterns from StreamCard.tsx and mobile UI patterns
 */

import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ViewStyle,
  ImageStyle,
} from 'react-native';
import { useTranslation } from 'react-i18next';

interface EmptyStateProps {
  icon?: string;
  title?: string;
  message?: string;
  actionLabel?: string;
  onAction?: () => void;
  style?: ViewStyle;
  iconStyle?: ImageStyle;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon = '📭',
  title,
  message,
  actionLabel,
  onAction,
  style,
  iconStyle,
}) => {
  const { t } = useTranslation();

  const displayTitle = title || t('common.noData', 'No Data');
  const displayMessage = message || t('common.noDataDesc', 'There is nothing to display yet');
  const displayActionLabel = actionLabel || t('common.refresh', 'Refresh');

  return (
    <View style={[styles.container, style]}>
      <View style={[styles.iconContainer, iconStyle]}>
        <Text style={styles.icon}>{icon}</Text>
      </View>

      <Text style={styles.title}>{displayTitle}</Text>

      <Text style={styles.message}>{displayMessage}</Text>

      {onAction && (
        <TouchableOpacity
          style={styles.actionButton}
          onPress={onAction}
          activeOpacity={0.7}
          hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
        >
          <Text style={styles.actionButtonText}>{displayActionLabel}</Text>
        </TouchableOpacity>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: 48,
    paddingHorizontal: 32,
    backgroundColor: '#ffffff',
    gap: 12,
  },
  iconContainer: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: '#f3f4f6',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 8,
  },
  icon: {
    fontSize: 40,
  },
  title: {
    fontSize: 18,
    fontWeight: '600',
    color: '#111827',
    textAlign: 'center',
  },
  message: {
    fontSize: 14,
    color: '#6b7280',
    textAlign: 'center',
    lineHeight: 20,
    maxWidth: 280,
  },
  actionButton: {
    marginTop: 16,
    paddingHorizontal: 24,
    paddingVertical: 12,
    backgroundColor: '#06b6d4',
    borderRadius: 12,
    minHeight: 44, // Ensure adequate touch target
    justifyContent: 'center',
    alignItems: 'center',
  },
  actionButtonText: {
    fontSize: 15,
    fontWeight: '600',
    color: '#ffffff',
  },
});
