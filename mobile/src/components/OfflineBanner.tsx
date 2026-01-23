/**
 * Offline Banner Component
 *
 * Displays a banner at the top of the screen when the device is offline.
 * Animated appearance/disappearance for smooth transitions.
 * Follows patterns from mobile/src/components/StatCard.tsx
 *
 * Features:
 * - Shows warning message when offline
 * - Displays connection type when available
 * - Animated slide-in/slide-out
 * - Auto-dismisses when connection is restored
 */

import React, { useEffect } from 'react';
import { View, Text, StyleSheet, Animated, Dimensions } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

interface OfflineBannerProps {
  isOnline: boolean;
  connectionType?: string | null;
}

export const OfflineBanner: React.FC<OfflineBannerProps> = ({ isOnline, connectionType }) => {
  const insets = useSafeAreaInsets();
  const slideAnim = React.useRef(new Animated.Value(-100)).current;

  /**
   * Animate banner in/out based on online status
   */
  useEffect(() => {
    if (!isOnline) {
      // Slide in from top
      Animated.timing(slideAnim, {
        toValue: 0,
        duration: 300,
        useNativeDriver: true,
      }).start();
    } else {
      // Slide out to top
      Animated.timing(slideAnim, {
        toValue: -100,
        duration: 300,
        useNativeDriver: true,
      }).start();
    }
  }, [isOnline, slideAnim]);

  // Don't render anything if online (after animation completes)
  if (isOnline && slideAnim._value <= -90) {
    return null;
  }

  /**
   * Get connection type label
   */
  const getConnectionLabel = (): string => {
    if (!connectionType || connectionType === 'none') {
      return '';
    }

    const labels: Record<string, string> = {
      wifi: 'Wi-Fi',
      cellular: 'Cellular',
      bluetooth: 'Bluetooth',
      ethernet: 'Ethernet',
      wimax: 'WiMAX',
      vpn: 'VPN',
      other: 'Other',
    };

    return labels[connectionType] || connectionType;
  };

  const connectionLabel = getConnectionLabel();

  return (
    <Animated.View
      style={[
        styles.container,
        {
          top: insets.top,
          transform: [{ translateY: slideAnim }],
        },
      ]}
    >
      <View style={styles.content}>
        <View style={styles.iconContainer}>
          <Text style={styles.icon}>⚠️</Text>
        </View>

        <View style={styles.textContainer}>
          <Text style={styles.title}>No Internet Connection</Text>
          {connectionLabel ? (
            <Text style={styles.subtitle}>{connectionLabel} unavailable</Text>
          ) : (
            <Text style={styles.subtitle}>
              Some features may be limited
            </Text>
          )}
        </View>
      </View>
    </Animated.View>
  );
};

const styles = StyleSheet.create({
  container: {
    position: 'absolute',
    left: 0,
    right: 0,
    backgroundColor: '#f59e0b',
    zIndex: 9999,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 4,
    elevation: 5,
  },
  content: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 12,
    paddingHorizontal: 16,
    gap: 12,
  },
  iconContainer: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  icon: {
    fontSize: 18,
  },
  textContainer: {
    flex: 1,
  },
  title: {
    fontSize: 14,
    fontWeight: '600',
    color: '#ffffff',
    marginBottom: 2,
  },
  subtitle: {
    fontSize: 12,
    color: 'rgba(255, 255, 255, 0.9)',
  },
});
