import { UserRole } from './user';

export interface RolePermissions {
  canViewAdminDashboard: boolean;
  canManageUsers: boolean;
  canManagePlaylist: boolean;
  canControlStream: boolean;
  canViewMonitoring: boolean;
  canAccessSqlAdmin: boolean;
}

export const ROLE_PERMISSIONS: Record<UserRole, RolePermissions> = {
  [UserRole.SUPERADMIN]: {
    canViewAdminDashboard: true,
    canManageUsers: true,
    canManagePlaylist: true,
    canControlStream: true,
    canViewMonitoring: true,
    canAccessSqlAdmin: true,
  },
  [UserRole.ADMIN]: {
    canViewAdminDashboard: true,
    canManageUsers: true,
    canManagePlaylist: true,
    canControlStream: true,
    canViewMonitoring: true,
    canAccessSqlAdmin: false,
  },
  [UserRole.MODERATOR]: {
    canViewAdminDashboard: true,
    canManageUsers: false,
    canManagePlaylist: true,
    canControlStream: true,
    canViewMonitoring: true,
    canAccessSqlAdmin: false,
  },
  [UserRole.OPERATOR]: {
    canViewAdminDashboard: false,
    canManageUsers: false,
    canManagePlaylist: false,
    canControlStream: true,
    canViewMonitoring: true,
    canAccessSqlAdmin: false,
  },
  [UserRole.USER]: {
    canViewAdminDashboard: false,
    canManageUsers: false,
    canManagePlaylist: false,
    canControlStream: false,
    canViewMonitoring: false,
    canAccessSqlAdmin: false,
  },
};
