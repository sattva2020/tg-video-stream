import { UserRole } from './user';

export interface RolePermissions {
  canViewAdminDashboard: boolean;
  canManageUsers: boolean;
  canManagePlaylist: boolean;
  canControlStream: boolean;
  canViewMonitoring: boolean;
  canAccessSqlAdmin: boolean;
  canViewAnalytics: boolean;
}

export const ROLE_PERMISSIONS: Record<UserRole, RolePermissions> = {
  [UserRole.SUPERADMIN]: {
    canViewAdminDashboard: true,
    canManageUsers: true,
    canManagePlaylist: true,
    canControlStream: true,
    canViewMonitoring: true,
    canAccessSqlAdmin: true,
    canViewAnalytics: true,
  },
  [UserRole.ADMIN]: {
    canViewAdminDashboard: true,
    canManageUsers: true,
    canManagePlaylist: true,
    canControlStream: true,
    canViewMonitoring: true,
    canAccessSqlAdmin: false,
    canViewAnalytics: true,
  },
  [UserRole.MODERATOR]: {
    canViewAdminDashboard: true,
    canManageUsers: false,
    canManagePlaylist: true,
    canControlStream: true,
    canViewMonitoring: true,
    canAccessSqlAdmin: false,
    canViewAnalytics: true,
  },
  [UserRole.OPERATOR]: {
    canViewAdminDashboard: false,
    canManageUsers: false,
    canManagePlaylist: false,
    canControlStream: true,
    canViewMonitoring: true,
    canAccessSqlAdmin: false,
    canViewAnalytics: false,
  },
  [UserRole.USER]: {
    canViewAdminDashboard: false,
    canManageUsers: false,
    canManagePlaylist: false,
    canControlStream: false,
    canViewMonitoring: false,
    canAccessSqlAdmin: false,
    canViewAnalytics: false,
  },
};
