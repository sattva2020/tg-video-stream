import React from 'react';

interface LogoutButtonProps {
  onClick: () => void;
  disabled?: boolean;
}

const LogoutButton: React.FC<LogoutButtonProps> = ({ onClick, disabled = false }) => {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="px-4 py-2 text-sm font-medium text-white bg-red-600 border border-transparent rounded-md shadow-sm hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 disabled:opacity-50 disabled:cursor-not-allowed"
    >
      Logout
    </button>
  );
};

export default LogoutButton;