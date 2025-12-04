import { describe, expect, it } from 'vitest';
import { UserRole } from '../../src/types/user';
import {
  ADMIN_LIKE_ROLES,
  STREAM_CONTROL_ROLES,
  canControlStream,
  getDashboardComponent,
  isAdminLike,
} from '../../src/utils/roleHelpers';

describe('roleHelpers', () => {
  it('detects admin-like roles correctly', () => {
    ADMIN_LIKE_ROLES.forEach((role) => {
      expect(isAdminLike(role)).toBe(true);
    });

    expect(isAdminLike(UserRole.OPERATOR)).toBe(false);
    expect(isAdminLike(UserRole.USER)).toBe(false);
    expect(isAdminLike(undefined)).toBe(false);
  });

  it('detects stream control roles correctly', () => {
    STREAM_CONTROL_ROLES.forEach((role) => {
      expect(canControlStream(role)).toBe(true);
    });

    expect(canControlStream(UserRole.USER)).toBe(false);
    expect(canControlStream(undefined)).toBe(false);
  });

  it('returns dashboard component by role', () => {
    expect(getDashboardComponent(UserRole.SUPERADMIN)).toBe('AdminDashboardV2');
    expect(getDashboardComponent(UserRole.ADMIN)).toBe('AdminDashboardV2');
    expect(getDashboardComponent(UserRole.MODERATOR)).toBe('AdminDashboardV2');
    expect(getDashboardComponent(UserRole.OPERATOR)).toBe('OperatorDashboard');
    expect(getDashboardComponent(UserRole.USER)).toBe('UserDashboard');
    expect(getDashboardComponent(undefined)).toBe('UserDashboard');
  });
});
