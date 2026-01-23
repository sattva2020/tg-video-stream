/**
 * OrganizationContext - manages organization context for multi-tenant support
 *
 * Provides the current organization state and methods to manage it.
 * This context is used to track which organization the user is currently working with.
 *
 * @example
 * // In App.tsx
 * <OrganizationProvider>
 *   <App />
 * </OrganizationProvider>
 *
 * // In any component
 * const { currentOrganization, setCurrentOrganization, clearCurrentOrganization } = useOrganizationContext();
 */

import React, { createContext, useContext, useState, useCallback, type ReactNode } from 'react';
import type { Organization, OrganizationContextState } from '../types/organization';

const OrganizationContext = createContext<OrganizationContextState | undefined>(undefined);

interface OrganizationProviderProps {
  children: ReactNode;
}

export const OrganizationProvider: React.FC<OrganizationProviderProps> = ({ children }) => {
  const [currentOrganization, setCurrentOrganizationState] = useState<Organization | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const setCurrentOrganization = useCallback((org: Organization | null) => {
    setCurrentOrganizationState(org);
    setError(null);
  }, []);

  const clearCurrentOrganization = useCallback(() => {
    setCurrentOrganizationState(null);
    setError(null);
  }, []);

  const value: OrganizationContextState = {
    currentOrganization,
    isLoading,
    error,
    setCurrentOrganization,
    clearCurrentOrganization,
  };

  return (
    <OrganizationContext.Provider value={value}>
      {children}
    </OrganizationContext.Provider>
  );
};

export const useOrganizationContext = (): OrganizationContextState => {
  const context = useContext(OrganizationContext);
  if (context === undefined) {
    throw new Error('useOrganizationContext must be used within an OrganizationProvider');
  }
  return context;
};

export default OrganizationContext;
