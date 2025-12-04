import { ReactNode } from 'react';

export interface NavItem {
  path: string;
  label: string;
  icon: ReactNode;
  adminOnly?: boolean;
  moderatorAllowed?: boolean;
}
