import { NavItem } from '../types/navigation';
import { UserRole } from '../types/user';

export function filterNavItems(items: NavItem[], role: UserRole | undefined): NavItem[] {
  return items.filter((item) => {
    const userRole = role ?? UserRole.USER;

    // Check allowedRoles if present
    if (item.allowedRoles) {
      return item.allowedRoles.includes(userRole);
    }

    if (!item.adminOnly) {
      return true;
    }

    if (userRole === UserRole.SUPERADMIN || userRole === UserRole.ADMIN) {
      return true;
    }

    if (userRole === UserRole.MODERATOR) {
      return Boolean(item.moderatorAllowed);
    }

    return false;
  });
}
