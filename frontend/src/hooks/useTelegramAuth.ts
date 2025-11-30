/**
 * Хук для авторизации через Telegram Login Widget.
 */
import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { telegramAuthApi, TelegramAuthData, TelegramAuthResponse } from '../services/telegramAuth';

interface UseTelegramAuthResult {
  isLoading: boolean;
  error: string | null;
  handleTelegramAuth: (data: TelegramAuthData) => Promise<void>;
  clearError: () => void;
}

/**
 * Хук для обработки авторизации через Telegram.
 * 
 * @param onSuccess - Callback при успешной авторизации
 * @returns Объект с состоянием и функциями для работы с Telegram auth
 */
export function useTelegramAuth(
  onSuccess?: (response: TelegramAuthResponse) => void
): UseTelegramAuthResult {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  const handleTelegramAuth = useCallback(async (data: TelegramAuthData) => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await telegramAuthApi.auth(data);
      
      if (response.success) {
        // Вызываем callback если предоставлен
        if (onSuccess) {
          onSuccess(response);
        }
        
        // Показываем уведомление о регистрации для новых пользователей
        if (response.is_new_user) {
          console.info('New user registered via Telegram:', response.user.telegram_username);
        }
        
        // Перенаправляем на dashboard
        // Для pending пользователей можно показать специальную страницу
        if (response.user.status === 'pending') {
          navigate('/pending-approval');
        } else {
          navigate('/dashboard');
        }
      }
    } catch (err: any) {
      console.error('Telegram auth failed:', err);
      
      // Обрабатываем разные типы ошибок
      if (err.response?.status === 400) {
        setError(err.response?.data?.detail || 'Ошибка авторизации. Попробуйте снова.');
      } else if (err.response?.status === 409) {
        setError('Этот Telegram аккаунт уже привязан к другому пользователю.');
      } else if (err.response?.status === 429) {
        setError('Слишком много попыток. Попробуйте позже.');
      } else {
        setError('Произошла ошибка. Попробуйте позже.');
      }
    } finally {
      setIsLoading(false);
    }
  }, [navigate, onSuccess]);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  return {
    isLoading,
    error,
    handleTelegramAuth,
    clearError,
  };
}
