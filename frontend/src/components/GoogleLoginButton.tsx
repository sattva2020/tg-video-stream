import React from 'react';

const GoogleIcon = () => (
  <svg className="w-5 h-5 mr-2" viewBox="0 0 48 48">
    <path fill="#FFC107" d="M43.611 20.083H42V20H24v8h11.303c-1.649 4.657-6.08 8-11.303 8c-6.627 0-12-5.373-12-12s5.373-12 12-12c3.059 0 5.842 1.154 7.961 3.039L38.802 9.92C34.553 6.08 29.613 4 24 4C12.955 4 4 12.955 4 24s8.955 20 20 20s20-8.955 20-20c0-1.341-.138-2.65-.389-3.917z"></path>
    <path fill="#FF3D00" d="M6.306 14.691c-1.645 3.119-2.645 6.632-2.645 10.309C3.661 30.631 5.013 34.41 7.096 37.52l6.98-5.498c-1.03-1.91-1.6-4.08-1.6-6.32s.57-4.41 1.6-6.32l-6.98-5.498z"></path>
    <path fill="#4CAF50" d="M24 44c5.166 0 9.86-1.977 13.2-5.25l-6.52-5.02c-2.14 1.45-4.84 2.27-7.68 2.27-4.83 0-8.99-2.6-10.9-6.22l-6.98 5.498C9.005 39.99 15.95 44 24 44z"></path>
    <path fill="#1976D2" d="M43.611 20.083H42V20H24v8h11.303c-.792 2.237-2.231 4.16-4.082 5.571l6.52 5.02C41.319 36.133 44 30.608 44 24c0-1.341-.138-2.65-.389-3.917z"></path>
  </svg>
);

interface GoogleLoginButtonProps {
  onClick: () => void;
  disabled?: boolean;
}

const GoogleLoginButton: React.FC<GoogleLoginButtonProps> = ({ onClick, disabled = false }) => {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="flex items-center justify-center w-full px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
    >
      <GoogleIcon />
      Sign in with Google
    </button>
  );
};

export default GoogleLoginButton;