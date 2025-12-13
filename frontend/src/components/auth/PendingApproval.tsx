import React from 'react';
import { useAuth } from '../../context/AuthContext';

interface PendingApprovalProps {
  onBackToLogin?: () => void;
}

export const PendingApproval: React.FC<PendingApprovalProps> = ({ onBackToLogin }) => {
  const { pendingApprovalMessage, clearPendingStatus, logout } = useAuth();

  const handleBackToLogin = () => {
    logout(); // Clear token and pending state
    clearPendingStatus();
    if (onBackToLogin) {
      onBackToLogin();
    }
  };

  return (
    <div className="w-full max-w-md p-8 space-y-6 bg-white rounded-lg shadow-lg">
      <div className="flex flex-col items-center space-y-4">
        {/* Icon */}
        <div className="flex items-center justify-center w-16 h-16 bg-yellow-100 rounded-full">
          <svg 
            className="w-8 h-8 text-yellow-600" 
            fill="none" 
            stroke="currentColor" 
            viewBox="0 0 24 24"
          >
            <path 
              strokeLinecap="round" 
              strokeLinejoin="round" 
              strokeWidth={2} 
              d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" 
            />
          </svg>
        </div>

        {/* Title */}
        <h2 className="text-2xl font-bold text-gray-900 text-center">
          Ожидание одобрения
        </h2>

        {/* Message */}
        <p className="text-center text-gray-600">
          {pendingApprovalMessage || 'Ваш аккаунт ожидает одобрения администратором'}
        </p>

        {/* Additional info */}
        <div className="w-full p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <p className="text-sm text-blue-800">
            <strong>Что дальше?</strong><br />
            После проверки вашего аккаунта администратором вы получите доступ к платформе. 
            Обычно это занимает несколько часов.
          </p>
        </div>

        {/* Actions */}
        <div className="flex flex-col w-full space-y-3 pt-4">
          <button
            onClick={handleBackToLogin}
            className="w-full px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
          >
            Вернуться к авторизации
          </button>
          
          <a
            href="mailto:admin@sattva.local"
            className="w-full px-4 py-2 text-sm font-medium text-center text-blue-600 border border-blue-600 rounded-md hover:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
          >
            Связаться с администратором
          </a>
        </div>
      </div>
    </div>
  );
};
