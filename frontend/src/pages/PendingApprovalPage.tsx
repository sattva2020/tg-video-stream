import React, { Suspense, lazy } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { LanguageSwitcher } from '../components/auth/LanguageSwitcher';
import AuthLayout from '../components/auth/AuthLayout';

// Lazy load the 3D scene
const AuthZenScene = lazy(() => import('../components/auth/ZenScene'));

const PendingApprovalPage: React.FC = () => {
  const { t } = useTranslation();

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
              {t('pending_approval_message', 'Ваш аккаунт успешно создан и ожидает подтверждения администратором. Мы уведомим вас, когда доступ будет предоставлен.')}
            </p>

            {/* Info box */}
            <div className="w-full p-4 rounded-xl bg-[#F7E2C6]/5 border border-[#F7E2C6]/20 mb-6">
              <p className="text-sm text-[#e5d9c7]/70 text-center">
                {t('pending_approval_info', 'Обычно проверка занимает несколько часов. Вы можете закрыть эту страницу.')}
              </p>
            </div>

            {/* Back to login link */}
            <Link 
              to="/login"
              className="text-sm text-[#F7E2C6]/70 hover:text-[#F7E2C6] transition-colors duration-300 underline underline-offset-4"
            >
              {t('back_to_login', 'Вернуться на страницу входа')}
            </Link>
          </div>
        }
      />
    </div>
  );
};

export default PendingApprovalPage;
