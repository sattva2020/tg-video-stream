import React, { useEffect, useMemo, useState } from 'react';
import { Card, CardBody, CardHeader, Chip } from '@heroui/react';
import { useTranslation } from 'react-i18next';
import GoogleLoginButton from '../GoogleLoginButton';
import TelegramLoginButton from '../TelegramLoginButton';
import ErrorToast from './ErrorToast';
import { useTelegramAuth } from '../../hooks/useTelegramAuth';

export type AuthMode = 'login' | 'register';

export interface AuthBanner {
  tone: 'success' | 'error';
  message: string;
}

interface AuthCardProps {
  mode: AuthMode;
  onModeChange: (nextMode: AuthMode) => void;
  onAuthenticated?: () => void;
  initialBanner?: AuthBanner | null;
}

const AuthCard: React.FC<AuthCardProps> = ({ mode, onAuthenticated, initialBanner = null }) => {
  const { t } = useTranslation();
  const [banner, setBanner] = useState<AuthBanner | null>(initialBanner);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const API_URL = useMemo(
    () => import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL || 'http://localhost:8000',
    []
  );
  
  // Telegram auth hook
  const { 
    isLoading: isTelegramLoading, 
    error: telegramError, 
    handleTelegramAuth 
  } = useTelegramAuth();

  // Показываем ошибку Telegram если есть
  useEffect(() => {
    if (telegramError) {
      setBanner({ tone: 'error', message: telegramError });
    }
  }, [telegramError]);

  useEffect(() => {
    setBanner(initialBanner ?? null);
  }, [initialBanner]);

  const googleLabel = `${t('or_continue')} Google`;

  return (
    <div data-testid="auth-card" className="h-full">
      <Card
        shadow="none"
        className="relative z-10 h-full w-full bg-transparent p-0 text-white"
      >
        <CardHeader className="flex flex-col items-center gap-3 rounded-[32px] bg-[#F5E6D3]/10 backdrop-blur-md border border-[#F5E6D3]/30 p-6 mb-6 shadow-lg">
          <p className="text-xs uppercase tracking-[0.45em] text-[#F5E6D3]/60 [text-shadow:1px_1px_0_#000,-1px_-1px_0_#000,1px_-1px_0_#000,-1px_1px_0_#000]">{t('zenscene_access')}</p>
          <h2 className="font-landing-serif text-3xl text-[#F5E6D3] [text-shadow:1px_1px_0_#000,-1px_-1px_0_#000,1px_-1px_0_#000,-1px_1px_0_#000]" data-testid="auth-headline">
            {t('sattva')}
          </h2>
          <p className="text-sm text-[#F5E6D3]/70">
            {t('enter_stream')}
          </p>
        </CardHeader>

        <CardBody className="flex flex-col gap-6 px-2">
          {banner && banner.tone === 'error' ? (
            <ErrorToast message={banner.message} data-testid="auth-error-toast" tone="error" />
          ) : banner ? (
            <Chip
              color={banner.tone === 'success' ? 'success' : 'default'}
              variant="bordered"
              className="w-full justify-center text-center border-0 bg-white/10 px-4 py-3 text-sm font-medium text-white"
              aria-live="polite"
            >
              {banner.message}
            </Chip>
          ) : null}

          {/* Основной текст */}
          <p className="text-center text-sm text-[#F5E6D3]/70">
            {t('choose_auth_method', 'Выберите способ входа')}
          </p>

          {/* Google кнопка */}
          <GoogleLoginButton
            onClick={() => {
              setIsSubmitting(true);
              if (typeof window !== 'undefined') {
                window.location.href = `${API_URL}/api/auth/google`;
              }
            }}
            disabled={isSubmitting || isTelegramLoading}
            label={googleLabel}
            className="!bg-[#F5E6D3]/10 !text-[#F5E6D3] !border-[#F5E6D3]/30 hover:!shadow-[0_0_20px_rgba(245,230,211,0.2)] hover:!bg-[#F5E6D3]/20 hover:!border-[#F5E6D3]/50 border transition-all duration-300"
          />

          {/* Разделитель */}
          <div className="relative">
            <div className="absolute inset-0 flex items-center" aria-hidden="true">
              <div className="w-full border-t border-white/15" />
            </div>
            <div className="relative flex justify-center text-xs uppercase tracking-[0.4em]">
              <span className="bg-transparent px-3 text-white/60">{t('or', 'или')}</span>
            </div>
          </div>

          {/* Telegram кнопка */}
          <TelegramLoginButton
            onAuth={handleTelegramAuth}
            disabled={isSubmitting || isTelegramLoading}
          />
        </CardBody>
      </Card>
    </div>
  );
};

export default AuthCard;
