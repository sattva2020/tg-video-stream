/**
 * Stat Card Component
 *
 * Displays a statistic with icon, title, value, and optional trend indicator.
 * Mobile-optimized with touch targets at least 44x44px.
 * Follows patterns from frontend/src/components/dashboard/StatCard.tsx
 */

import React from 'react';
import { View, Text, StyleSheet, ViewStyle } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { SvgFromUri } from 'react-native-svg';

// Icon types - using simple icon names for now
export type IconName = 'users' | 'clock' | 'radio' | 'music' | 'trending-up' | 'trending-down' | 'check';

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: IconName;
  trend?: {
    value: number;
    label: string;
  };
  color: 'violet' | 'amber' | 'emerald' | 'rose' | 'blue' | 'cyan';
  loading?: boolean;
  style?: ViewStyle;
}

// Color configuration matching frontend patterns
const colorConfig = {
  violet: {
    gradient: ['#8b5cf6', '#9333ea'] as const,
    background: 'rgba(139, 92, 246, 0.1)',
    text: '#8b5cf6',
    border: 'rgba(139, 92, 246, 0.2)',
  },
  amber: {
    gradient: ['#f59e0b', '#ea580c'] as const,
    background: 'rgba(245, 158, 11, 0.1)',
    text: '#f59e0b',
    border: 'rgba(245, 158, 11, 0.2)',
  },
  emerald: {
    gradient: ['#10b981', '#16a34a'] as const,
    background: 'rgba(16, 185, 129, 0.1)',
    text: '#10b981',
    border: 'rgba(16, 185, 129, 0.2)',
  },
  rose: {
    gradient: ['#f43f5e', '#e11d48'] as const,
    background: 'rgba(244, 63, 94, 0.1)',
    text: '#f43f5e',
    border: 'rgba(244, 63, 94, 0.2)',
  },
  blue: {
    gradient: ['#3b82f6', '#4f46e5'] as const,
    background: 'rgba(59, 130, 246, 0.1)',
    text: '#3b82f6',
    border: 'rgba(59, 130, 246, 0.2)',
  },
  cyan: {
    gradient: ['#06b6d4', '#14b8a6'] as const,
    background: 'rgba(6, 182, 212, 0.1)',
    text: '#06b6d4',
    border: 'rgba(6, 182, 212, 0.2)',
  },
};

// Simple icon components (using Text with emojis for simplicity)
// In production, you'd use react-native-vector-icons or similar
const SimpleIcon: React.FC<{ name: IconName; color: string; size: number }> = ({ name, color, size }) => {
  const icons: Record<IconName, string> = {
    'users': '👥',
    'clock': '⏱',
    'radio': '📻',
    'music': '🎵',
    'trending-up': '📈',
    'trending-down': '📉',
    'check': '✅',
  };

  return (
    <Text style={{ fontSize: size, color: 'white' }}>{icons[name]}</Text>
  );
};

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  subtitle,
  icon,
  trend,
  color,
  loading = false,
  style,
}) => {
  const colors = colorConfig[color];

  if (loading) {
    return (
      <View style={[styles.container, styles.loadingContainer, style]}>
        <View style={styles.skeletonHeader}>
          <View style={[styles.skeletonTitle, { backgroundColor: colors.border }]} />
          <View style={[styles.skeletonIcon, { backgroundColor: colors.border }]} />
        </View>
        <View style={[styles.skeletonValue, { backgroundColor: colors.border }]} />
        <View style={[styles.skeletonSubtitle, { backgroundColor: colors.border }]} />
      </View>
    );
  }

  const getTrendIcon = () => {
    if (!trend) return null;
    if (trend.value > 0) return 'trending-up';
    if (trend.value < 0) return 'trending-down';
    return null;
  };

  const getTrendColor = () => {
    if (!trend) return colors.text;
    if (trend.value > 0) return '#10b981'; // emerald
    if (trend.value < 0) return '#f43f5e'; // rose
    return '#6b7280'; // gray
  };

  return (
    <View style={[styles.container, { borderColor: colors.border }, style]}>
      {/* Icon */}
      <View style={styles.header}>
        <Text style={styles.title}>{title}</Text>
        <LinearGradient
          colors={[...colors.gradient]}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 1 }}
          style={styles.iconContainer}
        >
          <SimpleIcon name={icon} color="white" size={20} />
        </LinearGradient>
      </View>

      {/* Value */}
      <View style={styles.valueContainer}>
        <View>
          <Text style={styles.value}>{typeof value === 'number' ? value.toString() : value}</Text>
          {subtitle && (
            <Text style={styles.subtitle}>{subtitle}</Text>
          )}
        </View>

        {trend && (
          <View style={styles.trendContainer}>
            {getTrendIcon() && (
              <SimpleIcon name={getTrendIcon() as IconName} color={getTrendColor()} size={12} />
            )}
            <Text style={[styles.trendText, { color: getTrendColor() }]}>
              {Math.abs(trend.value)}%
            </Text>
          </View>
        )}
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    backgroundColor: '#ffffff',
    borderRadius: 24,
    borderWidth: 1,
    padding: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 3,
    minHeight: 120, // Ensure adequate touch target
  },
  loadingContainer: {
    justifyContent: 'center',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  title: {
    fontSize: 12,
    fontWeight: '600',
    color: '#6b7280',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  iconContainer: {
    width: 40,
    height: 40,
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.2,
    shadowRadius: 4,
    elevation: 2,
  },
  valueContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-end',
  },
  value: {
    fontSize: 28,
    fontWeight: '700',
    color: '#111827',
  },
  subtitle: {
    fontSize: 12,
    color: '#6b7280',
    marginTop: 4,
  },
  trendContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  trendText: {
    fontSize: 12,
    fontWeight: '600',
  },
  // Skeleton loading styles
  skeletonHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 12,
  },
  skeletonTitle: {
    width: 100,
    height: 16,
    borderRadius: 4,
  },
  skeletonIcon: {
    width: 40,
    height: 40,
    borderRadius: 12,
  },
  skeletonValue: {
    width: 80,
    height: 32,
    borderRadius: 4,
    marginBottom: 8,
  },
  skeletonSubtitle: {
    width: 120,
    height: 16,
    borderRadius: 4,
  },
});
