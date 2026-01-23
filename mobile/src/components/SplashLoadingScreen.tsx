/**
 * Splash Loading Screen
 *
 * Loading screen shown during app initialization and authentication checks.
 * Follows patterns from frontend/src/components LoadingFallback
 */

import React from 'react';
import { View, ActivityIndicator, Text, StyleSheet } from 'react-native';
import { useTranslation } from 'react-i18next';

export const SplashLoadingScreen: React.FC = () => {
  const { t } = useTranslation();

  return (
    <View style={styles.container}>
      <ActivityIndicator size="large" color="#06b6d4" />
      <Text style={styles.loadingText}>
        {t('common.loading', 'Загрузка...')}
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
