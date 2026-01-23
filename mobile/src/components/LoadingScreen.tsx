/**
 * Loading Screen
 *
 * Reusable loading screen component for displaying loading states.
 * Follows patterns from frontend/src/components LoadingFallback
 */

import React from 'react';
import { View, ActivityIndicator, Text, StyleSheet } from 'react-native';
import { useTranslation } from 'react-i18next';

interface LoadingScreenProps {
  message?: string;
  size?: number | 'small' | 'large';
}

export const LoadingScreen: React.FC<LoadingScreenProps> = ({
  message,
  size = 'large',
}) => {
  const { t } = useTranslation();

  return (
    <View style={styles.container}>
      <ActivityIndicator size={size} color="#06b6d4" />
      <Text style={styles.loadingText}>
        {message || t('common.loading', 'Загрузка...')}
      </Text>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#fff',
  },
  loadingText: {
    marginTop: 16,
    fontSize: 16,
    color: '#6b7280',
  },
});
