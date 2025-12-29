/**
 * Страница настроек пользователя.
 * 
 * Включает:
 * - Информация о профиле
 * - Связанные аккаунты (Google, Telegram, Email)
 * - Внешний вид (тема, язык)
 * - Уведомления
 * - Безопасность
 * - О приложении
 */
import React, { useState, useCallback, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';
import { UserRole } from '../types/user';
import { ResponsiveHeader } from '../components/layout';
import TelegramLoginButton from '../components/TelegramLoginButton';
import { telegramAuthApi, TelegramAuthData } from '../services/telegramAuth';
import { totpApi, type TotpSetupResponse } from '../api/totp';
import { 
  Sun, Moon, Monitor, Globe, Bell,
  Shield, LogOut, Info, ExternalLink,
  Mail, MessageSquare, Smartphone
} from 'lucide-react';
import { DEFAULT_LOGO, getUserLogo, resetUserLogo, setUserLogo } from '../utils/branding';

// Версия приложения
const APP_VERSION = '1.0.0';

const SettingsPage: React.FC = () => {
  const { i18n } = useTranslation();
  const { user, refreshUser, logout } = useAuth();
  const [isLinking, setIsLinking] = useState(false);
  const [isUnlinking, setIsUnlinking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [totpSetup, setTotpSetup] = useState<TotpSetupResponse | null>(null);
  const [totpCode, setTotpCode] = useState('');
  const [totpDisableCode, setTotpDisableCode] = useState('');
  const [totpError, setTotpError] = useState<string | null>(null);
  const [totpSuccess, setTotpSuccess] = useState<string | null>(null);
  const [totpLoading, setTotpLoading] = useState(false);
  const [logoPreview, setLogoPreview] = useState<string>(() => getUserLogo(user?.id) || DEFAULT_LOGO);
  const [isSavingLogo, setIsSavingLogo] = useState(false);
  
  // Настройки уведомлений (локальное состояние, можно связать с API)
  const [notifications, setNotifications] = useState({
    email: true,
    push: false,
    telegram: true,
  });

  const isAdmin = user?.role === UserRole.ADMIN || user?.role === UserRole.SUPERADMIN;

  // Текущий язык
  const currentLang = i18n.resolvedLanguage?.split('-')[0] || 'ru';
  
  // Текущая тема (из CSS переменной или localStorage)
  const [theme, setTheme] = useState<'light' | 'dark' | 'system'>(() => {
    const saved = localStorage.getItem('theme');
    return (saved as 'light' | 'dark' | 'system') || 'dark';
  });

  const handleThemeChange = (newTheme: 'light' | 'dark' | 'system') => {
    setTheme(newTheme);
    localStorage.setItem('theme', newTheme);
    // Применяем тему
    if (newTheme === 'system') {
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      document.documentElement.setAttribute('data-theme', prefersDark ? 'dark' : 'light');
    } else {
      document.documentElement.setAttribute('data-theme', newTheme);
    }
  };

  const handleLanguageChange = (lang: string) => {
    i18n.changeLanguage(lang);
  };

  const handleLinkTelegram = useCallback(async (data: TelegramAuthData) => {
    setIsLinking(true);
    setError(null);
    setSuccess(null);

    try {
      const response = await telegramAuthApi.link(data);
      if (response.success) {
        setSuccess('Telegram успешно привязан!');
        // Обновляем данные пользователя
        if (refreshUser) {
          await refreshUser();
        }
      }
    } catch (err: any) {
      console.error('Failed to link Telegram:', err);
      if (err.response?.status === 409) {
        setError(err.response?.data?.detail || 'Этот Telegram уже привязан.');
      } else {
        setError('Не удалось привязать Telegram. Попробуйте позже.');
      }
    } finally {
      setIsLinking(false);
    }
  }, [refreshUser]);

  const handleUnlinkTelegram = useCallback(async () => {
    if (!confirm('Вы уверены, что хотите отвязать Telegram?')) {
      return;
    }

    setIsUnlinking(true);
    setError(null);
    setSuccess(null);

    try {
      const response = await telegramAuthApi.unlink();
      if (response.success) {
        setSuccess('Telegram успешно отвязан!');
        // Обновляем данные пользователя
        if (refreshUser) {
          await refreshUser();
        }
      }
    } catch (err: any) {
      console.error('Failed to unlink Telegram:', err);
      if (err.response?.status === 400) {
        setError(err.response?.data?.detail || 'Нельзя отвязать единственный способ входа.');
      } else {
        setError('Не удалось отвязать Telegram. Попробуйте позже.');
      }
    } finally {
      setIsUnlinking(false);
    }
  }, [refreshUser]);

  // Проверяем, можно ли отвязать Telegram
  const canUnlinkTelegram = Boolean(
    user?.telegram_id && (user?.email || user?.google_id)
  );

  const normalizeTotpError = (err: any): string => {
    const detail = err?.response?.data?.detail;
    if (typeof detail === 'string' && detail.length > 0) return detail;
    return 'Не удалось выполнить действие с 2FA. Проверьте соединение и права.';
  };

  const handleTotpSetup = useCallback(async () => {
    if (!isAdmin) return;
    setTotpLoading(true);
    setTotpError(null);
    setTotpSuccess(null);
    try {
      const data = await totpApi.setup();
      setTotpSetup(data);
      setTotpSuccess('Секрет 2FA сгенерирован. Отсканируйте QR-код и подтвердите кодом из приложения.');
    } catch (err: any) {
      console.error('Failed to start TOTP setup', err);
      setTotpError(normalizeTotpError(err));
    } finally {
      setTotpLoading(false);
    }
  }, [isAdmin]);

  const handleTotpVerify = useCallback(async () => {
    if (!totpCode || totpCode.trim().length < 6) {
      setTotpError('Введите 6-значный код из приложения 2FA.');
      return;
    }
    setTotpLoading(true);
    setTotpError(null);
    setTotpSuccess(null);
    try {
      await totpApi.verify(totpCode.trim());
      setTotpSuccess('2FA включена. Держите приложение-аутентификатор под рукой.');
      setTotpSetup(null);
      setTotpCode('');
      if (refreshUser) {
        await refreshUser();
      }
    } catch (err: any) {
      console.error('Failed to verify TOTP', err);
      setTotpError(normalizeTotpError(err));
    } finally {
      setTotpLoading(false);
    }
  }, [totpCode, refreshUser]);

  const handleTotpDisable = useCallback(async () => {
    if (!confirm('Отключить 2FA? Вам потребуется войти заново без кода.')) {
      return;
    }
    setTotpLoading(true);
    setTotpError(null);
    setTotpSuccess(null);
    try {
      await totpApi.disable(totpDisableCode.trim() || undefined);
      setTotpSuccess('2FA отключена. Рекомендуем включить её позже.');
      setTotpDisableCode('');
      setTotpSetup(null);
      setTotpCode('');
      if (refreshUser) {
        await refreshUser();
      }
    } catch (err: any) {
      console.error('Failed to disable TOTP', err);
      setTotpError(normalizeTotpError(err));
    } finally {
      setTotpLoading(false);
    }
  }, [totpDisableCode, refreshUser]);

  // Обновляем превью при смене пользователя
  useEffect(() => {
    setLogoPreview(getUserLogo(user?.id) || DEFAULT_LOGO);
  }, [user?.id]);

  useEffect(() => {
    if (user?.totp_enabled) {
      setTotpSetup(null);
      setTotpCode('');
    }
    if (!user?.totp_enabled) {
      setTotpDisableCode('');
    }
  }, [user?.totp_enabled]);

  const handleLogoFile = useCallback(async (file: File) => {
    if (!user?.id) return;
    if (!file.type.startsWith('image/')) {
      setError('Можно загрузить только изображение');
      return;
    }
    setIsSavingLogo(true);
    setError(null);
    setSuccess(null);
    try {
      const dataUrl = await new Promise<string>((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result as string);
        reader.onerror = () => reject(reader.error);
        reader.readAsDataURL(file);
      });
      setUserLogo(user.id, dataUrl);
      setLogoPreview(dataUrl);
      setSuccess('Логотип обновлён');
    } catch (err) {
      console.error('Logo upload failed', err);
      setError('Не удалось загрузить логотип');
    } finally {
      setIsSavingLogo(false);
    }
  }, [user?.id]);

  const handleLogoReset = useCallback(() => {
    if (!user?.id) return;
    resetUserLogo(user.id);
    setLogoPreview(DEFAULT_LOGO);
    setSuccess('Логотип сброшен на стандартный');
  }, [user?.id]);

  return (
    <div className="min-h-screen bg-[color:var(--color-surface)] text-[color:var(--color-text)] transition-colors duration-300">
      <ResponsiveHeader />

      {/* Header */}
      <div className="border-b border-[color:var(--color-border)] bg-[color:var(--color-panel)]/30">
        <div className="mx-auto max-w-3xl px-4 py-3 sm:px-6 lg:px-8">
          <h1 className="text-xl font-semibold">Настройки</h1>
        </div>
      </div>

      <main className="mx-auto max-w-3xl px-4 py-6 sm:py-8 sm:px-6 lg:px-8">
        {/* Profile Section */}
        <section className="mb-8">
          <h2 className="text-lg font-semibold mb-4 border-b border-[color:var(--color-border)] pb-2">
            Профиль
          </h2>
          <div className="space-y-4">
            <div className="flex items-center gap-4">
              {user?.profile_picture_url && (
                <img
                  src={user.profile_picture_url}
                  alt="Profile"
                  className="w-16 h-16 rounded-full"
                />
              )}
              <div>
                <p className="font-medium">{user?.full_name || 'Имя не указано'}</p>
                <p className="text-sm text-[color:var(--color-text-secondary)]">
                  {user?.email || 'Email не указан'}
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Branding / Logo Section */}
        <section className="mb-8">
          <h2 className="text-lg font-semibold mb-4 border-b border-[color:var(--color-border)] pb-2">
            Брендинг (логотип)
          </h2>
          <div className="flex flex-col gap-4">
            <div className="flex items-center gap-4">
              <img
                src={logoPreview}
                alt="Текущий логотип"
                className="w-16 h-16 rounded-lg border border-[color:var(--color-border)] object-contain bg-white"
              />
              <div className="space-y-2">
                <p className="text-sm text-[color:var(--color-text-secondary)]">Логотип, отображаемый в админке для этого пользователя. По умолчанию используется стандартный.</p>
                <div className="flex flex-wrap gap-2">
                  <label className="inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] text-sm cursor-pointer hover:border-[color:var(--color-accent)]">
                    <input
                      type="file"
                      accept="image/*"
                      className="hidden"
                      onChange={(e) => {
                        const file = e.target.files?.[0];
                        if (file) {
                          void handleLogoFile(file);
                        }
                      }}
                    />
                    Загрузить логотип
                  </label>
                  <button
                    type="button"
                    onClick={handleLogoReset}
                    className="px-3 py-2 rounded-lg border border-[color:var(--color-border)] text-sm hover:border-[color:var(--color-accent)]"
                    disabled={isSavingLogo}
                  >
                    Сбросить на стандартный
                  </button>
                </div>
                <p className="text-xs text-[color:var(--color-text-tertiary)]">Рекомендуется квадратное изображение до 300 КБ.</p>
              </div>
            </div>
          </div>
        </section>

        {/* Connected Accounts Section */}
        <section className="mb-8">
          <h2 className="text-lg font-semibold mb-4 border-b border-[color:var(--color-border)] pb-2">
            Связанные аккаунты
          </h2>

          {/* Messages */}
          {error && (
            <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-500">
              {error}
            </div>
          )}
          {success && (
            <div className="mb-4 p-3 rounded-lg bg-green-500/10 border border-green-500/20 text-green-500">
              {success}
            </div>
          )}

          <div className="space-y-4">
            {/* Google Account */}
            <div className="flex items-center justify-between p-4 rounded-lg bg-[color:var(--color-panel)] border border-[color:var(--color-border)]">
              <div className="flex items-center gap-3">
                <svg className="w-6 h-6" viewBox="0 0 24 24">
                  <path
                    fill="#4285F4"
                    d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                  />
                  <path
                    fill="#34A853"
                    d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                  />
                  <path
                    fill="#FBBC05"
                    d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                  />
                  <path
                    fill="#EA4335"
                    d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                  />
                </svg>
                <div>
                  <p className="font-medium">Google</p>
                  {user?.google_id ? (
                    <p className="text-sm text-green-500">Подключён</p>
                  ) : (
                    <p className="text-sm text-[color:var(--color-text-secondary)]">Не подключён</p>
                  )}
                </div>
              </div>
            </div>

            {/* Telegram Account */}
            <div className="flex items-center justify-between p-4 rounded-lg bg-[color:var(--color-panel)] border border-[color:var(--color-border)]">
              <div className="flex items-center gap-3">
                <svg className="w-6 h-6" viewBox="0 0 24 24" fill="#0088cc">
                  <path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.894 8.221l-1.97 9.28c-.145.658-.537.818-1.084.508l-3-2.21-1.446 1.394c-.16.16-.295.295-.605.295l.213-3.053 5.56-5.023c.242-.213-.054-.333-.375-.12l-6.87 4.326-2.962-.924c-.643-.204-.657-.643.136-.954l11.566-4.458c.537-.194 1.006.13.837.94z"/>
                </svg>
                <div>
                  <p className="font-medium">Telegram</p>
                  {user?.telegram_id ? (
                    <div>
                      <p className="text-sm text-green-500">Подключён</p>
                      {user.telegram_username && (
                        <p className="text-xs text-[color:var(--color-text-secondary)]">
                          @{user.telegram_username}
                        </p>
                      )}
                    </div>
                  ) : (
                    <p className="text-sm text-[color:var(--color-text-secondary)]">Не подключён</p>
                  )}
                </div>
              </div>

              <div>
                {user?.telegram_id ? (
                  <button
                    onClick={handleUnlinkTelegram}
                    disabled={isUnlinking || !canUnlinkTelegram}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                      canUnlinkTelegram
                        ? 'bg-red-500/10 text-red-500 hover:bg-red-500/20 border border-red-500/30'
                        : 'bg-gray-500/10 text-gray-400 cursor-not-allowed'
                    }`}
                    title={!canUnlinkTelegram ? 'Добавьте альтернативный способ входа' : ''}
                  >
                    {isUnlinking ? 'Отвязка...' : 'Отвязать'}
                  </button>
                ) : (
                  <div className="flex items-center gap-2">
                    {isLinking ? (
                      <span className="text-sm text-[color:var(--color-text-secondary)]">
                        Подключение...
                      </span>
                    ) : (
                      <TelegramLoginButton
                        onAuth={handleLinkTelegram}
                        buttonSize="small"
                        showUserPhoto={false}
                      />
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* Email Account */}
            <div className="flex items-center justify-between p-4 rounded-lg bg-[color:var(--color-panel)] border border-[color:var(--color-border)]">
              <div className="flex items-center gap-3">
                <svg className="w-6 h-6 text-[color:var(--color-text)]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
                <div>
                  <p className="font-medium">Email</p>
                  {user?.email ? (
                    <div>
                      <p className="text-sm text-green-500">Подключён</p>
                      <p className="text-xs text-[color:var(--color-text-secondary)]">
                        {user.email}
                      </p>
                    </div>
                  ) : (
                    <p className="text-sm text-[color:var(--color-text-secondary)]">Не подключён</p>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Warning if only one auth method */}
          {user?.telegram_id && !canUnlinkTelegram && (
            <div className="mt-4 p-3 rounded-lg bg-yellow-500/10 border border-yellow-500/20 text-yellow-600">
              <p className="text-sm">
                ⚠️ Telegram — ваш единственный способ входа. 
                Для отвязки сначала добавьте email или Google аккаунт.
              </p>
            </div>
          )}
        </section>

        {/* Appearance Section */}
        <section className="mb-8">
          <h2 className="text-lg font-semibold mb-4 border-b border-[color:var(--color-border)] pb-2 flex items-center gap-2">
            <Sun className="w-5 h-5" />
            Внешний вид
          </h2>

          <div className="space-y-4">
            {/* Theme */}
            <div className="p-4 rounded-lg bg-[color:var(--color-panel)] border border-[color:var(--color-border)]">
              <div className="flex items-center justify-between mb-3">
                <div>
                  <p className="font-medium">Тема оформления</p>
                  <p className="text-sm text-[color:var(--color-text-secondary)]">
                    Выберите цветовую схему интерфейса
                  </p>
                </div>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => handleThemeChange('light')}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                    theme === 'light'
                      ? 'bg-[color:var(--color-accent)] text-white'
                      : 'bg-[color:var(--color-surface)] border border-[color:var(--color-border)] hover:bg-white/5'
                  }`}
                >
                  <Sun className="w-4 h-4" />
                  Светлая
                </button>
                <button
                  onClick={() => handleThemeChange('dark')}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                    theme === 'dark'
                      ? 'bg-[color:var(--color-accent)] text-white'
                      : 'bg-[color:var(--color-surface)] border border-[color:var(--color-border)] hover:bg-white/5'
                  }`}
                >
                  <Moon className="w-4 h-4" />
                  Тёмная
                </button>
                <button
                  onClick={() => handleThemeChange('system')}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                    theme === 'system'
                      ? 'bg-[color:var(--color-accent)] text-white'
                      : 'bg-[color:var(--color-surface)] border border-[color:var(--color-border)] hover:bg-white/5'
                  }`}
                >
                  <Monitor className="w-4 h-4" />
                  Системная
                </button>
              </div>
            </div>

            {/* Language */}
            <div className="p-4 rounded-lg bg-[color:var(--color-panel)] border border-[color:var(--color-border)]">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-3">
                  <Globe className="w-5 h-5 text-[color:var(--color-accent)]" />
                  <div>
                    <p className="font-medium">Язык интерфейса</p>
                    <p className="text-sm text-[color:var(--color-text-secondary)]">
                      Выберите язык приложения
                    </p>
                  </div>
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                {[
                  { code: 'ru', label: 'Русский', flag: '🇷🇺' },
                  { code: 'uk', label: 'Українська', flag: '🇺🇦' },
                  { code: 'en', label: 'English', flag: '🇬🇧' },
                  { code: 'de', label: 'Deutsch', flag: '🇩🇪' },
                ].map((lang) => (
                  <button
                    key={lang.code}
                    onClick={() => handleLanguageChange(lang.code)}
                    className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                      currentLang === lang.code
                        ? 'bg-[color:var(--color-accent)] text-white'
                        : 'bg-[color:var(--color-surface)] border border-[color:var(--color-border)] hover:bg-white/5'
                    }`}
                  >
                    <span>{lang.flag}</span>
                    {lang.label}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* Notifications Section */}
        <section className="mb-8">
          <h2 className="text-lg font-semibold mb-4 border-b border-[color:var(--color-border)] pb-2 flex items-center gap-2">
            <Bell className="w-5 h-5" />
            Уведомления
          </h2>

          <div className="space-y-3">
            {/* Email Notifications */}
            <div className="flex items-center justify-between p-4 rounded-lg bg-[color:var(--color-panel)] border border-[color:var(--color-border)]">
              <div className="flex items-center gap-3">
                <Mail className="w-5 h-5 text-[color:var(--color-text-secondary)]" />
                <div>
                  <p className="font-medium">Email-уведомления</p>
                  <p className="text-sm text-[color:var(--color-text-secondary)]">
                    Получать уведомления на почту
                  </p>
                </div>
              </div>
              <button
                onClick={() => setNotifications(prev => ({ ...prev, email: !prev.email }))}
                className={`relative w-12 h-6 rounded-full transition-colors ${
                  notifications.email ? 'bg-[color:var(--color-accent)]' : 'bg-gray-600'
                }`}
              >
                <span 
                  className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-transform ${
                    notifications.email ? 'left-7' : 'left-1'
                  }`} 
                />
              </button>
            </div>

            {/* Telegram Notifications */}
            <div className="flex items-center justify-between p-4 rounded-lg bg-[color:var(--color-panel)] border border-[color:var(--color-border)]">
              <div className="flex items-center gap-3">
                <MessageSquare className="w-5 h-5 text-[color:var(--color-text-secondary)]" />
                <div>
                  <p className="font-medium">Telegram-уведомления</p>
                  <p className="text-sm text-[color:var(--color-text-secondary)]">
                    Получать уведомления в Telegram
                  </p>
                </div>
              </div>
              <button
                onClick={() => setNotifications(prev => ({ ...prev, telegram: !prev.telegram }))}
                className={`relative w-12 h-6 rounded-full transition-colors ${
                  notifications.telegram ? 'bg-[color:var(--color-accent)]' : 'bg-gray-600'
                }`}
                disabled={!user?.telegram_id}
                title={!user?.telegram_id ? 'Сначала привяжите Telegram' : ''}
              >
                <span 
                  className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-transform ${
                    notifications.telegram ? 'left-7' : 'left-1'
                  }`} 
                />
              </button>
            </div>

            {/* Push Notifications */}
            <div className="flex items-center justify-between p-4 rounded-lg bg-[color:var(--color-panel)] border border-[color:var(--color-border)]">
              <div className="flex items-center gap-3">
                <Smartphone className="w-5 h-5 text-[color:var(--color-text-secondary)]" />
                <div>
                  <p className="font-medium">Push-уведомления</p>
                  <p className="text-sm text-[color:var(--color-text-secondary)]">
                    Уведомления в браузере
                  </p>
                </div>
              </div>
              <button
                onClick={() => setNotifications(prev => ({ ...prev, push: !prev.push }))}
                className={`relative w-12 h-6 rounded-full transition-colors ${
                  notifications.push ? 'bg-[color:var(--color-accent)]' : 'bg-gray-600'
                }`}
              >
                <span 
                  className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-transform ${
                    notifications.push ? 'left-7' : 'left-1'
                  }`} 
                />
              </button>
            </div>
          </div>
        </section>

        {/* Security Section */}
        <section className="mb-8">
          <h2 className="text-lg font-semibold mb-4 border-b border-[color:var(--color-border)] pb-2 flex items-center gap-2">
            <Shield className="w-5 h-5" />
            Безопасность
          </h2>

          <div className="space-y-3">
            {/* Active Sessions */}
            <div className="p-4 rounded-lg bg-[color:var(--color-panel)] border border-[color:var(--color-border)]">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium">Активные сессии</p>
                  <p className="text-sm text-[color:var(--color-text-secondary)]">
                    Текущее устройство
                  </p>
                </div>
                <span className="px-2 py-1 rounded-full bg-green-500/20 text-green-500 text-xs font-medium">
                  Активна
                </span>
              </div>
            </div>

            {/* Two-Factor Auth */}
            <div className="p-4 rounded-lg bg-[color:var(--color-panel)] border border-[color:var(--color-border)]">
              <div className="flex items-center justify-between gap-3 flex-wrap">
                <div>
                  <p className="font-medium">Двухфакторная аутентификация (TOTP)</p>
                  <p className="text-sm text-[color:var(--color-text-secondary)]">
                    Одноразовые коды из приложения-генератора
                  </p>
                </div>
                <span
                  className={`px-2 py-1 rounded-full text-xs font-medium ${
                    user?.totp_enabled
                      ? 'bg-green-500/20 text-green-500'
                      : 'bg-gray-600 text-gray-300'
                  }`}
                >
                  {user?.totp_enabled ? 'Включена' : 'Выключена'}
                </span>
              </div>

              {totpError && (
                <div className="mt-3 p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-sm text-red-400">
                  {totpError}
                </div>
              )}
              {totpSuccess && (
                <div className="mt-3 p-3 rounded-lg bg-green-500/10 border border-green-500/30 text-sm text-green-400">
                  {totpSuccess}
                </div>
              )}

              {!isAdmin ? (
                <p className="mt-3 text-sm text-[color:var(--color-text-secondary)]">
                  Доступно только администраторам. Обратитесь к суперадминистратору для включения 2FA.
                </p>
              ) : user?.totp_enabled ? (
                <div className="mt-3 space-y-3">
                  <p className="text-sm text-[color:var(--color-text-secondary)]">
                    2FA активна. Отключайте её только при смене устройства или по процедуре восстановления доступа.
                  </p>
                  <div className="flex flex-col sm:flex-row gap-2 items-start">
                    <input
                      type="text"
                      inputMode="numeric"
                      autoComplete="one-time-code"
                      placeholder="Код 2FA (опционально)"
                      className="w-full sm:w-64 rounded-lg border border-[color:var(--color-border)] bg-[color:var(--color-surface)] p-2 text-sm"
                      value={totpDisableCode}
                      onChange={(e) => setTotpDisableCode(e.target.value)}
                      disabled={totpLoading}
                    />
                    <button
                      type="button"
                      onClick={handleTotpDisable}
                      disabled={totpLoading}
                      className="px-4 py-2 rounded-lg bg-red-500/20 text-red-200 text-sm font-medium hover:bg-red-500/30 disabled:opacity-60"
                    >
                      Отключить 2FA
                    </button>
                  </div>
                  <p className="text-xs text-[color:var(--color-text-tertiary)]">
                    Укажите актуальный код для подтверждения (если доступен). Без кода отключение всё равно сработает, но потребует JWT c правами администратора.
                  </p>
                </div>
              ) : (
                <div className="mt-3 space-y-3">
                  {totpSetup ? (
                    <>
                      <div className="grid gap-3 sm:grid-cols-2 items-start">
                        <div className="flex items-center justify-center rounded-lg bg-[color:var(--color-surface-muted)] border border-[color:var(--color-border)] p-3">
                          <img
                            src={`https://api.qrserver.com/v1/create-qr-code/?size=220x220&data=${encodeURIComponent(totpSetup.otpauth_url)}`}
                            alt="QR-код для 2FA"
                            className="w-40 h-40"
                          />
                        </div>
                        <div className="space-y-2 text-sm">
                          <p>1. Отсканируйте QR-код в Google Authenticator, 1Password или другом TOTP-клиенте.</p>
                          <p>2. Если QR не сканируется, введите секрет вручную:</p>
                          <div className="font-mono text-xs bg-[color:var(--color-surface-muted)] border border-[color:var(--color-border)] rounded-lg p-2 break-all select-all">
                            {totpSetup.secret}
                          </div>
                          <p className="text-xs text-[color:var(--color-text-tertiary)]">
                            Секрет показывается только сейчас. После подтверждения его можно будет обновить заново.
                          </p>
                        </div>
                      </div>
                      <div className="flex flex-col sm:flex-row gap-2 items-start">
                        <input
                          type="text"
                          inputMode="numeric"
                          autoComplete="one-time-code"
                          placeholder="123456"
                          className="w-full sm:w-40 rounded-lg border border-[color:var(--color-border)] bg-[color:var(--color-surface)] p-2 text-sm"
                          value={totpCode}
                          onChange={(e) => setTotpCode(e.target.value)}
                          disabled={totpLoading}
                        />
                        <button
                          type="button"
                          onClick={handleTotpVerify}
                          disabled={totpLoading || totpCode.trim().length < 6}
                          className="px-4 py-2 rounded-lg bg-[color:var(--color-accent)] text-white text-sm font-medium hover:opacity-90 disabled:opacity-60"
                        >
                          Подтвердить код
                        </button>
                        <button
                          type="button"
                          onClick={() => {
                            setTotpSetup(null);
                            setTotpCode('');
                            setTotpError(null);
                            setTotpSuccess(null);
                          }}
                          className="px-4 py-2 rounded-lg border border-[color:var(--color-border)] text-sm hover:bg-[color:var(--color-surface-muted)] disabled:opacity-60"
                          disabled={totpLoading}
                        >
                          Сбросить
                        </button>
                      </div>
                    </>
                  ) : (
                    <button
                      type="button"
                      onClick={handleTotpSetup}
                      disabled={totpLoading}
                      className="px-4 py-2 rounded-lg bg-[color:var(--color-accent)] text-white text-sm font-medium hover:opacity-90 disabled:opacity-60"
                    >
                      Сгенерировать QR для 2FA
                    </button>
                  )}
                </div>
              )}
            </div>

            {/* Logout from all devices */}
            <button
              onClick={() => {
                if (confirm('Выйти со всех устройств? Вам потребуется войти заново.')) {
                  logout();
                }
              }}
              className="w-full flex items-center justify-between p-4 rounded-lg bg-[color:var(--color-panel)] border border-red-500/30 hover:bg-red-500/10 transition-colors group"
            >
              <div className="flex items-center gap-3">
                <LogOut className="w-5 h-5 text-red-400" />
                <div className="text-left">
                  <p className="font-medium text-red-400">Выйти со всех устройств</p>
                  <p className="text-sm text-[color:var(--color-text-secondary)]">
                    Завершить все активные сессии
                  </p>
                </div>
              </div>
            </button>
          </div>
        </section>

        {/* About Section */}
        <section className="mb-8">
          <h2 className="text-lg font-semibold mb-4 border-b border-[color:var(--color-border)] pb-2 flex items-center gap-2">
            <Info className="w-5 h-5" />
            О приложении
          </h2>

          <div className="p-4 rounded-lg bg-[color:var(--color-panel)] border border-[color:var(--color-border)]">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-[color:var(--color-text-secondary)]">Версия</span>
                <span className="font-mono">{APP_VERSION}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-[color:var(--color-text-secondary)]">Сборка</span>
                <span className="font-mono text-sm">2025.12.17</span>
              </div>
              <div className="pt-3 border-t border-[color:var(--color-border)]">
                <a
                  href="https://github.com/sattva2020/tg-video-stream"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 text-sm text-[color:var(--color-accent)] hover:underline"
                >
                  <ExternalLink className="w-4 h-4" />
                  GitHub репозиторий
                </a>
              </div>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
};

export default SettingsPage;
