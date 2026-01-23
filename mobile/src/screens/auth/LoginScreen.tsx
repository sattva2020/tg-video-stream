/**
 * Login Screen
 *
 * Screen for user authentication with email/password and OAuth options.
 * Follows patterns from frontend/src/pages/LoginPage.tsx
 *
 * Features:
 * - Email/password login
 * - Optional 2FA (TOTP) code input
 * - Google OAuth button (placeholder)
 * - Telegram OAuth button (placeholder)
 * - Form validation
 * - Error handling
 */

import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  Alert,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  ActivityIndicator,
} from 'react-native';
import { useTranslation } from 'react-i18next';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { useAuth } from '../../contexts/AuthContext';
import { authApi } from '../../api/auth';
import type { AuthStackParamList } from '../../navigation/types';

type Props = NativeStackScreenProps<AuthStackParamList, 'Login'>;

export const LoginScreen: React.FC<Props> = ({ navigation }) => {
  const { t } = useTranslation();
  const { login } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [totpCode, setTotpCode] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [showPassword, setShowPassword] = useState(false);

  const validateForm = (): boolean => {
    if (!email || !email.includes('@')) {
      setErrorMessage('Please enter a valid email address');
      return false;
    }
    if (!password) {
      setErrorMessage('Please enter your password');
      return false;
    }
    if (totpCode && totpCode.length !== 6) {
      setErrorMessage('2FA code must be 6 digits');
      return false;
    }
    return true;
  };

  const handleLogin = async () => {
    setErrorMessage(null);

    if (!validateForm()) {
      return;
    }

    setIsLoading(true);

    try {
      const response = await authApi.login({
        email,
        password,
        totp_code: totpCode || undefined,
      });

      // Save token and update auth state
      await login(response.access_token);

      // Navigate to biometric prompt screen
      // This screen will offer to enable biometric auth, then navigate to main app
      navigation.navigate('BiometricPrompt', { email });
    } catch (error: any) {
      setIsLoading(false);

      if (error.response?.status === 401) {
        const detail = error.response?.data?.detail;
        if (typeof detail === 'string' && detail.toLowerCase().includes('totp')) {
          setErrorMessage('Введите одноразовый код 2FA из приложения.');
        } else {
          setErrorMessage('Invalid email or password.');
        }
      } else if (error.response?.status === 423) {
        setErrorMessage('Слишком много попыток. Попробуйте позже.');
      } else if (error.response?.status === 403) {
        const detail = error.response?.data?.detail;
        if (detail?.code === 'pending') {
          // Navigate to pending approval screen
          navigation.navigate('PendingApproval');
          return;
        }
        setErrorMessage('Your account is pending approval or has been rejected.');
      } else {
        setErrorMessage('Login failed. Please try again later.');
      }
    }
  };

  const handleGoogleLogin = () => {
    // TODO: Implement Google OAuth
    // This will require expo-google-app-auth or @react-native-google-signin/google-signin
    Alert.alert('Coming Soon', 'Google login will be implemented in a future update.');
  };

  const handleTelegramLogin = () => {
    // TODO: Implement Telegram OAuth
    // This will require WebBrowser or AuthSession for OAuth flow
    Alert.alert('Coming Soon', 'Telegram login will be implemented in a future update.');
  };

  const handleForgotPassword = () => {
    // TODO: Navigate to password reset screen
    Alert.alert('Coming Soon', 'Password reset will be implemented in a future update.');
  };

  const handleRegister = () => {
    // TODO: Navigate to registration screen
    Alert.alert('Coming Soon', 'Registration will be implemented in a future update.');
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        keyboardShouldPersistTaps="handled"
      >
        <View style={styles.header}>
          <Text style={styles.title}>{t('auth.login.title', 'Sign in to your account')}</Text>
          <Text style={styles.subtitle}>
            {t('auth.login.noAccount', 'Or')}{' '}
            <Text style={styles.link} onPress={handleRegister}>
              {t('auth.login.createAccount', 'create a new account')}
            </Text>
          </Text>
        </View>

        {errorMessage && (
          <View style={styles.errorBox}>
            <Text style={styles.errorText}>{errorMessage}</Text>
          </View>
        )}

        <View style={styles.form}>
          <View style={styles.inputGroup}>
            <Text style={styles.label}>
              {t('auth.login.emailLabel', 'Email address')}
            </Text>
            <TextInput
              style={styles.input}
              value={email}
              onChangeText={setEmail}
              placeholder="your@email.com"
              autoCapitalize="none"
              autoComplete="email"
              keyboardType="email-address"
              textContentType="emailAddress"
              editable={!isLoading}
            />
          </View>

          <View style={styles.inputGroup}>
            <Text style={styles.label}>
              {t('auth.login.passwordLabel', 'Password')}
            </Text>
            <View style={styles.passwordContainer}>
              <TextInput
                style={styles.passwordInput}
                value={password}
                onChangeText={setPassword}
                placeholder="••••••••"
                autoCapitalize="none"
                autoComplete="password"
                textContentType="password"
                secureTextEntry={!showPassword}
                editable={!isLoading}
              />
              <TouchableOpacity
                style={styles.eyeIcon}
                onPress={() => setShowPassword(!showPassword)}
              >
                <Text style={styles.eyeIconText}>{showPassword ? '👁️' : '👁️‍🗨️'}</Text>
              </TouchableOpacity>
            </View>
          </View>

          <View style={styles.inputGroup}>
            <Text style={styles.label}>
              {t('auth.login.totpLabel', '2FA code (if enabled)')}
            </Text>
            <TextInput
              style={styles.input}
              value={totpCode}
              onChangeText={(text) => {
                // Only allow digits, max 6 characters
                const filtered = text.replace(/\D/g, '').slice(0, 6);
                setTotpCode(filtered);
              }}
              placeholder="123456"
              autoCapitalize="none"
              autoComplete="one-time-code"
              keyboardType="number-pad"
              textContentType="oneTimeCode"
              maxLength={6}
              editable={!isLoading}
            />
            <Text style={styles.hintText}>
              {t(
                'auth.login.totpHint',
                'Enter code from Google Authenticator/1Password if 2FA is enabled.'
              )}
            </Text>
          </View>

          <TouchableOpacity
            style={[styles.submitButton, isLoading && styles.submitButtonDisabled]}
            onPress={handleLogin}
            disabled={isLoading}
          >
            {isLoading ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={styles.submitButtonText}>
                {t('auth.login.signIn', 'Sign in')}
              </Text>
            )}
          </TouchableOpacity>

          <TouchableOpacity onPress={handleForgotPassword}>
            <Text style={styles.forgotPassword}>
              {t('auth.login.forgotPassword', 'Forgot your password?')}
            </Text>
          </TouchableOpacity>
        </View>

        <View style={styles.divider}>
          <View style={styles.dividerLine} />
          <Text style={styles.dividerText}>
            {t('auth.login.orContinue', 'Or continue with')}
          </Text>
          <View style={styles.dividerLine} />
        </View>

        <View style={styles.oauthButtons}>
          <TouchableOpacity
            style={[styles.oauthButton, styles.googleButton]}
            onPress={handleGoogleLogin}
            disabled={isLoading}
          >
            <Text style={styles.oauthButtonText}>G</Text>
            <Text style={styles.oauthButtonLabel}>
              {t('auth.login.continueWithGoogle', 'Continue with Google')}
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.oauthButton, styles.telegramButton]}
            onPress={handleTelegramLogin}
            disabled={isLoading}
          >
            <Text style={styles.oauthButtonText}>✈️</Text>
            <Text style={styles.oauthButtonLabel}>
              {t('auth.login.continueWithTelegram', 'Continue with Telegram')}
            </Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f9fafb',
  },
  scrollContent: {
    flexGrow: 1,
    padding: 24,
    justifyContent: 'center',
  },
  header: {
    marginBottom: 24,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#111827',
    textAlign: 'center',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 14,
    color: '#6b7280',
    textAlign: 'center',
  },
  link: {
    color: '#4f46e5',
    fontWeight: '600',
  },
  errorBox: {
    backgroundColor: '#fee2e2',
    borderColor: '#fecaca',
    borderWidth: 1,
    borderRadius: 8,
    padding: 12,
    marginBottom: 24,
  },
  errorText: {
    color: '#991b1b',
    fontSize: 14,
    textAlign: 'center',
  },
  form: {
    marginBottom: 24,
  },
  inputGroup: {
    marginBottom: 16,
  },
  label: {
    fontSize: 14,
    fontWeight: '600',
    color: '#374151',
    marginBottom: 6,
  },
  input: {
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: '#d1d5db',
    borderRadius: 8,
    paddingHorizontal: 16,
    paddingVertical: 12,
    fontSize: 16,
    color: '#111827',
  },
  passwordContainer: {
    flexDirection: 'row',
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: '#d1d5db',
    borderRadius: 8,
    alignItems: 'center',
  },
  passwordInput: {
    flex: 1,
    paddingHorizontal: 16,
    paddingVertical: 12,
    fontSize: 16,
    color: '#111827',
  },
  eyeIcon: {
    paddingHorizontal: 16,
    paddingVertical: 12,
  },
  eyeIconText: {
    fontSize: 18,
  },
  hintText: {
    fontSize: 12,
    color: '#6b7280',
    marginTop: 4,
  },
  submitButton: {
    backgroundColor: '#4f46e5',
    borderRadius: 8,
    paddingVertical: 14,
    alignItems: 'center',
    marginTop: 8,
    marginBottom: 16,
  },
  submitButtonDisabled: {
    opacity: 0.5,
  },
  submitButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  forgotPassword: {
    color: '#4f46e5',
    fontSize: 14,
    textAlign: 'center',
    fontWeight: '600',
  },
  divider: {
    flexDirection: 'row',
    alignItems: 'center',
    marginVertical: 24,
  },
  dividerLine: {
    flex: 1,
    height: 1,
    backgroundColor: '#d1d5db',
  },
  dividerText: {
    paddingHorizontal: 12,
    fontSize: 14,
    color: '#6b7280',
  },
  oauthButtons: {
    gap: 12,
  },
  oauthButton: {
    flexDirection: 'row',
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: '#d1d5db',
    borderRadius: 8,
    paddingVertical: 12,
    paddingHorizontal: 16,
    alignItems: 'center',
    justifyContent: 'center',
  },
  googleButton: {
    borderColor: '#d1d5db',
  },
  telegramButton: {
    borderColor: '#d1d5db',
  },
  oauthButtonText: {
    fontSize: 18,
    marginRight: 12,
  },
  oauthButtonLabel: {
    fontSize: 16,
    fontWeight: '600',
    color: '#374151',
  },
});
