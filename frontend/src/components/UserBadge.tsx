import React from 'react';
import { UserRole } from '../types/user';

interface UserBadgeProps {
  role: UserRole;
}

const UserBadge: React.FC<UserBadgeProps> = ({ role }) => {
  if (role !== UserRole.ADMIN) {
    return null;
  }

  return (
    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800 ml-2">
      Admin
    </span>
  );
};

export default UserBadge;
