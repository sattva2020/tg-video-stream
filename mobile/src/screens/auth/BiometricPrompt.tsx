/**
 * Biometric Prompt Screen
 *
 * Screen shown after successful login to offer biometric authentication setup.
 * Allows users to enable Face ID, Touch ID, or fingerprint for quick re-authentication.
 *
 * Features:
 * - Display available biometric type
 * - Enable/disable biometric authentication
 * - Skip option for users who don't want biometrics
 * - Clear explanation of benefits
 */

import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  SafeAreaView,
} from 'react-native';
import { useTranslation } from 'react-i18next';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import type { AuthStackParamList, RootStackParamList } from '../../navigation/types';
import {
  getBiometricType,
  getBiometricTypeName,
  isBiometricAvailable,
  isBiometricEnrolled,
  authenticateWithBiometrics,
  enableBiometric,
} from '../../utils/biometricAuth';

type Props = NativeStackScreenProps<AuthStackParamList, 'BiometricPrompt'>;

interface BiometricPromptParams {
  email: string;
}

export const BiometricPromptScreen: React.FC<Props> = ({ navigation, route }) => {
  // Get the root navigator to navigate to Main (which is at root level, not in AuthStack)
  const rootNavigation = navigation.getParent() as any;
  const { t } = useTranslation();
  const params = route.params as BiometricPromptParams;

  const [biometricType, setBiometricType] = useState<'face' | 'fingerprint' | 'iris' | null>(null);
  const [isAvailable, setIsAvailable] = useState<boolean>(false);
  const [isEnrolled, setIsEnrolled] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isEnabling, setIsEnabling] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    checkBiometricSupport();
  }, []);

  const checkBiometricSupport = async () => {
    try {
      const [available, enrolled, type] = await Promise.all([
        isBiometricAvailable(),
        isBiometricEnrolled(),
        getBiometricType(),
      ]);

      setIsAvailable(available);
      setIsEnrolled(enrolled);
      setBiometricType(type);

      // If biometrics are not available or enrolled, auto-advance
      if (!available || !enrolled) {
        handleSkip();
      }
    } catch (error) {
      // On error, just skip biometric setup
      handleSkip();
    } finally {
      setIsLoading(false);
    }
  };

  const handleEnable = async () => {
    setErrorMessage(null);
    setIsEnabling(true);

    try {
      // First, authenticate with biometrics to verify it works
      const result = await authenticateWithBiometrics(
        `Authenticate to enable ${getBiometricTypeName(biometricType)}`
      );

      if (!result.success) {
        setErrorMessage(result.error || 'Authentication failed. Please try again.');
        setIsEnabling(false);
        return;
      }

      // Enable biometric for this user
      await enableBiometric(params.email);

      // Navigate to main app using the root navigator
      rootNavigation?.reset({
        index: 0,
        routes: [{ name: 'Main' }],
      });
    } catch (error: any) {
      setErrorMessage(error.message || 'Failed to enable biometric authentication');
      setIsEnabling(false);
    }
  };

  const handleSkip = () => {
    // Navigate to main app without enabling biometrics
    rootNavigation?.reset({
      index: 0,
      routes: [{ name: 'Main' }],
    });
  };

  const getBiometricIcon = () => {
    switch (biometricType) {
      case 'face':
        return '👤';
      case 'fingerprint':
        return '👆';
      case 'iris':
        return '👁️';
      default:
        return '🔒';
    }
  };

  if (isLoading) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#4f46e5" />
        </View>
      </SafeAreaView>
    );
  }

  if (!isAvailable || !isEnrolled) {
    // Auto-skip if biometrics not available
    return null;
  }

  const biometricName = getBiometricTypeName(biometricType);

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.content}>
        <View style={styles.iconContainer}>
          <Text style={styles.icon}>{getBiometricIcon()}</Text>
        </View>

        <View style={styles.textContainer}>
          <Text style={styles.title}>
            {t('auth.biometric.title', 'Enable {{biometric}}?', { biometric: biometricName })}
          </Text>

          <Text style={styles.description}>
            {t(
              'auth.biometric.description',
              'Use {{biometric}} for quick and secure access to your account.',
              { biometric: biometricName }
            )}
          </Text>

          <View style={styles.benefitsContainer}>
            <Text style={styles.benefitsTitle}>
              {t('auth.biometric.benefitsTitle', 'Benefits:')}
            </Text>
            <Text style={styles.benefitItem}>
              ✓ {t('auth.biometric.benefit1', 'Quick access - no password required')}
            </Text>
            <Text style={styles.benefitItem}>
              ✓ {t('auth.biometric.benefit2', 'Enhanced security with device authentication')}
            </Text>
            <Text style={styles.benefitItem}>
              ✓ {t('auth.biometric.benefit3', 'Your data stays secure on your device')}
            </Text>
          </View>

          <Text style={styles.privacyNote}>
            {t(
              'auth.biometric.privacyNote',
              'Your biometric data is stored securely by your device and is never shared with our servers.'
            )}
          </Text>
        </View>

        {errorMessage && (
          <View style={styles.errorContainer}>
            <Text style={styles.errorText}>{errorMessage}</Text>
          </View>
        )}

        <View style={styles.buttonContainer}>
          <TouchableOpacity
            style={[styles.button, styles.enableButton]}
            onPress={handleEnable}
            disabled={isEnabling}
          >
            {isEnabling ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={styles.enableButtonText}>
                {t('auth.biometric.enable', 'Enable {{biometric}}', { biometric: biometricName })}
              </Text>
            )}
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.button, styles.skipButton]}
            onPress={handleSkip}
            disabled={isEnabling}
          >
            <Text style={styles.skipButtonText}>
              {t('auth.biometric.skip', 'Not now')}
            </Text>
          </TouchableOpacity>
        </View>

        <View style={styles.footer}>
          <Text style={styles.footerText}>
            {t(
              'auth.biometric.footer',
              'You can enable this later in Settings if you change your mind.'
            )}
          </Text>
        </View>
      </View>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f9fafb',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  content: {
    flex: 1,
    padding: 24,
    justifyContent: 'center',
  },
  iconContainer: {
    alignItems: 'center',
    marginBottom: 32,
  },
  icon: {
    fontSize: 80,
  },
  textContainer: {
    marginBottom: 32,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#111827',
    textAlign: 'center',
    marginBottom: 16,
  },
  description: {
    fontSize: 16,
    color: '#4b5563',
    textAlign: 'center',
    marginBottom: 24,
    lineHeight: 24,
  },
  benefitsContainer: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: '#e5e7eb',
  },
  benefitsTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#374151',
    marginBottom: 12,
  },
  benefitItem: {
    fontSize: 14,
    color: '#6b7280',
    marginBottom: 8,
    lineHeight: 20,
  },
  privacyNote: {
    fontSize: 12,
    color: '#9ca3af',
    textAlign: 'center',
    fontStyle: 'italic',
  },
  errorContainer: {
    backgroundColor: '#fee2e2',
    borderColor: '#fecaca',
    borderWidth: 1,
    borderRadius: 8,
    padding: 12,
    marginBottom: 16,
  },
  errorText: {
    color: '#991b1b',
    fontSize: 14,
    textAlign: 'center',
  },
  buttonContainer: {
    gap: 12,
    marginBottom: 16,
  },
  button: {
    borderRadius: 12,
    paddingVertical: 16,
    alignItems: 'center',
  },
  enableButton: {
    backgroundColor: '#4f46e5',
  },
  enableButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  skipButton: {
    backgroundColor: 'transparent',
    borderWidth: 1,
    borderColor: '#d1d5db',
  },
  skipButtonText: {
    color: '#4b5563',
    fontSize: 16,
    fontWeight: '600',
  },
  footer: {
    alignItems: 'center',
  },
  footerText: {
    fontSize: 12,
    color: '#9ca3af',
    textAlign: 'center',
  },
});
