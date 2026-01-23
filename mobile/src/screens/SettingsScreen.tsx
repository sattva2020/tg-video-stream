/**
 * Settings Screen
 *
 * Main settings screen with language selector and theme toggle.
 * Follows patterns from frontend/src/pages/SettingsPage.tsx
 *
 * Features:
 * - Language selection with immediate effect
 * - Theme toggle (light/dark/system)
 * - Profile section
 * - App version info
 * - Mobile-optimized layout
 */

import React, { useState, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Alert,
  NativeModules,
  Platform,
} from 'react-native';
import { useTranslation } from 'react-i18next';
import { useTheme } from '../contexts/ThemeContext';
import { useAuth } from '../contexts/AuthContext';
import { changeLanguage, getSupportedLanguages } from '../i18n';
import { LanguageSelector } from '../components/LanguageSelector';
import { ThemeToggle } from '../components/ThemeToggle';

const APP_VERSION = '1.0.0';
const APP_BUILD = '2025.01.23';

const SettingsScreen: React.FC = () => {
  const { t } = useTranslation();
  const { theme, resolvedTheme } = useTheme();
  const { user, logout } = useAuth();
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  // Get current language
  const currentLang = t('settings.language', 'Language');

  // Handle language change
  const handleLanguageChange = useCallback(async (languageCode: string) => {
    try {
      await changeLanguage(languageCode);
      Alert.alert(
        t('common.success', 'Success'),
        t('settings.languageChanged', 'Language changed successfully')
      );
    } catch (error) {
      Alert.alert(
        t('common.error', 'Error'),
        t('errors.somethingWentWrong', 'Something went wrong')
      );
    }
  }, [t]);

  // Handle logout
  const handleLogout = useCallback(() => {
    Alert.alert(
      t('settings.logout', 'Log Out'),
      t('settings.confirmLogout', 'Are you sure you want to log out?'),
      [
        {
          text: t('common.cancel', 'Cancel'),
          style: 'cancel',
        },
        {
          text: t('settings.logout', 'Log Out'),
          style: 'destructive',
          onPress: async () => {
            setIsLoggingOut(true);
            try {
              await logout();
            } catch (error) {
              setIsLoggingOut(false);
              Alert.alert(
                t('common.error', 'Error'),
                t('errors.somethingWentWrong', 'Something went wrong')
              );
            }
          },
        },
      ]
    );
  }, [t, logout]);

  const isDark = resolvedTheme === 'dark';

  return (
    <ScrollView
      style={[styles.container, isDark && styles.containerDark]}
      contentContainerStyle={styles.contentContainer}
    >
      {/* Profile Section */}
      <View style={[styles.section, isDark && styles.sectionDark]}>
        <Text style={[styles.sectionTitle, isDark && styles.textLight]}>
          {t('settings.profile', 'Profile')}
        </Text>
        <View style={[styles.card, isDark && styles.cardDark]}>
          <View style={styles.profileContainer}>
            <View style={[styles.avatar, isDark && styles.avatarDark]}>
              <Text style={styles.avatarText}>
                {user?.full_name?.charAt(0).toUpperCase() || user?.email?.charAt(0).toUpperCase() || 'U'}
              </Text>
            </View>
            <View style={styles.profileInfo}>
              <Text style={[styles.profileName, isDark && styles.textLight]}>
                {user?.full_name || t('common.user', 'User')}
              </Text>
              <Text style={[styles.profileEmail, isDark && styles.textSecondary]}>
                {user?.email || t('settings.noEmail', 'No email')}
              </Text>
            </View>
          </View>
        </View>
      </View>

      {/* Appearance Section */}
      <View style={[styles.section, isDark && styles.sectionDark]}>
        <Text style={[styles.sectionTitle, isDark && styles.textLight]}>
          {t('settings.preferences', 'Preferences')}
        </Text>

        {/* Theme Toggle */}
        <View style={[styles.card, styles.cardWithMargin, isDark && styles.cardDark]}>
          <Text style={[styles.cardLabel, isDark && styles.textLight]}>
            {t('settings.theme', 'Theme')}
          </Text>
          <ThemeToggle />
        </View>

        {/* Language Selector */}
        <View style={[styles.card, isDark && styles.cardDark]}>
          <Text style={[styles.cardLabel, isDark && styles.textLight]}>
            {t('settings.language', 'Language')}
          </Text>
          <LanguageSelector
            currentLanguage={currentLang}
            onLanguageChange={handleLanguageChange}
          />
        </View>
      </View>

      {/* About Section */}
      <View style={[styles.section, isDark && styles.sectionDark]}>
        <Text style={[styles.sectionTitle, isDark && styles.textLight]}>
          {t('settings.about', 'About')}
        </Text>
        <View style={[styles.card, isDark && styles.cardDark]}>
          <View style={styles.aboutRow}>
            <Text style={[styles.aboutLabel, isDark && styles.textSecondary]}>
              {t('settings.version', 'Version')}
            </Text>
            <Text style={[styles.aboutValue, isDark && styles.textLight]}>
              {APP_VERSION}
            </Text>
          </View>
          <View style={styles.aboutRow}>
            <Text style={[styles.aboutLabel, isDark && styles.textSecondary]}>
              Build
            </Text>
            <Text style={[styles.aboutValue, isDark && styles.textLight]}>
              {APP_BUILD}
            </Text>
          </View>
        </View>
      </View>

      {/* Logout Button */}
      <TouchableOpacity
        style={[styles.logoutButton, isDark && styles.logoutButtonDark]}
        onPress={handleLogout}
        disabled={isLoggingOut}
        activeOpacity={0.7}
      >
        <Text style={styles.logoutButtonText}>
          {isLoggingOut ? '...' : t('settings.logout', 'Log Out')}
        </Text>
      </TouchableOpacity>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f9fafb',
  },
  containerDark: {
    backgroundColor: '#111827',
  },
  contentContainer: {
    padding: 16,
    paddingBottom: 32,
  },
  // Section
  section: {
    marginBottom: 24,
  },
  sectionDark: {
    backgroundColor: 'transparent',
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#111827',
    marginBottom: 12,
    marginLeft: 4,
  },
  // Card
  card: {
    backgroundColor: '#ffffff',
    borderRadius: 16,
    padding: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 3,
  },
  cardDark: {
    backgroundColor: '#1f2937',
  },
  cardWithMargin: {
    marginBottom: 12,
  },
  cardLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#374151',
    marginBottom: 12,
  },
  // Profile
  profileContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  avatar: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: '#06b6d4',
    justifyContent: 'center',
    alignItems: 'center',
  },
  avatarDark: {
    backgroundColor: '#0891b2',
  },
  avatarText: {
    fontSize: 24,
    fontWeight: '700',
    color: '#ffffff',
  },
  profileInfo: {
    flex: 1,
  },
  profileName: {
    fontSize: 18,
    fontWeight: '600',
    color: '#111827',
    marginBottom: 2,
  },
  profileEmail: {
    fontSize: 14,
    color: '#6b7280',
  },
  // About
  aboutRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 4,
  },
  aboutLabel: {
    fontSize: 14,
    color: '#6b7280',
  },
  aboutValue: {
    fontSize: 14,
    fontWeight: '600',
    color: '#111827',
  },
  // Logout
  logoutButton: {
    backgroundColor: '#ef4444',
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 2,
  },
  logoutButtonDark: {
    backgroundColor: '#dc2626',
  },
  logoutButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#ffffff',
  },
  // Text colors
  textLight: {
    color: '#f9fafb',
  },
  textSecondary: {
    color: '#9ca3af',
  },
});

export default SettingsScreen;
