/**
 * Loading Spinner Component
 *
 * A reusable loading spinner component for inline loading states.
 * More compact than LoadingScreen, suitable for use within cards and lists.
 * Follows patterns from LoadingScreen.tsx and StreamCard.tsx
 */

import React from 'react';
import { View, ActivityIndicator, Text, StyleSheet, ViewStyle } from 'react-native';
import { useTranslation } from 'react-i18next';

interface LoadingSpinnerProps {
  size?: number | 'small' | 'large';
  color?: string;
  message?: string;
  style?: ViewStyle;
  fullScreen?: boolean;
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  size = 'small',
  color = '#06b6d4',
  message,
  style,
  fullScreen = false,
}) => {
  const { t } = useTranslation();

  if (fullScreen) {
    return (
      <View style={[styles.fullScreen, style]}>
        <ActivityIndicator size={size} color={color} />
        {message && (
          <Text style={styles.fullScreenMessage}>
            {message || t('common.loading', 'Loading...')}
          </Text>
        )}
      </View>
    );
  }

  return (
    <View style={[styles.container, style]}>
      <ActivityIndicator size={size} color={color} />
      {message && (
        <Text style={styles.message}>
          {message || t('common.loading', 'Loading...')}
        </Text>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 16,
    paddingHorizontal: 20,
    gap: 12,
  },
  message: {
    fontSize: 14,
    color: '#6b7280',
    marginLeft: 8,
  },
  fullScreen: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#ffffff',
    gap: 16,
  },
  fullScreenMessage: {
    fontSize: 16,
    color: '#6b7280',
    marginTop: 12,
    textAlign: 'center',
  },
});
