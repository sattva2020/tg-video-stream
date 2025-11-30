import React from 'react';
import clsx from 'clsx';

export interface ErrorToastProps {
  message: string;
  tone?: 'error' | 'success' | 'info';
  'data-testid'?: string;
}

const TONE_CLASSES: Record<string, string> = {
  error: 'bg-red-600 text-white border border-red-400',
  success: 'bg-green-600 text-white border border-green-400',
  info: 'bg-blue-600 text-white border border-blue-400',
};

const ErrorToast: React.FC<ErrorToastProps> = ({ message, tone = 'error', ['data-testid']: testId }) => {
  return (
    <div
      role="alert"
      aria-live="polite"
      data-testid={testId ?? 'error-toast'}
      className={clsx('rounded-lg px-4 py-3 text-sm font-medium shadow-md', TONE_CLASSES[tone])}
    >
      {message}
    </div>
  );
};

export default ErrorToast;
