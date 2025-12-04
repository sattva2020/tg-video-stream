import React, { useEffect, useMemo, useState } from 'react';
import { Card, CardBody, CardHeader, Modal, ModalContent, ModalBody } from '@heroui/react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import GoogleLoginButton from '../GoogleLoginButton';
import { TelegramLogin } from './TelegramLogin';
import ErrorToast from './ErrorToast';
import { Send } from 'lucide-react';
import { authApi } from '../../api/auth';
import { useAuth } from '../../context/AuthContext';

export type AuthMode = 'login' | 'register';

export interface AuthBanner {
  tone: 'success' | 'error';
  message: string;
}

interface AuthCardProps {
  mode?: AuthMode;
  onModeChange?: (nextMode: AuthMode) => void;
  onAuthenticated?: () => void;
  initialBanner?: AuthBanner | null;
}

const AuthCard: React.FC<AuthCardProps> = ({ initialBanner = null }) => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { login: authLogin } = useAuth();
  const [banner, setBanner] = useState<AuthBanner | null>(initialBanner);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isVisible, setIsVisible] = useState(false);
  const [showTelegramModal, setShowTelegramModal] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [formError, setFormError] = useState<string | null>(null);
  const API_URL = useMemo(
    () => import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL || 'http://localhost:8000',
    []
  );
  const enableBasicLogin = (import.meta.env.VITE_ENABLE_BASIC_LOGIN ?? 'true') !== 'false';

  // Плавное появление карточки
  useEffect(() => {
    const timer = setTimeout(() => setIsVisible(true), 300);
    return () => clearTimeout(timer);
  }, []);

  useEffect(() => {
    setBanner(initialBanner ?? null);
  }, [initialBanner]);

  const googleLabel = `${t('or_continue')} Google`;

  // Обработчик успешной авторизации через Telegram
  const handleTelegramSuccess = async (token?: string) => {
    if (token) {
      // Используем authLogin для правильного сохранения токена и обновления состояния
      await authLogin(token);
    }
    setShowTelegramModal(false);
    navigate('/channels');
  };

  const handleBasicLogin = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!enableBasicLogin) {
      return;
    }

    setFormError(null);
    setIsSubmitting(true);
    try {
      const response = await authApi.login({ username: email, password });
      await authLogin(response.access_token);
      navigate('/dashboard');
    } catch (error: any) {
      const serverMessage = error?.response?.data?.message;
      const status = error?.response?.status;
      if (status === 401) {
        setFormError(t('invalid_credentials', 'Неверный email или пароль.'));
      } else if (status === 403) {
        setFormError(t('account_pending_or_blocked', 'Учетная запись ожидает одобрения или заблокирована.'));
      } else {
        setFormError(serverMessage ?? t('login_failed_try_again', 'Войти не удалось. Попробуйте ещё раз.'));
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div 
      data-testid="auth-card" 
      className={`h-full transition-all duration-700 ease-out ${isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}`}
    >
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

        <CardBody className="flex flex-col gap-6 px-0">
          {banner && banner.tone === 'error' ? (
            <ErrorToast message={banner.message} data-testid="auth-error-toast" tone="error" />
          ) : banner ? (
            <div
              className="w-full flex justify-center text-center rounded-full bg-white/10 px-4 py-3 text-sm font-medium text-white"
              aria-live="polite"
            >
              {banner.message}
            </div>
          ) : null}

          {/* Основной текст */}
          <p className="text-center text-sm text-[#F5E6D3]/70">
            {t('choose_auth_method', 'Выберите способ входа')}
          </p>

          {enableBasicLogin && (
            <form
              className="flex flex-col gap-3 rounded-3xl border border-white/10 bg-white/5 p-4"
              onSubmit={handleBasicLogin}
              data-testid="credentials-form"
            >
              <div className="space-y-1">
                <label htmlFor="auth-email" className="text-xs uppercase tracking-[0.3em] text-[#F5E6D3]/60">
                  Email
                </label>
                <input
                  id="auth-email"
                  type="email"
                  required
                  autoComplete="email"
                  className="w-full rounded-full border border-white/20 bg-black/20 px-4 py-2 text-sm text-white placeholder:text-white/40 focus:border-white/60 focus:outline-none"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  disabled={isSubmitting}
                  data-testid="email-input"
                />
              </div>

              <div className="space-y-1">
                <label htmlFor="auth-password" className="text-xs uppercase tracking-[0.3em] text-[#F5E6D3]/60">
                  {t('password', 'Пароль')}
                </label>
                <input
                  id="auth-password"
                  type="password"
                  required
                  autoComplete="current-password"
                  className="w-full rounded-full border border-white/20 bg-black/20 px-4 py-2 text-sm text-white placeholder:text-white/40 focus:border-white/60 focus:outline-none"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  disabled={isSubmitting}
                  data-testid="password-input"
                />
              </div>

              {formError && (
                <p className="text-xs text-red-300" role="alert">
                  {formError}
                </p>
              )}

              <button
                type="submit"
                disabled={isSubmitting || !email || !password}
                className="rounded-full bg-[#F5E6D3] px-6 py-2 text-sm font-semibold uppercase tracking-[0.3em] text-black transition hover:bg-white disabled:opacity-50"
                data-testid="login-button"
              >
                {isSubmitting ? t('logging_in', 'Входим…') : t('login', 'Войти')}
              </button>

              <p className="text-center text-[10px] uppercase tracking-[0.35em] text-[#F5E6D3]/50">
                {t('qa_login_hint', 'Для QA и Playwright тестов')}  
              </p>
            </form>
          )}

          {/* Google кнопка */}
          <GoogleLoginButton
            onClick={() => {
              setIsSubmitting(true);
              if (typeof window !== 'undefined') {
                window.location.href = `${API_URL}/api/auth/google`;
              }
            }}
            disabled={isSubmitting}
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

          {/* Telegram кнопка - открывает модальное окно с Pyrogram-авторизацией */}
          <button
            onClick={() => setShowTelegramModal(true)}
            disabled={isSubmitting}
            className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-full
              bg-[#F5E6D3]/10 text-[#F5E6D3] border border-[#F5E6D3]/30
              hover:shadow-[0_0_20px_rgba(245,230,211,0.2)] hover:bg-[#F5E6D3]/20 hover:border-[#F5E6D3]/50
              transition-all duration-300 disabled:opacity-50"
          >
            <Send className="w-5 h-5" />
            <span>{t('login_telegram', 'Войти через Telegram')}</span>
          </button>
        </CardBody>
      </Card>

      {/* Модальное окно для Telegram авторизации */}
      <Modal 
        isOpen={showTelegramModal} 
        onClose={() => setShowTelegramModal(false)}
        size="md"
        backdrop="blur"
        classNames={{
          base: "bg-gray-900 border border-gray-700",
          header: "border-b border-gray-700",
          body: "py-6",
          closeButton: "hover:bg-gray-700 active:bg-gray-600 text-gray-400"
        }}
      >
        <ModalContent>
          <ModalBody>
            <TelegramLogin 
              onSuccess={handleTelegramSuccess} 
              apiPrefix="/api/auth/telegram-login"
            />
          </ModalBody>
        </ModalContent>
      </Modal>
    </div>
  );
};

export default AuthCard;
