/**
 * Theme Toggle Component
 *
 * Allows users to toggle between light, dark, and system theme modes.
 * Follows patterns from frontend/src/pages/SettingsPage.tsx
 *
 * Features:
 * - Three options: Light, Dark, System
 * - Visual feedback for selected theme
 * - Icons representing each theme mode
 */

import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
} from 'react-native';
import { useTheme } from '../contexts/ThemeContext';
import { useTranslation } from 'react-i18next';

export type ThemeMode = 'light' | 'dark' | 'system';

interface ThemeToggleProps {
  onThemeChange?: (theme: ThemeMode) => void;
}

interface ThemeOption {
  mode: ThemeMode;
  label: string;
  icon: string;
}

export const ThemeToggle: React.FC<ThemeToggleProps> = ({ onThemeChange }) => {
  const { theme, setTheme, resolvedTheme } = useTheme();
  const { t } = useTranslation();
  const isDark = resolvedTheme === 'dark';

  const themeOptions: ThemeOption[] = [
    { mode: 'light', label: t('settings.themeLight', 'Light'), icon: '☀️' },
    { mode: 'dark', label: t('settings.themeDark', 'Dark'), icon: '🌙' },
    { mode: 'system', label: t('settings.themeSystem', 'System'), icon: '💻' },
  ];

  const handleThemeChange = async (newTheme: ThemeMode) => {
    await setTheme(newTheme);
    onThemeChange?.(newTheme);
  };

  return (
    <View style={styles.container}>
      <View style={styles.optionsContainer}>
        {themeOptions.map((option) => {
          const isSelected = theme === option.mode;

          return (
            <TouchableOpacity
              key={option.mode}
              style={[
                styles.optionButton,
                isSelected && styles.optionButtonSelected,
                isSelected && isDark && styles.optionButtonSelectedDark,
                !isSelected && isDark && styles.optionButtonDark,
              ]}
              onPress={() => handleThemeChange(option.mode)}
              activeOpacity={0.7}
              accessibilityLabel={`Select ${option.label} theme`}
              accessibilityRole="button"
              accessibilityState={{ selected: isSelected }}
            >
              <Text style={styles.icon}>{option.icon}</Text>
              <Text
                style={[
                  styles.label,
                  isSelected && styles.labelSelected,
                  isSelected && isDark && styles.labelSelectedDark,
                  !isSelected && isDark && styles.labelDark,
                ]}
              >
                {option.label}
              </Text>
            </TouchableOpacity>
          );
        })}
      </View>

      {/* Current theme indicator */}
      <View style={[styles.currentIndicator, isDark && styles.currentIndicatorDark]}>
        <Text style={[styles.currentIndicatorText, isDark && styles.textSecondary]}>
          {t('settings.currentTheme', 'Current')}: {t(`settings.theme${theme.charAt(0).toUpperCase() + theme.slice(1)}`, theme)}
        </Text>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    width: '100%',
  },
  optionsContainer: {
    flexDirection: 'row',
    gap: 8,
  },
  optionButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    paddingHorizontal: 12,
    paddingVertical: 12,
    borderRadius: 12,
    backgroundColor: '#f3f4f6',
    borderWidth: 2,
    borderColor: 'transparent',
    minHeight: 48, // Minimum touch target
  },
  optionButtonDark: {
    backgroundColor: '#374151',
    borderColor: 'transparent',
  },
  optionButtonSelected: {
    backgroundColor: '#06b6d4',
    borderColor: '#0891b2',
  },
  optionButtonSelectedDark: {
    backgroundColor: '#06b6d4',
    borderColor: '#22d3ee',
  },
  icon: {
    fontSize: 18,
  },
  label: {
    fontSize: 14,
    fontWeight: '600',
    color: '#374151',
  },
  labelDark: {
    color: '#d1d5db',
  },
  labelSelected: {
    color: '#ffffff',
  },
  labelSelectedDark: {
    color: '#ffffff',
    fontWeight: '700',
  },
  currentIndicator: {
    marginTop: 12,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: '#e5e7eb',
  },
  currentIndicatorDark: {
    borderTopColor: '#374151',
  },
  currentIndicatorText: {
    fontSize: 12,
    color: '#6b7280',
  },
  textSecondary: {
    color: '#9ca3af',
  },
});
