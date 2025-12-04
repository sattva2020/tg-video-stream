import { UserRole } from '../types/user';

export type DashboardType = 'AdminDashboardV2' | 'OperatorDashboard' | 'UserDashboard';

export const ADMIN_LIKE_ROLES: UserRole[] = [
  UserRole.SUPERADMIN,
  UserRole.ADMIN,
  UserRole.MODERATOR,
];

export const STREAM_CONTROL_ROLES: UserRole[] = [
  ...ADMIN_LIKE_ROLES,
  UserRole.OPERATOR,
];

export function isAdminLike(role: UserRole | undefined): boolean {
  return role ? ADMIN_LIKE_ROLES.includes(role) : false;
}

export function canControlStream(role: UserRole | undefined): boolean {
  return role ? STREAM_CONTROL_ROLES.includes(role) : false;
}

export function getDashboardComponent(role: UserRole | undefined): DashboardType {
  if (!role) return 'UserDashboard';

  if (ADMIN_LIKE_ROLES.includes(role)) {
    return 'AdminDashboardV2';
  }

  if (role === UserRole.OPERATOR) {
    return 'OperatorDashboard';
  }

  return 'UserDashboard';
}
