import React, { useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { authApi } from '../api/auth';
import { PasswordInput } from '../components/ui/PasswordInput';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { PasswordResetRequestSchema, PasswordResetConfirmSchema } from '../api/auth';
import type { PasswordResetRequestData, PasswordResetConfirmData } from '../api/auth';

type FormStage = 'request' | 'confirm';

const PasswordResetPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');
  const [stage] = useState<FormStage>(token ? 'confirm' : 'request');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  // Request form (email)
  const requestForm = useForm<PasswordResetRequestData>({
    resolver: zodResolver(PasswordResetRequestSchema),
  });

  // Confirm form (token + new password)
  const confirmForm = useForm<PasswordResetConfirmData>({
    resolver: zodResolver(PasswordResetConfirmSchema),
    defaultValues: {
      token: token || '',
    },
  });

  const onRequestSubmit = async (data: PasswordResetRequestData) => {
    setIsLoading(true);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      await authApi.requestPasswordReset(data);
      setSuccessMessage('Check your email for a password reset link.');
      requestForm.reset();
    } catch (error: any) {
      console.error('Password reset request failed:', error);
      if (error.response?.status === 404) {
        setErrorMessage('Email not found in our system.');
      } else {
        setErrorMessage('Failed to send reset email. Please try again later.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const onConfirmSubmit = async (data: PasswordResetConfirmData) => {
    setIsLoading(true);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      await authApi.confirmPasswordReset(data);
      setSuccessMessage('Password reset successful! You can now log in with your new password.');
      confirmForm.reset();
      setTimeout(() => {
        window.location.href = '/login';
      }, 2000);
    } catch (error: any) {
      console.error('Password reset confirmation failed:', error);
      if (error.response?.status === 400) {
        setErrorMessage('Invalid or expired reset token. Please request a new one.');
      } else {
        setErrorMessage('Failed to reset password. Please try again later.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-50">
      <div className="w-full max-w-md p-8 space-y-8 bg-white rounded-lg shadow-md">
        <div>
          <h2 className="text-2xl font-bold text-center text-gray-900">
            {stage === 'request' ? 'Reset your password' : 'Set new password'}
          </h2>
          <p className="mt-2 text-sm text-center text-gray-600">
            <Link to="/login" className="text-indigo-600 hover:text-indigo-500">
              Back to login
            </Link>
          </p>
        </div>

        {errorMessage && (
          <div className="p-3 text-sm text-center text-red-800 bg-red-100 border border-red-300 rounded-md">
            {errorMessage}
          </div>
        )}

        {successMessage && (
          <div className="p-3 text-sm text-center text-green-800 bg-green-100 border border-green-300 rounded-md">
            {successMessage}
          </div>
        )}

        <div className="mt-8 space-y-6">
          {stage === 'request' ? (
            <form onSubmit={requestForm.handleSubmit(onRequestSubmit)} className="space-y-4">
              <div>
                <label htmlFor="email" className="block text-sm font-medium text-gray-700">
                  Email address
                </label>
                <input
                  id="email"
                  type="email"
                  autoComplete="email"
                  placeholder="you@example.com"
                  className="block w-full px-3 py-2 mt-1 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                  {...requestForm.register('email')}
                />
                {requestForm.formState.errors.email && (
                  <p className="mt-1 text-xs text-red-600">
                    {requestForm.formState.errors.email.message}
                  </p>
                )}
              </div>

              <div>
                <button
                  type="submit"
                  disabled={isLoading}
                  className="flex justify-center w-full px-4 py-2 text-sm font-medium text-white bg-indigo-600 border border-transparent rounded-md shadow-sm hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
                >
                  {isLoading ? 'Sending...' : 'Send reset email'}
                </button>
              </div>

              <p className="text-xs text-center text-gray-600">
                Remembered your password?{' '}
                <Link to="/login" className="text-indigo-600 hover:text-indigo-500">
                  Sign in here
                </Link>
              </p>
            </form>
          ) : (
            <form onSubmit={confirmForm.handleSubmit(onConfirmSubmit)} className="space-y-4">
              <input
                type="hidden"
                {...confirmForm.register('token')}
              />

              <div>
                <label htmlFor="new_password" className="block text-sm font-medium text-gray-700">
                  New password
                </label>
                <PasswordInput
                  id="new_password"
                  autoComplete="new-password"
                  className="block w-full px-3 py-2 pr-10 mt-1 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                  {...confirmForm.register('new_password')}
                />
                {confirmForm.formState.errors.new_password && (
                  <p className="mt-1 text-xs text-red-600">
                    {confirmForm.formState.errors.new_password.message}
                  </p>
                )}
                <p className="mt-2 text-xs text-gray-500">
                  Password requirements: at least 12 characters, one uppercase, one lowercase, one number, one special character (!@#$%^&*).
                </p>
              </div>

              <div>
                <button
                  type="submit"
                  disabled={isLoading}
                  className="flex justify-center w-full px-4 py-2 text-sm font-medium text-white bg-indigo-600 border border-transparent rounded-md shadow-sm hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
                >
                  {isLoading ? 'Resetting...' : 'Reset password'}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};

export default PasswordResetPage;
