/**
 * Protected Route Component
 *
 * Wrapper component for routes that require specific user roles.
 * Follows patterns from frontend/src/components/ProtectedRoute
 */

import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import type { UserRole } from '../types';

interface ProtectedRouteProps {
  allowedRoles: UserRole[];
  userRole: UserRole | undefined;
  component: React.ComponentType<any>;
  [key: string]: any;
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  allowedRoles,
  userRole,
  component: Component,
  ...rest
}) => {
  // Check if user has required role
  const hasAccess = userRole && allowedRoles.includes(userRole);

  if (!hasAccess) {
    // User doesn't have access - show access denied screen
    return (
      <View style={styles.container}>
        <Text style={styles.title}>Access Denied</Text>
        <Text style={styles.message}>
          You don't have permission to access this screen.
        </Text>
      </View>
    );
  }

  // User has access - render the component
  return <Component {...rest} />;
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#f9fafb',
    padding: 20,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#dc2626',
    marginBottom: 12,
  },
  message: {
    fontSize: 16,
    color: '#6b7280',
    textAlign: 'center',
  },
});
