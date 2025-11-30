import React from 'react';
import { UserRole } from '../types/user';

interface UserBadgeProps {
  role: UserRole | string;
}

const roleConfig: Record<string, { label: string; className: string }> = {
  superadmin: {
    label: 'Super Admin',
    className: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
  },
  admin: {
    label: 'Admin',
    className: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
  },
  moderator: {
    label: 'Moderator',
    className: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  },
  operator: {
    label: 'Operator',
    className: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  },
};

const UserBadge: React.FC<UserBadgeProps> = ({ role }) => {
  const roleKey = typeof role === 'string' ? role.toLowerCase() : role;
  const config = roleConfig[roleKey];

  // Обычные пользователи без бейджа
  if (!config) {
    return null;
  }

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${config.className}`}>
      {config.label}
    </span>
  );
};

export default UserBadge;
