/**
 * Error State Component
 *
 * A reusable component for displaying error states.
 * Provides user-friendly error messages and retry actions.
 * Follows patterns from StreamCard.tsx error section and mobile UI patterns
 */

import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  ViewStyle,
} from 'react-native';
import { useTranslation } from 'react-i18next';

export type ErrorSeverity = 'low' | 'medium' | 'high';

interface ErrorStateProps {
  title?: string;
  message?: string;
  error?: Error | string | null;
  retryLabel?: string;
  onRetry?: () => void;
  severity?: ErrorSeverity;
  style?: ViewStyle;
  scrollable?: boolean;
}

const getErrorConfig = (severity: ErrorSeverity) => {
  switch (severity) {
    case 'low':
      return {
        icon: 'ℹ️',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        borderColor: 'rgba(59, 130, 246, 0.2)',
        textColor: '#1e40af',
        iconColor: '#3b82f6',
      };
    case 'high':
      return {
        icon: '🚨',
        backgroundColor: 'rgba(239, 68, 68, 0.1)',
        borderColor: 'rgba(239, 68, 68, 0.2)',
        textColor: '#b91c1c',
        iconColor: '#ef4444',
      };
    case 'medium':
    default:
      return {
        icon: '⚠️',
        backgroundColor: 'rgba(245, 158, 11, 0.1)',
        borderColor: 'rgba(245, 158, 11, 0.2)',
        textColor: '#b45309',
        iconColor: '#f59e0b',
      };
  }
};

export const ErrorState: React.FC<ErrorStateProps> = ({
  title,
  message,
  error,
  retryLabel,
  onRetry,
  severity = 'medium',
  style,
  scrollable = false,
}) => {
  const { t } = useTranslation();

  const config = getErrorConfig(severity);

  const displayTitle = title || t('common.error', 'Error');
  const displayMessage =
    message ||
    (typeof error === 'string' ? error : error?.message) ||
    t('errors.somethingWentWrong', 'Something went wrong. Please try again.');
  const displayRetryLabel = retryLabel || t('common.retry', 'Retry');

  const content = (
    <View style={[styles.container, style]}>
      <View
        style={[
          styles.iconContainer,
          {
            backgroundColor: config.backgroundColor,
            borderColor: config.borderColor,
          },
        ]}
      >
        <Text style={[styles.icon, { color: config.iconColor }]}>{config.icon}</Text>
      </View>

      <Text style={[styles.title, { color: config.textColor }]}>{displayTitle}</Text>

      <Text style={styles.message}>{displayMessage}</Text>

      {onRetry && (
        <TouchableOpacity
          style={[styles.retryButton, { borderColor: config.borderColor }]}
          onPress={onRetry}
          activeOpacity={0.7}
          hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
        >
          <Text style={[styles.retryButtonText, { color: config.iconColor }]}>
            {displayRetryLabel}
          </Text>
        </TouchableOpacity>
      )}
    </View>
  );

  if (scrollable) {
    return (
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        bounces={false}
      >
        {content}
      </ScrollView>
    );
  }

  return content;
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
  scrollContent: {
    flexGrow: 1,
    justifyContent: 'center',
  },
  iconContainer: {
    width: 80,
    height: 80,
    borderRadius: 40,
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 2,
    marginBottom: 8,
  },
  icon: {
    fontSize: 40,
  },
  title: {
    fontSize: 18,
    fontWeight: '600',
    textAlign: 'center',
  },
  message: {
    fontSize: 14,
    color: '#6b7280',
    textAlign: 'center',
    lineHeight: 20,
    maxWidth: 280,
  },
  retryButton: {
    marginTop: 16,
    paddingHorizontal: 24,
    paddingVertical: 12,
    backgroundColor: 'transparent',
    borderRadius: 12,
    borderWidth: 2,
    minHeight: 44, // Ensure adequate touch target
    justifyContent: 'center',
    alignItems: 'center',
  },
  retryButtonText: {
    fontSize: 15,
    fontWeight: '600',
  },
});
