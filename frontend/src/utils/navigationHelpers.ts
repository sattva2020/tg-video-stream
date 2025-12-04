import { NavItem } from '../types/navigation';
import { UserRole } from '../types/user';

export function filterNavItems(items: NavItem[], role: UserRole | undefined): NavItem[] {
  return items.filter((item) => {
    if (!item.adminOnly) {
      return true;
    }

    const userRole = role ?? UserRole.USER;

    if (userRole === UserRole.SUPERADMIN || userRole === UserRole.ADMIN) {
      return true;
    }

    if (userRole === UserRole.MODERATOR) {
      return Boolean(item.moderatorAllowed);
    }

    return false;
  });
}
