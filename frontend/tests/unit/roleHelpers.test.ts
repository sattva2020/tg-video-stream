import { describe, expect, it } from 'vitest';
import { UserRole } from '../../src/types/user';
import {
  ADMIN_LIKE_ROLES,
  STREAM_CONTROL_ROLES,
  canControlStream,
  getDashboardComponent,
  isAdminLike,
  type DashboardType,
} from '../../src/utils/roleHelpers';

describe('roleHelpers', () => {
  describe('Constants', () => {
    it('ADMIN_LIKE_ROLES contains correct roles', () => {
      expect(ADMIN_LIKE_ROLES).toEqual([
        UserRole.SUPERADMIN,
        UserRole.ADMIN,
        UserRole.MODERATOR,
      ]);
      expect(ADMIN_LIKE_ROLES).toHaveLength(3);
    });

    it('STREAM_CONTROL_ROLES contains admin-like roles and operator', () => {
      expect(STREAM_CONTROL_ROLES).toContain(UserRole.SUPERADMIN);
      expect(STREAM_CONTROL_ROLES).toContain(UserRole.ADMIN);
      expect(STREAM_CONTROL_ROLES).toContain(UserRole.MODERATOR);
      expect(STREAM_CONTROL_ROLES).toContain(UserRole.OPERATOR);
      expect(STREAM_CONTROL_ROLES).toHaveLength(4);
    });

    it('STREAM_CONTROL_ROLES includes all ADMIN_LIKE_ROLES', () => {
      ADMIN_LIKE_ROLES.forEach((role) => {
        expect(STREAM_CONTROL_ROLES).toContain(role);
      });
    });

    it('STREAM_CONTROL_ROLES does not include regular user', () => {
      expect(STREAM_CONTROL_ROLES).not.toContain(UserRole.USER);
    });
  });

  describe('isAdminLike', () => {
    it('returns true for all admin-like roles', () => {
      expect(isAdminLike(UserRole.SUPERADMIN)).toBe(true);
      expect(isAdminLike(UserRole.ADMIN)).toBe(true);
      expect(isAdminLike(UserRole.MODERATOR)).toBe(true);
    });

    it('returns false for operator role', () => {
      expect(isAdminLike(UserRole.OPERATOR)).toBe(false);
    });

    it('returns false for regular user role', () => {
      expect(isAdminLike(UserRole.USER)).toBe(false);
    });

    it('returns false for undefined role', () => {
      expect(isAdminLike(undefined)).toBe(false);
    });

    it('returns false for null when passed as any', () => {
      expect(isAdminLike(null as any)).toBe(false);
    });
  });

  describe('canControlStream', () => {
    it('returns true for all stream control roles', () => {
      expect(canControlStream(UserRole.SUPERADMIN)).toBe(true);
      expect(canControlStream(UserRole.ADMIN)).toBe(true);
      expect(canControlStream(UserRole.MODERATOR)).toBe(true);
      expect(canControlStream(UserRole.OPERATOR)).toBe(true);
    });

    it('returns false for regular user', () => {
      expect(canControlStream(UserRole.USER)).toBe(false);
    });

    it('returns false for undefined role', () => {
      expect(canControlStream(undefined)).toBe(false);
    });

    it('returns false for null when passed as any', () => {
      expect(canControlStream(null as any)).toBe(false);
    });

    it('all admin-like roles can control stream', () => {
      ADMIN_LIKE_ROLES.forEach((role) => {
        expect(canControlStream(role)).toBe(true);
      });
    });
  });

  describe('getDashboardComponent', () => {
    it('returns AdminDashboardV2 for all admin-like roles', () => {
      expect(getDashboardComponent(UserRole.SUPERADMIN)).toBe('AdminDashboardV2');
      expect(getDashboardComponent(UserRole.ADMIN)).toBe('AdminDashboardV2');
      expect(getDashboardComponent(UserRole.MODERATOR)).toBe('AdminDashboardV2');
    });

    it('returns OperatorDashboard for operator role', () => {
      expect(getDashboardComponent(UserRole.OPERATOR)).toBe('OperatorDashboard');
    });

    it('returns UserDashboard for regular user', () => {
      expect(getDashboardComponent(UserRole.USER)).toBe('UserDashboard');
    });

    it('returns UserDashboard for undefined role', () => {
      expect(getDashboardComponent(undefined)).toBe('UserDashboard');
    });

    it('returns UserDashboard for null when passed as any', () => {
      expect(getDashboardComponent(null as any)).toBe('UserDashboard');
    });

    it('returns one of three valid dashboard types', () => {
      const validDashboards: DashboardType[] = [
        'AdminDashboardV2',
        'OperatorDashboard',
        'UserDashboard',
      ];

      const allRoles = Object.values(UserRole);
      allRoles.forEach((role) => {
        const dashboard = getDashboardComponent(role);
        expect(validDashboards).toContain(dashboard);
      });
    });

    it('all admin-like roles map to AdminDashboardV2', () => {
      ADMIN_LIKE_ROLES.forEach((role) => {
        expect(getDashboardComponent(role)).toBe('AdminDashboardV2');
      });
    });
  });

  describe('Role hierarchy integration', () => {
    it('admin-like roles have all stream control permissions', () => {
      ADMIN_LIKE_ROLES.forEach((role) => {
        expect(isAdminLike(role)).toBe(true);
        expect(canControlStream(role)).toBe(true);
        expect(getDashboardComponent(role)).toBe('AdminDashboardV2');
      });
    });

    it('operator can control stream but is not admin-like', () => {
      expect(isAdminLike(UserRole.OPERATOR)).toBe(false);
      expect(canControlStream(UserRole.OPERATOR)).toBe(true);
      expect(getDashboardComponent(UserRole.OPERATOR)).toBe('OperatorDashboard');
    });

    it('regular user has minimal permissions', () => {
      expect(isAdminLike(UserRole.USER)).toBe(false);
      expect(canControlStream(UserRole.USER)).toBe(false);
      expect(getDashboardComponent(UserRole.USER)).toBe('UserDashboard');
    });

    it('undefined/null behaves as minimal permission user', () => {
      [undefined, null as any].forEach((role) => {
        expect(isAdminLike(role)).toBe(false);
        expect(canControlStream(role)).toBe(false);
        expect(getDashboardComponent(role)).toBe('UserDashboard');
      });
    });
  });
});
