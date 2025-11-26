import React, { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';

const AuthCallback: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { t } = useTranslation();
  const { login } = useAuth();

  useEffect(() => {
    const token = searchParams.get('token');
    const error = searchParams.get('error');

    const handleLogin = async (token: string) => {
      try {
        await login(token);
        navigate('/dashboard', { replace: true });
      } catch (err) {
        console.error("Login failed in callback", err);
        navigate('/login?error=auth_process_failed', { replace: true });
      }
    };

    if (token) {
      handleLogin(token);
    } else if (error) {
      navigate(`/login?error=${error}`, { replace: true });
    } else {
      navigate('/login?error=oauth_failed', { replace: true });
    }
  }, [searchParams, navigate, login]);

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-900 text-white">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-indigo-500 mx-auto mb-4"></div>
        <h2 className="text-xl font-semibold">{t('entering', 'Entering...')}</h2>
        <p className="text-gray-400 mt-2">Processing Google Login...</p>
      </div>
    </div>
  );
};

export default AuthCallback;
