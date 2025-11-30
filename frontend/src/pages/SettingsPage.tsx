/**
 * Страница настроек пользователя.
 * 
 * Включает:
 * - Привязка/отвязка Telegram
 * - Информация о профиле
 * - Связанные аккаунты
 */
import React, { useState, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { ResponsiveHeader } from '../components/layout';
import { ThemeToggle } from '../components/auth/ThemeToggle';
import TelegramLoginButton from '../components/TelegramLoginButton';
import { telegramAuthApi, TelegramAuthData } from '../services/telegramAuth';

const SettingsPage: React.FC = () => {
  const { user, refreshUser } = useAuth();
  const [isLinking, setIsLinking] = useState(false);
  const [isUnlinking, setIsUnlinking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

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

  return (
    <div className="min-h-screen bg-[color:var(--color-surface)] text-[color:var(--color-text)] transition-colors duration-300">
      <ResponsiveHeader />

      {/* Header */}
      <div className="border-b border-[color:var(--color-border)] bg-[color:var(--color-panel)]/30">
        <div className="mx-auto max-w-3xl px-4 py-3 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between">
            <h1 className="text-xl font-semibold">Настройки</h1>
            <ThemeToggle className="text-[color:var(--color-text)]" />
          </div>
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
      </main>
    </div>
  );
};

export default SettingsPage;
