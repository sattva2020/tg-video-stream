/**
 * Language Selector Component
 *
 * Allows users to select the app language.
 * Changes take effect immediately.
 * Follows patterns from frontend/src/pages/SettingsPage.tsx
 *
 * Features:
 * - Grid of language options with flags
 * - Visual feedback for selected language
 * - Mobile-optimized touch targets
 */

import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ViewStyle,
} from 'react-native';
import { useTheme } from '../contexts/ThemeContext';
import { getSupportedLanguages } from '../i18n';

interface LanguageOption {
  code: string;
  name: string;
  flag: string;
}

interface LanguageSelectorProps {
  currentLanguage: string;
  onLanguageChange: (languageCode: string) => void;
  style?: ViewStyle;
}

// Language flag mapping
const LANGUAGE_FLAGS: Record<string, string> = {
  en: '🇬🇧',
  ru: '🇷🇺',
  uk: '🇺🇦',
  de: '🇩🇪',
  es: '🇪🇸',
  ja: '🇯🇵',
  zh: '🇨🇳',
};

// Language names for display (can be localized)
const LANGUAGE_NAMES: Record<string, string> = {
  en: 'English',
  ru: 'Русский',
  uk: 'Українська',
  de: 'Deutsch',
  es: 'Español',
  ja: '日本語',
  zh: '中文',
};

export const LanguageSelector: React.FC<LanguageSelectorProps> = ({
  currentLanguage,
  onLanguageChange,
  style,
}) => {
  const { resolvedTheme } = useTheme();
  const isDark = resolvedTheme === 'dark';

  // Get supported languages with flags
  const languages: LanguageOption[] = getSupportedLanguages().map((lang) => ({
    code: lang.code,
    name: LANGUAGE_NAMES[lang.code] || lang.name,
    flag: LANGUAGE_FLAGS[lang.code] || '🌐',
  }));

  return (
    <View style={[styles.container, style]}>
      <View style={styles.grid}>
        {languages.map((lang) => {
          const isSelected = currentLanguage.toLowerCase().includes(lang.code.toLowerCase()) ||
                            currentLanguage === lang.name;

          return (
            <TouchableOpacity
              key={lang.code}
              style={[
                styles.languageButton,
                isSelected && styles.languageButtonSelected,
                isSelected && isDark && styles.languageButtonSelectedDark,
                !isSelected && isDark && styles.languageButtonDark,
              ]}
              onPress={() => onLanguageChange(lang.code)}
              activeOpacity={0.7}
              accessibilityLabel={`Select ${lang.name}`}
              accessibilityRole="button"
              accessibilityState={{ selected: isSelected }}
            >
              <Text style={styles.flag}>{lang.flag}</Text>
              <Text
                style={[
                  styles.languageName,
                  isSelected && styles.languageNameSelected,
                  isSelected && isDark && styles.languageNameSelectedDark,
                  !isSelected && isDark && styles.languageNameDark,
                ]}
              >
                {lang.name}
              </Text>
            </TouchableOpacity>
          );
        })}
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    width: '100%',
  },
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginHorizontal: -4,
    gap: 8,
  },
  languageButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 12,
    paddingVertical: 10,
    borderRadius: 12,
    backgroundColor: '#f3f4f6',
    borderWidth: 2,
    borderColor: 'transparent',
    minWidth: 100,
    minHeight: 44, // Minimum touch target
  },
  languageButtonDark: {
    backgroundColor: '#374151',
    borderColor: 'transparent',
  },
  languageButtonSelected: {
    backgroundColor: '#06b6d4',
    borderColor: '#0891b2',
  },
  languageButtonSelectedDark: {
    backgroundColor: '#06b6d4',
    borderColor: '#22d3ee',
  },
  flag: {
    fontSize: 20,
  },
  languageName: {
    fontSize: 14,
    fontWeight: '600',
    color: '#374151',
  },
  languageNameDark: {
    color: '#d1d5db',
  },
  languageNameSelected: {
    color: '#ffffff',
  },
  languageNameSelectedDark: {
    color: '#ffffff',
    fontWeight: '700',
  },
});
