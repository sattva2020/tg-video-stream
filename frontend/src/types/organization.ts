/**
 * Organization types for multi-tenant support
 */

export interface Organization {
  id: string;
  name: string;
  slug?: string;
  logo_url?: string;
  primary_color?: string;
  secondary_color?: string;
  custom_domain?: string;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface OrganizationContextState {
  currentOrganization: Organization | null;
  isLoading: boolean;
  error: string | null;
  setCurrentOrganization: (org: Organization | null) => void;
  clearCurrentOrganization: () => void;
}
