import React, { useEffect, useState } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import GoogleLoginButton from '../components/GoogleLoginButton';
import { authApi } from '../api/auth';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { LoginSchema, type LoginRequest } from '../api/auth';

const errorMap: { [key: string]: string } = {
  state_mismatch: 'Authentication failed. State mismatch (CSRF protection). Please try again.',
  token_fetch_failed: 'Could not verify authentication with Google. Please try again.',
  user_info_failed: 'Could not fetch your user profile from Google. Please try again.',
  auth_process_failed: 'An error occurred during the authentication process. Please try again.',
  invalid_callback: 'Invalid callback request. Please initiate login from this page.',
  callback_no_token: 'Authentication callback from server did not contain a token.',
};

const LoginPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginRequest>({
    resolver: zodResolver(LoginSchema),
  });

  useEffect(() => {
    const errorKey = searchParams.get('error');
    if (errorKey && errorMap[errorKey]) {
      setErrorMessage(errorMap[errorKey]);
    } else if (errorKey) {
      setErrorMessage('An unknown error occurred. Please try again.');
    }
  }, [searchParams]);

  const handleGoogleLogin = () => {
    window.location.href = '/api/auth/google';
  };

  const onSubmit = async (data: LoginRequest) => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const response = await authApi.login(data);
      localStorage.setItem('token', response.access_token);
      navigate('/dashboard'); // Redirect to dashboard after login
    } catch (error: any) {
      console.error('Login failed:', error);
      if (error.response?.status === 401) {
        setErrorMessage('Invalid email or password.');
      } else {
        setErrorMessage('Login failed. Please try again later.');
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
            Sign in to your account
          </h2>
          <p className="mt-2 text-sm text-center text-gray-600">
            Or{' '}
            <Link to="/register" className="text-indigo-600 hover:text-indigo-500">
              create a new account
            </Link>
          </p>
        </div>

        {errorMessage && (
          <div className="p-3 text-sm text-center text-red-800 bg-red-100 border border-red-300 rounded-md">
            {errorMessage}
          </div>
        )}

        <div className="mt-8 space-y-6">
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div>
              <label htmlFor="username" className="block text-sm font-medium text-gray-700">
                Email address
              </label>
              <input
                id="username"
                type="email"
                autoComplete="email"
                className="block w-full px-3 py-2 mt-1 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                {...register('username')}
              />
              {errors.username && (
                <p className="mt-1 text-xs text-red-600">{errors.username.message}</p>
              )}
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700">
                Password
              </label>
              <input
                id="password"
                type="password"
                autoComplete="current-password"
                className="block w-full px-3 py-2 mt-1 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                {...register('password')}
              />
              {errors.password && (
                <p className="mt-1 text-xs text-red-600">{errors.password.message}</p>
              )}
            </div>

            <div>
              <button
                type="submit"
                disabled={isLoading}
                className="flex justify-center w-full px-4 py-2 text-sm font-medium text-white bg-indigo-600 border border-transparent rounded-md shadow-sm hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
              >
                {isLoading ? 'Signing in...' : 'Sign in'}
              </button>
            </div>

            <div className="text-sm text-center">
              <Link to="/password-reset" className="text-indigo-600 hover:text-indigo-500">
                Forgot your password?
              </Link>
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

export default LoginPage;