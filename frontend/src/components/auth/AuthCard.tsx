import React, { useEffect, useMemo, useState } from 'react';
import { Card, CardBody, CardHeader, Chip, Link } from '@heroui/react';
import { useTranslation } from 'react-i18next';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import clsx from 'clsx';
import GoogleLoginButton from '../GoogleLoginButton';
import { authClient, isAuthClientError } from '../../lib/api/authClient';
import ErrorToast from './ErrorToast';
import { normalizeAuthError } from '../../services/authService';
import { useAuth } from '../../context/AuthContext';

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

const passwordSchema = z
  .string()
  .min(12, 'Пароль должен содержать не менее 12 символов')
  .regex(/[A-Z]/, 'Пароль должен содержать заглавную букву')
  .regex(/[a-z]/, 'Пароль должен содержать строчную букву')
  .regex(/[0-9]/, 'Пароль должен содержать цифру')
  .regex(/[!@#$%^&*]/, 'Пароль должен содержать специальный символ');

const loginSchema = z.object({
  email: z.string().email('Введите корректный email'),
  password: z.string().min(1, 'Введите пароль'),
});

const registerSchema = z
  .object({
    email: z.string().email('Введите корректный email'),
    fullName: z
      .union([z.string().max(120, 'Слишком длинное имя'), z.literal('')])
      .transform((value) => (value?.trim() ? value.trim() : undefined)),
    password: passwordSchema,
    confirmPassword: z.string().min(1, 'confirm_password'),
  })
  .refine((values) => values.password === values.confirmPassword, {
    path: ['confirmPassword'],
    message: 'passwords_mismatch',
  });

export type LoginFormValues = z.infer<typeof loginSchema>;
export type RegisterFormValues = z.infer<typeof registerSchema>;

const INPUT_BASE =
  'w-full rounded-2xl border border-[#F5E6D3]/30 bg-[#F5E6D3]/10 px-5 py-3 text-base text-[#F5E6D3] placeholder:text-[#F5E6D3]/50 shadow-inner transition focus-visible:border-[#F5E6D3] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F5E6D3]/30';

const CTA_LABEL: Record<AuthMode, string> = {
  login: 'enter',
  register: 'begin',
};

const AuthCard: React.FC<AuthCardProps> = ({ mode, onModeChange, onAuthenticated, initialBanner = null }) => {
  const { t } = useTranslation();
  const { login } = useAuth();
  const [banner, setBanner] = useState<AuthBanner | null>(initialBanner);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const API_URL = useMemo(
    () => import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL || 'http://localhost:8000',
    []
  );

  useEffect(() => {
    setBanner(initialBanner ?? null);
  }, [initialBanner]);

  const loginForm = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    mode: 'onBlur',
    reValidateMode: 'onBlur',
    defaultValues: { email: '', password: '' },
  });

  const registerForm = useForm<RegisterFormValues>({
    resolver: zodResolver(registerSchema),
    mode: 'onBlur',
    reValidateMode: 'onBlur',
    defaultValues: { email: '', password: '', confirmPassword: '', fullName: '' },
  });

  const toggleMode = () => {
    const nextMode = mode === 'login' ? 'register' : 'login';
    onModeChange(nextMode);
    setBanner(null);
  };

  const setErrorBanner = (message: string) => setBanner({ tone: 'error', message });

  const handleLoginSubmit = loginForm.handleSubmit(async (values) => {
    setIsSubmitting(true);
    setBanner(null);
    try {
      const session = await authClient.login({ email: values.email, password: values.password });
      await login(session.access_token);
      setBanner({ tone: 'success', message: t('enter_stream') });
      onAuthenticated?.();
    } catch (error) {
      if (isAuthClientError(error)) {
        const parsed = normalizeAuthError(error);
        setErrorBanner(parsed.message);
      } else {
        setErrorBanner(t('login_failed'));
      }
    } finally {
      setIsSubmitting(false);
    }
  });

  const handleRegisterSubmit = registerForm.handleSubmit(async (values) => {
    setIsSubmitting(true);
    setBanner(null);
    try {
      await authClient.register({
        email: values.email,
        password: values.password,
        full_name: values.fullName,
      });
      setBanner({ tone: 'success', message: t('account_pending') });
      onModeChange('login');
    } catch (error) {
      if (isAuthClientError(error)) {
        const parsed = normalizeAuthError(error);
        setErrorBanner(parsed.message);
      } else {
        setErrorBanner(t('registration_failed'));
      }
    } finally {
      setIsSubmitting(false);
    }
  });

  const googleLabel = `${t('or_continue')} Google`;

  const renderFieldError = (field?: { message?: string }) =>
    field?.message ? (
      <p className="mt-2 text-xs font-medium text-red-400">{t(field.message)}</p>
    ) : null;

  return (
    <div data-testid="auth-card" className="h-full">
      <Card
        shadow="none"
        className="relative z-10 h-full w-full bg-transparent p-0 text-white"
      >
      <CardHeader className="flex flex-col gap-2 rounded-[32px] bg-[#F5E6D3]/10 backdrop-blur-md border border-[#F5E6D3]/30 p-6 mb-6 shadow-lg">
        <p className="text-xs uppercase tracking-[0.45em] text-[#F5E6D3]/60 [text-shadow:1px_1px_0_#000,-1px_-1px_0_#000,1px_-1px_0_#000,-1px_1px_0_#000]">ZenScene Access</p>
        <h2 className="font-landing-serif text-3xl text-[#F5E6D3] [text-shadow:1px_1px_0_#000,-1px_-1px_0_#000,1px_-1px_0_#000,-1px_1px_0_#000]" data-testid="auth-headline">
          {mode === 'login' ? t('sattva') : t('join_us')}
        </h2>
        <p className="text-sm text-[#F5E6D3]/70">
          {mode === 'login' ? t('enter_stream') : t('begin_journey')}
        </p>
      </CardHeader>
      <CardBody className="flex flex-col gap-6 px-2">
        {banner && banner.tone === 'error' ? (
          <ErrorToast message={banner.message} data-testid="auth-error-toast" tone="error" />
        ) : banner ? (
          <Chip
            color={banner.tone === 'success' ? 'success' : 'default'}
            variant="bordered"
            className="justify-start border-0 bg-white/10 px-4 py-3 text-sm font-medium text-white"
            aria-live="polite"
          >
            {banner.message}
          </Chip>
        ) : null}

        {mode === 'login' ? (
          <form className="space-y-4" onSubmit={handleLoginSubmit}>
            <div>
              <label className="text-xs uppercase tracking-[0.3em] text-white/60" htmlFor="login-email">
                {t('email')}
              </label>
              <input
                id="login-email"
                type="email"
                autoComplete="email"
                className={INPUT_BASE}
                placeholder="founder@sattva.studio"
                {...loginForm.register('email')}
              />
              {renderFieldError(loginForm.formState.errors.email)}
            </div>
            <div>
              <label className="text-xs uppercase tracking-[0.3em] text-white/60" htmlFor="login-password">
                {t('password')}
              </label>
              <input
                id="login-password"
                type="password"
                autoComplete="current-password"
                className={INPUT_BASE}
                placeholder="••••••••••••"
                {...loginForm.register('password')}
              />
              {renderFieldError(loginForm.formState.errors.password)}
            </div>
            <button
              type="submit"
              data-testid="auth-primary-action"
              disabled={isSubmitting}
              className={clsx(
                'w-full rounded-2xl bg-[#F5E6D3]/10 px-6 py-4 text-center text-base font-semibold uppercase tracking-[0.4em] text-[#F5E6D3] shadow-xl transition-all duration-300 border border-[#F5E6D3]/30',
                isSubmitting ? 'opacity-60' : 'hover:shadow-[0_0_20px_rgba(245,230,211,0.2)] hover:bg-[#F5E6D3]/20 hover:border-[#F5E6D3]/50 hover:scale-[1.02]',
              )}
            >
              {isSubmitting ? t('entering') : t(CTA_LABEL[mode])}
            </button>
          </form>
        ) : (
          <form className="space-y-4" onSubmit={handleRegisterSubmit}>
            <div>
              <label className="text-xs uppercase tracking-[0.3em] text-white/60" htmlFor="register-email">
                {t('email')}
              </label>
              <input
                id="register-email"
                type="email"
                autoComplete="email"
                className={INPUT_BASE}
                placeholder="founder@sattva.studio"
                {...registerForm.register('email')}
              />
              {renderFieldError(registerForm.formState.errors.email)}
            </div>
            <div>
              <label className="text-xs uppercase tracking-[0.3em] text-white/60" htmlFor="register-full-name">
                {t('full_name')}
              </label>
              <input
                id="register-full-name"
                type="text"
                autoComplete="name"
                className={INPUT_BASE}
                placeholder="Aleksandra P."
                {...registerForm.register('fullName')}
              />
              {renderFieldError(registerForm.formState.errors.fullName)}
            </div>
            <div>
              <label className="text-xs uppercase tracking-[0.3em] text-white/60" htmlFor="register-password">
                {t('password')}
              </label>
              <input
                id="register-password"
                type="password"
                autoComplete="new-password"
                className={INPUT_BASE}
                placeholder="••••••••••••"
                {...registerForm.register('password')}
              />
              <p className="mt-2 text-xs text-white/60">{t('password_requirements')}</p>
              {renderFieldError(registerForm.formState.errors.password)}
            </div>
            <div>
              <label className="text-xs uppercase tracking-[0.3em] text-white/60" htmlFor="register-confirm-password">
                {t('confirm_password')}
              </label>
              <input
                id="register-confirm-password"
                type="password"
                autoComplete="new-password"
                className={INPUT_BASE}
                placeholder="••••••••••••"
                {...registerForm.register('confirmPassword')}
              />
              {renderFieldError(registerForm.formState.errors.confirmPassword)}
            </div>
            <button
              type="submit"
              data-testid="auth-primary-action"
              disabled={isSubmitting}
              className={clsx(
                'w-full rounded-2xl bg-[#F5E6D3]/10 px-6 py-4 text-center text-base font-semibold uppercase tracking-[0.4em] text-[#F5E6D3] shadow-xl transition-all duration-300 border border-[#F5E6D3]/30',
                isSubmitting ? 'opacity-60' : 'hover:shadow-[0_0_20px_rgba(245,230,211,0.2)] hover:bg-[#F5E6D3]/20 hover:border-[#F5E6D3]/50 hover:scale-[1.02]',
              )}
            >
              {isSubmitting ? t('joining') : t(CTA_LABEL[mode])}
            </button>
          </form>
        )}

        <div className="flex justify-center">
          <Link
            as="button"
            onPress={toggleMode}
            className="text-sm text-white/80 hover:text-white underline cursor-pointer"
          >
            {mode === 'login' ? t('dont_have_account') : t('already_have_account')}
          </Link>
        </div>

        <div className="relative">
          <div className="absolute inset-0 flex items-center" aria-hidden="true">
            <div className="w-full border-t border-white/15" />
          </div>
          <div className="relative flex justify-center text-xs uppercase tracking-[0.4em]">
            <span className="bg-transparent px-3 text-white/60">{t('or_continue')}</span>
          </div>
        </div>

        <GoogleLoginButton
          onClick={() => {
            if (typeof window !== 'undefined') {
              window.location.href = `${API_URL}/api/auth/google`;
            }
          }}
          disabled={isSubmitting}
          label={googleLabel}
          className="!bg-[#F5E6D3]/10 !text-[#F5E6D3] !border-[#F5E6D3]/30 hover:!shadow-[0_0_20px_rgba(245,230,211,0.2)] hover:!bg-[#F5E6D3]/20 hover:!border-[#F5E6D3]/50 border transition-all duration-300"
        />
      </CardBody>
    </Card>
  </div>
  );
};

export default AuthCard;
