import React, { useEffect, useState, Suspense, lazy } from 'react';
import { useNavigate, useSearchParams, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import AuthCard, { type AuthMode, type AuthBanner } from '../components/auth/AuthCard';
import { LanguageSwitcher } from '../components/auth/LanguageSwitcher';
import AuthLayout from '../components/auth/AuthLayout';

// Lazy load the 3D scene to improve TBT/LCP
const AuthZenScene = lazy(() => import('../components/auth/ZenScene'));

const AuthPage3D: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const [mode, setMode] = useState<AuthMode>('login');
  const [banner, setBanner] = useState<AuthBanner | null>(null);
  const [scrollY, setScrollY] = useState(0);

  const forceStatic = searchParams.get('forceStatic') === '1';

  useEffect(() => {
    if (location.pathname.includes('/register')) {
      setMode('register');
    } else {
      setMode('login');
    }
  }, [location.pathname]);

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
    <div
      data-testid="auth-page"
      className="relative min-h-screen overflow-hidden bg-[color:var(--color-surface)] text-[color:var(--color-text)] font-landing-sans"
    >
      <Suspense fallback={<div className="absolute inset-0 bg-[color:var(--color-surface)]" />}>
        <AuthZenScene scrollY={scrollY} forceStatic={forceStatic} />
      </Suspense>

      <AuthLayout
        hero={
          <header className="space-y-3">
            <div className="flex items-center justify-between">
              <p className="text-xs uppercase tracking-[0.45em] text-[color:var(--color-text-muted)]">Sattva studio</p>
              <div className="flex items-center gap-4">
                <LanguageSwitcher className="text-[#F7E2C6]" />
              </div>
            </div>
          </header>
        }
        primary={
          <AuthCard
            mode={mode}
            onModeChange={setMode}
            onAuthenticated={handleAuthenticated}
            initialBanner={banner}
          />
        }
      />
    </div>
  );
};

export default AuthPage3D;
