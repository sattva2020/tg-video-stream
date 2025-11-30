import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import GoogleLoginButton from '../components/GoogleLoginButton';
import { PasswordInput } from '../components/ui/PasswordInput';
import { authApi } from '../api/auth';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { RegisterSchema, type RegisterRequest } from '../api/auth';

const RegisterPage: React.FC = () => {
  const navigate = useNavigate();
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<RegisterRequest>({
    resolver: zodResolver(RegisterSchema),
  });

  const handleGoogleLogin = () => {
    const API_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
    window.location.href = `${API_URL}/api/auth/google`;
  };

  const onSubmit = async (data: RegisterRequest) => {
    setIsLoading(true);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      const response = await authApi.register(data);
      
      if (response.status === 'pending') {
        setSuccessMessage('Registration successful! Your account is awaiting administrator approval. You will be notified once approved.');
        // Do not redirect immediately, let the user read the message
      } else if (response.access_token) {
        localStorage.setItem('token', response.access_token);
        setSuccessMessage('Registration successful! Redirecting to dashboard...');
        setTimeout(() => {
          navigate('/dashboard');
        }, 1500);
      } else {
        // Fallback for unexpected response
        setSuccessMessage('Registration successful! Please log in.');
        setTimeout(() => {
          navigate('/login');
        }, 2000);
      }
    } catch (error: any) {
      console.error('Registration failed:', error);
      if (error.response?.status === 400) {
        setErrorMessage(error.response?.data?.detail || 'Email already registered.');
      } else if (error.response?.status === 409) {
        setErrorMessage('Email already exists. Please use a different email.');
      } else {
        setErrorMessage('Registration failed. Please try again later.');
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
            Create your account
          </h2>
          <p className="mt-2 text-sm text-center text-gray-600">
            Or{' '}
            <Link to="/login" className="text-indigo-600 hover:text-indigo-500">
              sign in to your existing account
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
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700">
                Email address
              </label>
              <input
                id="email"
                type="email"
                autoComplete="email"
                className="block w-full px-3 py-2 mt-1 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                {...register('email')}
              />
              {errors.email && (
                <p className="mt-1 text-xs text-red-600">{errors.email.message}</p>
              )}
            </div>

            <div>
              <label htmlFor="full_name" className="block text-sm font-medium text-gray-700">
                Full name (optional)
              </label>
              <input
                id="full_name"
                type="text"
                autoComplete="name"
                className="block w-full px-3 py-2 mt-1 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                {...register('full_name')}
              />
              {errors.full_name && (
                <p className="mt-1 text-xs text-red-600">{errors.full_name.message}</p>
              )}
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700">
                Password
              </label>
              <PasswordInput
                id="password"
                autoComplete="new-password"
                className="block w-full px-3 py-2 pr-10 mt-1 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                {...register('password')}
              />
              {errors.password && (
                <p className="mt-1 text-xs text-red-600">{errors.password.message}</p>
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
                {isLoading ? 'Creating account...' : 'Create account'}
              </button>
            </div>
          </form>

          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-300" />
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-2 text-gray-500 bg-white">Or continue with</span>
            </div>
          </div>

          <div>
            <GoogleLoginButton onClick={handleGoogleLogin} />
          </div>
        </div>
      </div>
    </div>
  );
};

export default RegisterPage;
