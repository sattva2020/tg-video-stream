/**
 * ReportBugButton - кнопка для быстрого создания обращения в поддержку
 * 
 * Плавающая кнопка, которая показывается при наличии ошибок
 * или всегда доступна через меню.
 */

import React from 'react';
import { useLogCollectorContext } from '../context/LogCollectorContext';

interface ReportBugButtonProps {
  variant?: 'floating' | 'inline' | 'menu';
  showOnError?: boolean;
  className?: string;
}

export function ReportBugButton({
  variant = 'floating',
  showOnError = true,
  className = '',
}: ReportBugButtonProps) {
  const { openReportDialog, lastError, logs } = useLogCollectorContext();
  
  // Подсчёт ошибок
  const errorCount = logs.filter(log => 
    (log.type === 'console' && log.level === 'error') ||
    (log.type === 'network' && log.statusCode && log.statusCode >= 400)
  ).length;
  
  // Для floating варианта — показываем только при наличии ошибок
  if (variant === 'floating' && showOnError && errorCount === 0) {
    return null;
  }
  
  // Floating button
  if (variant === 'floating') {
    return (
      <button
        onClick={openReportDialog}
        className={`
          fixed bottom-4 right-4 z-40
          flex items-center gap-2 px-4 py-3
          bg-red-500 hover:bg-red-600 text-white
          rounded-full shadow-lg
          transition-all duration-300
          animate-bounce-subtle
          ${className}
        `}
        title="Сообщить о проблеме"
      >
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
            d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" 
          />
        </svg>
        <span className="font-medium">
          {errorCount > 0 ? `Ошибки (${errorCount})` : 'Сообщить о проблеме'}
        </span>
      </button>
    );
  }
  
  // Inline button
  if (variant === 'inline') {
    return (
      <button
        onClick={openReportDialog}
        className={`
          inline-flex items-center gap-2 px-3 py-2
          text-gray-600 dark:text-gray-400
          hover:text-red-500 dark:hover:text-red-400
          hover:bg-red-50 dark:hover:bg-red-900/20
          rounded-lg transition-colors
          ${className}
        `}
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
            d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" 
          />
        </svg>
        <span>Сообщить о проблеме</span>
        {errorCount > 0 && (
          <span className="px-1.5 py-0.5 text-xs bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 rounded-full">
            {errorCount}
          </span>
        )}
      </button>
    );
  }
  
  // Menu item
  return (
    <button
      onClick={openReportDialog}
      className={`
        w-full flex items-center gap-3 px-4 py-2
        text-left text-gray-700 dark:text-gray-300
        hover:bg-gray-100 dark:hover:bg-gray-700
        transition-colors
        ${className}
      `}
    >
      <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
          d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" 
        />
      </svg>
      <span>Сообщить о проблеме</span>
      {errorCount > 0 && (
        <span className="ml-auto px-2 py-0.5 text-xs bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 rounded-full">
          {errorCount}
        </span>
      )}
    </button>
  );
}

export default ReportBugButton;
