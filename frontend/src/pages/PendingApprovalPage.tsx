import React, { Suspense, lazy, useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { LanguageSwitcher } from '../components/auth/LanguageSwitcher';
import AuthLayout from '../components/auth/AuthLayout';
import { useAuth } from '../context/AuthContext';

// Lazy load the 3D scene
const AuthZenScene = lazy(() => import('../components/auth/ZenScene'));

const PendingApprovalPage: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { isAuthenticated, isPendingApproval, isLoading, refreshUser } = useAuth();
  const [isChecking, setIsChecking] = useState(false);

  // Auto-redirect if approved
  useEffect(() => {
    if (!isLoading && isAuthenticated && !isPendingApproval) {
      navigate('/dashboard', { replace: true });
    }
  }, [isAuthenticated, isPendingApproval, isLoading, navigate]);

  // Polling for approval status
  useEffect(() => {
    if (!isPendingApproval) return;

    const interval = setInterval(() => {
      refreshUser();
    }, 10000); // Check every 10 seconds

    return () => clearInterval(interval);
  }, [isPendingApproval, refreshUser]);

  const handleCheckStatus = async () => {
    setIsChecking(true);
    await refreshUser();
    setTimeout(() => setIsChecking(false), 1000);
  };

  return (
    <div
      data-testid="pending-approval-page"
      data-theme="dark"
      className="relative min-h-screen overflow-hidden bg-[#0c0a09] text-[#e5d9c7] font-landing-sans"
    >
      <Suspense fallback={<div className="absolute inset-0 bg-[#0c0a09]" />}>
        <AuthZenScene scrollY={0} forceStatic={false} />
      </Suspense>

      <AuthLayout
        hero={
          <header className="space-y-3">
            <div className="flex items-center justify-between">
              <Link 
                to="/"
                className="text-xs uppercase tracking-[0.45em] text-[#e5d9c7]/70 hover:text-[#F7E2C6] transition-colors duration-300 cursor-pointer"
                title="Go to Home"
              >
                Sattva studio
              </Link>
              <div className="flex items-center gap-4">
                <LanguageSwitcher className="text-[#F7E2C6]" />
              </div>
            </div>
          </header>
        }
        primary={
          <div className="relative z-10 flex flex-col items-center justify-center p-8 rounded-2xl bg-black/30 backdrop-blur-md border border-[#e5d9c7]/10">
            {/* Icon */}
            <div className="mb-6">
              <svg 
                className="w-20 h-20 text-[#F7E2C6]" 
                fill="none" 
                stroke="currentColor" 
                viewBox="0 0 24 24"
              >
                <path 
                  strokeLinecap="round" 
                  strokeLinejoin="round" 
                  strokeWidth={1.5} 
                  d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" 
                />
              </svg>
            </div>

            {/* Title */}
            <h1 className="text-2xl font-semibold text-[#F7E2C6] mb-4 text-center">
              {t('pending_approval_title', 'Ожидание подтверждения')}
            </h1>

            {/* Message */}
            <p className="text-[#e5d9c7]/80 text-center mb-6 max-w-sm leading-relaxed">
              {t('pending_approval_message', 'Аккаунт создан, но ожидает подтверждения.')}
            </p>

            {/* Info box */}
            <div className="w-full p-4 rounded-xl bg-[#F7E2C6]/5 border border-[#F7E2C6]/20 mb-6">
              <p className="text-sm text-[#e5d9c7]/70 text-center">
                {t('pending_approval_info', 'Обычно проверка занимает несколько часов. Вы можете закрыть эту страницу.')}
              </p>
            </div>

            {/* Action Buttons */}
            <div className="flex flex-col w-full gap-3">
              {/* Animated Check Status Button with border glow */}
              <div className="relative group">
                {/* Animated gradient border */}
                <div className="absolute -inset-0.5 bg-gradient-to-r from-[#F7E2C6] via-[#d4a574] to-[#F7E2C6] rounded-xl opacity-75 group-hover:opacity-100 blur-sm transition duration-500 animate-gradient-x"></div>
                <button
                  onClick={handleCheckStatus}
                  disabled={isChecking || isLoading}
                  className="relative w-full py-3 px-4 rounded-xl bg-[#F7E2C6] text-[#0c0a09] font-medium hover:bg-[#e5d9c7] transition-all duration-300 flex items-center justify-center gap-2 disabled:opacity-70"
                >
                  {/* Spinning arrows icon */}
                  <svg 
                    className={`w-5 h-5 transition-transform duration-300 ${isChecking ? 'animate-spin' : 'group-hover:rotate-180'}`} 
                    fill="none" 
                    stroke="currentColor" 
                    viewBox="0 0 24 24"
                  >
                    <path 
                      strokeLinecap="round" 
                      strokeLinejoin="round" 
                      strokeWidth={2} 
                      d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" 
                    />
                  </svg>
                  <span>{isChecking ? t('checking', 'Проверяем...') : t('check_status', 'Проверить статус')}</span>
                </button>
              </div>

              <Link 
                to="/login"
                onClick={() => {
                  // Clear token to allow logging in with another account if needed
                  localStorage.removeItem('token');
                }}
                className="text-sm text-[#F7E2C6]/70 hover:text-[#F7E2C6] transition-colors duration-300 underline underline-offset-4 text-center"
              >
                {t('back_to_login', 'Вернуться на страницу входа')}
              </Link>
            </div>
          </div>
        }
      />
    </div>
  );
};

export default PendingApprovalPage;
