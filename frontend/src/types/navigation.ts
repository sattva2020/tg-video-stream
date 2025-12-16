import { ReactNode } from 'react';
import { UserRole } from './user';

export interface NavItem {
  path: string;
  label: string;
  icon: ReactNode;
  adminOnly?: boolean;
  moderatorAllowed?: boolean;
  allowedRoles?: UserRole[];
}
