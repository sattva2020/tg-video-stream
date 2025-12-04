import { filterNavItems } from '../../frontend/src/utils/navigationHelpers';
import { getDashboardComponent } from '../../frontend/src/utils/roleHelpers';
import { UserRole } from '../../frontend/src/types/user';
import type { NavItem } from '../../frontend/src/types/navigation';

const navItems: NavItem[] = [
  { path: '/dashboard', label: 'Dashboard', icon: null as any },
  { path: '/channels', label: 'Channels', icon: null as any },
  { path: '/playlist', label: 'Playlist', icon: null as any },
  { path: '/schedule', label: 'Schedule', icon: null as any },
  { path: '/admin', label: 'Admin', icon: null as any, adminOnly: true },
  { path: '/admin/pending', label: 'Pending', icon: null as any, adminOnly: true },
  {
    path: '/admin/monitoring',
    label: 'Monitoring',
    icon: null as any,
    adminOnly: true,
    moderatorAllowed: true,
  },
];

const expectedNav: Record<UserRole, string[]> = {
  [UserRole.SUPERADMIN]: ['/dashboard', '/channels', '/playlist', '/schedule', '/admin', '/admin/pending', '/admin/monitoring'],
  [UserRole.ADMIN]: ['/dashboard', '/channels', '/playlist', '/schedule', '/admin', '/admin/pending', '/admin/monitoring'],
  [UserRole.MODERATOR]: ['/dashboard', '/channels', '/playlist', '/schedule', '/admin/monitoring'],
  [UserRole.OPERATOR]: ['/dashboard', '/channels', '/playlist', '/schedule'],
  [UserRole.USER]: ['/dashboard', '/channels', '/playlist', '/schedule'],
};

const rolesToCheck: UserRole[] = [UserRole.SUPERADMIN, UserRole.ADMIN, UserRole.MODERATOR];

let hasError = false;

for (const role of rolesToCheck) {
  const filtered = filterNavItems(navItems, role).map((item) => item.path);
  const expected = expectedNav[role];

  if (JSON.stringify(filtered) !== JSON.stringify(expected)) {
    console.error(`[SMOKE] Navigation mismatch for ${role}. Expected ${expected}, got ${filtered}`);
    hasError = true;
  } else {
    console.log(`[SMOKE] Navigation OK for ${role}: ${filtered.join(', ')}`);
  }

  const dashboard = getDashboardComponent(role);
  if (dashboard !== 'AdminDashboardV2') {
    console.error(`[SMOKE] Dashboard mismatch for ${role}. Expected AdminDashboardV2, got ${dashboard}`);
    hasError = true;
  } else {
    console.log(`[SMOKE] Dashboard OK for ${role}: ${dashboard}`);
  }
}

process.exit(hasError ? 1 : 0);
