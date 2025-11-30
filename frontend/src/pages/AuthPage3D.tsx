import React, { useEffect, useState, Suspense, lazy } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import AuthCard, { type AuthBanner } from '../components/auth/AuthCard';
import { LanguageSwitcher } from '../components/auth/LanguageSwitcher';
import AuthLayout from '../components/auth/AuthLayout';

// Lazy load the 3D scene to improve TBT/LCP
const AuthZenScene = lazy(() => import('../components/auth/ZenScene'));

const AuthPage3D: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [banner, setBanner] = useState<AuthBanner | null>(null);
  const [scrollY, setScrollY] = useState(0);

  const forceStatic = searchParams.get('forceStatic') === '1';

  useEffect(() => {
    const status = searchParams.get('status');
    const error = searchParams.get('error');

    if (status === 'pending') {
      setBanner({ tone: 'success', message: t('account_pending') });
      return;
    }

    if (error) {
      const friendlyMap: Record<string, string> = {
        state_mismatch: t('Authentication failed. State mismatch (CSRF protection). Please try again.'),
        token_fetch_failed: t('Could not verify authentication with Google. Please try again.'),
        user_info_failed: t('Could not fetch your user profile from Google. Please try again.'),
        auth_process_failed: t('An error occurred during the authentication process. Please try again.'),
        invalid_callback: t('Invalid callback request. Please initiate login from this page.'),
        callback_no_token: t('Authentication callback from server did not contain a token.'),
      };

      setBanner({ tone: 'error', message: friendlyMap[error] ?? t(error) ?? error });
      return;
    }

    setBanner(null);
  }, [searchParams, t]);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }

    const handleScroll = () => setScrollY(window.scrollY);
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const handleAuthenticated = () => {
    navigate('/dashboard');
  };

  return (
    <>
      <div
        data-testid="auth-page"
        data-theme="dark"
        className="relative min-h-screen overflow-hidden bg-[#0c0a09] text-[#e5d9c7] font-landing-sans"
      >
        <Suspense fallback={<div className="absolute inset-0 bg-[#0c0a09]" />}>
          <AuthZenScene scrollY={scrollY} forceStatic={forceStatic} />
        </Suspense>

        <AuthLayout
          hero={
            <header className="space-y-3">
              <div className="flex items-center justify-between">
                {/* Кликабельный логотип - переход на главную */}
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
            <AuthCard
              mode="login"
              onModeChange={() => {}}
              onAuthenticated={handleAuthenticated}
              initialBanner={banner}
            />
          }
        />
      </div>
    </>
  );
};

export default AuthPage3D;
